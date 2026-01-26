import pytest
from unittest.mock import MagicMock, Mock
import os
import json
import re
from livekit.agents.utils.interrupt_handler import can_ignore
from livekit.agents.voice.agent_session import DEFAULT_IGNORE_LIST

# --- MOCKS ---

class MockOptions:
    def __init__(self):
        self.resume_false_interruption = False
        self.false_interruption_timeout = None
        self.min_interruption_words = 0
        self.ignore_list = ["yeah", "ok", "hmm", "aha"]

class MockSession:
    def __init__(self):
        self.options = MockOptions()
        self.agent_state = "listening"
        self.output = MagicMock()
        self._update_agent_state = MagicMock()

class MockAudioRecognition:
    def __init__(self):
        self.current_transcript = ""

class MockSpeech:
    def __init__(self):
        self.interrupted = False
        self.allow_interruptions = True
        self.interrupt = MagicMock()

class AgentUnderTest:
    def __init__(self):
        self._session = MockSession()
        self._audio_recognition = MockAudioRecognition()
        self.stt = MagicMock()
        self.llm = MagicMock()
        self.llm.capabilities.turn_detection = False
        self._current_speech = MockSpeech()
        self._rt_session = MagicMock()
        self._false_interruption_timer = None
    
    def _interrupt_by_audio_activity(self) -> None:
        opt = self._session.options
        use_pause = opt.resume_false_interruption and opt.false_interruption_timeout is not None

        if hasattr(self.llm, 'capabilities') and self.llm.capabilities.turn_detection:
            return

        if (self.stt is not None and opt.min_interruption_words > 0):
             pass 
        
        is_agent_speaking = self.stt and self._audio_recognition and self._session.agent_state == "speaking"
        if is_agent_speaking:
            transcript = self._audio_recognition.current_transcript        
            ignore_list = self._session.options.ignore_list

            if(can_ignore(transcript, ignore_list)):
                return

        if self._rt_session is not None:
            self._rt_session.start_user_activity()

        if (
            self._current_speech is not None
            and not self._current_speech.interrupted
            and self._current_speech.allow_interruptions
        ):
            # skipping pause logic for simplicity to focus on the interrupt call
            self._current_speech.interrupt()

# --- UNIT TESTS ---

class TestCanIgnoreLogic:
    """Tests strictly for the string matching logic."""

    def test_basic_backchannel_ignored(self):
        """Scenario 1: Simple backchannels should be ignored."""
        assert can_ignore("yeah", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("uh-huh", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("Okay.", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("fine.", DEFAULT_IGNORE_LIST) is True

    def test_mixed_backchannel_ignored(self):
        """Scenario 2: Multiple backchannels in a row should be ignored."""
        assert can_ignore("okay yeah uh-huh", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("Okay. Yeah. Fine.", DEFAULT_IGNORE_LIST) is True

    def test_command_interrupts(self):
        """Scenario 3: Commands not in the list should NOT be ignored."""
        assert can_ignore("no stop", DEFAULT_IGNORE_LIST) is False
        assert can_ignore("stop", DEFAULT_IGNORE_LIST) is False
        assert can_ignore("Wait.", DEFAULT_IGNORE_LIST) is False

    def test_mixed_input_interrupts(self):
        """Scenario 4: Mixed input (Backchannel + Command) should NOT be ignored."""
        assert can_ignore("yeah okay but wait", DEFAULT_IGNORE_LIST) is False  
        assert can_ignore("wait yeah", DEFAULT_IGNORE_LIST) is False
        assert can_ignore("no stop", DEFAULT_IGNORE_LIST) is False

    def test_punctuation_and_case_handling(self):
        """Ensure logic is robust against messy STT output."""
        assert can_ignore("Yeah.", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("OKAY!!!", DEFAULT_IGNORE_LIST) is True
        assert can_ignore("mm-hmm", ["mm-hmm"]) is True

@pytest.fixture
def agent():
    return AgentUnderTest()

def test_matrix_ignore_backchannel_while_speaking(agent):
    """
    Scenario: User says 'yeah' while Agent is Speaking.
    Result: IGNORE (Agent does NOT stop).
    """
    agent._session.agent_state = "speaking"
    agent._audio_recognition.current_transcript = "Yeah"
    
    agent._interrupt_by_audio_activity()
    
    # The function should have returned early, so interrupt() should NOT be called.
    agent._current_speech.interrupt.assert_not_called()

def test_matrix_interrupt_command_while_speaking(agent):
    """
    Scenario: User says 'Stop' while Agent is Speaking.
    Result: INTERRUPT (Agent stops).
    """
    agent._session.agent_state = "speaking"
    agent._audio_recognition.current_transcript = "Stop"
    
    agent._interrupt_by_audio_activity()
    
    # 'Stop' is not in ignore list, so interrupt() SHOULD be called.
    agent._current_speech.interrupt.assert_called_once()

def test_matrix_respond_backchannel_while_silent(agent):
    """
    Scenario: User says 'Yeah' while Agent is Silent (Listening).
    Result: RESPOND (Normal processing, NO ignore).
    """
    agent._session.agent_state = "listening"
    agent._audio_recognition.current_transcript = "Yeah"
    
    agent._interrupt_by_audio_activity()
    
    # Even though it's 'Yeah', the agent wasn't speaking, so the ignore logic is skipped.
    agent._current_speech.interrupt.assert_called_once()

def test_matrix_semantic_interruption_mixed_input(agent):
    """
    Scenario: User says 'Yeah wait' while Agent is Speaking.
    Result: INTERRUPT (Contains command).
    """
    agent._session.agent_state = "speaking"
    agent._audio_recognition.current_transcript = "Yeah wait"
    
    agent._interrupt_by_audio_activity()
    
    # 'Yeah wait' is not an exact match for 'yeah', so it should NOT ignore.
    agent._current_speech.interrupt.assert_called_once()

def test_configurable_ignore_list(agent):
    """Scenario: Verify dynamic ignore list updates."""
    agent._session.agent_state = "speaking"
    agent._audio_recognition.current_transcript = "banana"
    
    # Before adding banana: Should interrupt
    agent._current_speech.interrupt = MagicMock()
    agent._interrupt_by_audio_activity()
    agent._current_speech.interrupt.assert_called_once()
    
    # After adding banana: Should IGNORE
    agent._session.options.ignore_list.append("banana")
    agent._current_speech.interrupt.reset_mock()
    
    agent._interrupt_by_audio_activity()
    agent._current_speech.interrupt.assert_not_called()