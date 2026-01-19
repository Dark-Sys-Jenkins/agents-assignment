# examples/voice_agents/test_timing_race.py
"""
Test the race condition handling in SmartAgentActivity.
"""

import asyncio
import pytest
import logging
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Ensure we can import from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smart_interruption_session import SmartAgentActivity
from intelligent_interruption_agent import InterruptionClassifier
from livekit.agents.stt import SpeechEvent, SpeechData, SpeechEventType
from livekit.agents.voice.agent_activity import AgentActivity

logging.basicConfig(level=logging.DEBUG)

# We use a mock parent class to avoid deep livekit dependencies, 
# BUT we want to test SmartAgentActivity directly as requested.
# The SmartAgentActivity inherits from AgentActivity.
# Ideally we should be able to instantiate it if we mock the args.

@pytest.fixture
def handler():
    """Create handler with classifier"""
    # specific import to avoid issues
    from intelligent_interruption_agent import IntelligentInterruptionHandler
    return IntelligentInterruptionHandler()


@pytest.fixture
def activity(handler):
    """Create SmartAgentActivity for testing"""
    mock_agent = Mock()
    mock_session = Mock()
    
    # Don't patch parent class - create directly
    # We rely on mocks for agent and session to satisfy AgentActivity.__init__
    
    # Issue: AgentActivity.__init__ might require valid objects or do side effects.
    # However, user requested "create directly".
    # If AgentActivity inherits from RecognitionHooks, it might be fine with mocks.
    
    # We might still need to patch livekit.agents.voice.agent_activity.AudioRecognition 
    # if it's instantiated in __init__
    
    with patch('livekit.agents.voice.agent_activity.AudioRecognition'):
        activity = SmartAgentActivity(mock_agent, mock_session, handler)
        
        # Mock the interrupt method explicitly or rely on it being present/mockable
        # Since we're not patching the class, we need to mock the method on the instance
        # OR ensure the parent class method works (which calls session methods)
        
        # We'll attach a mock for _interrupt_by_audio_activity to trace called
        # The parent implementation exists, but we want to verify it's CALLED.
        # We can't easily spy on it unless we mock it.
        activity._interrupt_by_audio_activity = AsyncMock()
        
        # Initialize state
        activity._current_speech = Mock()
        activity._current_speech.interrupt = AsyncMock() # Ensure this is async too just in case fallback hits
        activity._agent_state = "speaking"
        
        return activity


@pytest.mark.asyncio
async def test_backchanneling_buffered_and_ignored(activity):
    """
    Test: User says 'yeah' during agent speech
    Expected: Buffered, then ignored (agent continues)
    """
    # Agent is speaking
    activity._agent_state = "speaking"
    
    # VAD fires
    vad_event = Mock()
    activity.on_vad_inference_done(vad_event) # SYNC
    await asyncio.sleep(0.01) # Yield to allow task to run
    
    # Should have created pending interruption
    assert len(activity.pending_interruptions) == 1
    assert not activity._interrupt_by_audio_activity.called
    
    # Small delay (simulate VAD-STT gap)
    await asyncio.sleep(0.05)
    
    # STT completes with "yeah"
    transcript = SpeechEvent(
        type=SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[SpeechData(text="yeah", language="en")]
    )
    # Correct signature: (ev, speaking=None)
    activity.on_final_transcript(transcript, speaking=True) # SYNC
    await asyncio.sleep(0.01) # Yield
    
    # Should NOT have interrupted
    assert not activity._interrupt_by_audio_activity.called
    assert len(activity.pending_interruptions) == 0  # Cleaned up


@pytest.mark.asyncio
async def test_real_interrupt_buffered_and_executed(activity):
    """
    Test: User says 'stop' during agent speech
    Expected: Buffered, then executed (agent stops)
    """
    # Agent is speaking
    activity._agent_state = "speaking"
    
    # VAD fires
    vad_event = Mock()
    activity.on_vad_inference_done(vad_event)
    await asyncio.sleep(0.01)
    
    # Should have created pending interruption
    assert len(activity.pending_interruptions) == 1
    
    # STT completes with "stop"
    transcript = SpeechEvent(
        type=SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[SpeechData(text="stop", language="en")]
    )
    activity.on_final_transcript(transcript, speaking=True)
    await asyncio.sleep(0.01)
    
    # Should have interrupted
    assert activity._interrupt_by_audio_activity.called
    assert len(activity.pending_interruptions) == 0


@pytest.mark.asyncio
async def test_timeout_triggers_interrupt(activity):
    """
    Test: STT takes too long
    Expected: Timeout triggers interruption after 400ms
    """
    # Set short timeout for testing
    activity.INTERRUPTION_TIMEOUT_MS = 100
    
    # Agent is speaking
    activity._agent_state = "speaking"
    
    # VAD fires
    vad_event = Mock()
    activity.on_vad_inference_done(vad_event)
    await asyncio.sleep(0.01)
    
    # Wait for timeout
    await asyncio.sleep(0.15)
    
    # Should have interrupted due to timeout
    assert activity._interrupt_by_audio_activity.called


@pytest.mark.asyncio
async def test_interim_early_detection(activity):
    """
    Test: Interim STT detects "stop" early
    Expected: Interrupts immediately without waiting for final
    """
    # Agent is speaking
    activity._agent_state = "speaking"
    
    # VAD fires
    activity.on_vad_inference_done(Mock())
    await asyncio.sleep(0.01)
    
    # Interim STT with "stop"
    interim = SpeechEvent(
        type=SpeechEventType.INTERIM_TRANSCRIPT,
        alternatives=[SpeechData(text="stop", language="en")]
    )
    
    # FIX: Correct signature
    activity.on_interim_transcript(interim, speaking=True)
    await asyncio.sleep(0.01)
    
    # Should have interrupted early
    assert activity._interrupt_by_audio_activity.called


@pytest.mark.asyncio
async def test_agent_silent_normal_processing(activity):
    """
    Test: User says 'yeah' when agent is silent
    Expected: Normal processing (not buffered)
    """
    activity._current_speech = None
    activity._agent_state = "listening"

    # Mock parent handler to avoid deep LiveKit VAD internals
    with patch.object(AgentActivity, 'on_vad_inference_done', return_value=None):
        vad_event = Mock()
        activity.on_vad_inference_done(vad_event)
        await asyncio.sleep(0.01)

    assert len(activity.pending_interruptions) == 0


@pytest.mark.asyncio
async def test_mixed_input_yeah_but_wait(activity):
    """
    Test: User says 'yeah but wait'
    Expected: Interrupts (contains 'wait')
    """
    # Agent is speaking
    activity._agent_state = "speaking"
    
    # VAD fires
    activity.on_vad_inference_done(Mock())
    await asyncio.sleep(0.01)
    
    # STT completes
    transcript = SpeechEvent(
        type=SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[SpeechData(text="yeah but wait", language="en")]
    )
    activity.on_final_transcript(transcript, speaking=True)
    await asyncio.sleep(0.01)
    
    # Should interrupt
    assert activity._interrupt_by_audio_activity.called
