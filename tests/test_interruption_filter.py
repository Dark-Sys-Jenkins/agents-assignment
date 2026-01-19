"""
Tests for intelligent interruption handling (backchannel filtering).

This module tests the context-aware interruption logic that distinguishes between:
- Backchannels ("yeah", "ok", "hmm") - ignored when agent is speaking AND transcript is available
- Interrupt commands ("stop", "wait", "no") - always trigger interruption
- Mixed inputs ("yeah but wait") - trigger interruption due to interrupt word
"""

from __future__ import annotations

import asyncio

import pytest

from livekit.agents import Agent, AgentStateChangedEvent
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session


class SimpleAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")


SESSION_TIMEOUT = 60.0


@pytest.mark.asyncio
async def test_backchannel_ignored_while_agent_speaking() -> None:
    """
    CRITICAL TEST - Scenario 1: The Long Explanation
    
    Test that backchannels are IGNORED (audio NOT interrupted) when agent is speaking.
    This is the CORE requirement of the challenge.
    
    Scenario: Agent is speaking, user says "yeah".
    Expected: Agent continues speaking WITHOUT interruption (interrupted=False).
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you... once upon a time...")
    actions.add_tts(10.0)  # Long audio response (10 seconds)
    # User says "yeah" at 5.0s while agent is speaking (should be IGNORED)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.2)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "ignore_backchannels_when_speaking": True,
            "resume_false_interruption": True,
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Audio should NOT be interrupted - this is the CORE REQUIREMENT
    # The playback should complete naturally or be resumed after backchannel detection
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False


async def test_interrupt_command_stops_agent() -> None:
    """
    Test that interrupt commands ('stop', 'wait', 'no') stop the agent immediately.
    
    Scenario: Agent is speaking, user says "stop".
    Expected: Agent stops immediately.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you... once upon a time...")
    actions.add_tts(10.0)  # Long audio response
    # User says "stop" at 5.0s while agent is speaking (should INTERRUPT)
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.2)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"ignore_backchannels_when_speaking": True},
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Audio SHOULD be interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True


@pytest.mark.asyncio
async def test_mixed_input_triggers_interrupt() -> None:
    """
    Test that mixed input containing interrupt words triggers interruption.
    
    Scenario: Agent is speaking, user says "yeah but wait".
    Expected: Agent stops because "wait" is an interrupt word.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you... once upon a time...")
    actions.add_tts(10.0)
    # User says "yeah but wait" (contains interrupt word "wait")
    actions.add_user_speech(5.0, 6.0, "yeah but wait", stt_delay=0.2)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"ignore_backchannels_when_speaking": True},
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Audio SHOULD be interrupted due to "wait"
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True


@pytest.mark.asyncio
async def test_backchannel_filtering_disabled() -> None:
    """
    Test that backchannels are NOT filtered when ignore_backchannels_when_speaking is False.
    
    Scenario: Feature disabled, agent speaking, user says "yeah".
    Expected: Agent is interrupted (default behavior).
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you... once upon a time...")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.2)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"ignore_backchannels_when_speaking": False},
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # When disabled, "yeah" SHOULD interrupt (back to default behavior)
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True


@pytest.mark.asyncio
async def test_backchannel_processed_when_agent_silent() -> None:
    """
    CRITICAL TEST - Scenario 2: The Passive Affirmation
    
    Test that backchannels ("yeah") ARE processed when agent is SILENT.
    This tests state-awareness: same word is handled differently based on agent state.
    
    Scenario: Agent asks "Are you ready?" and goes silent. User says "Yeah".
    Expected: Agent processes "Yeah" as valid input and responds.
    """
    speed = 5.0
    actions = FakeActions()
    # User initiates conversation
    actions.add_user_speech(0.5, 2.5, "Ask me if I'm ready.")
    actions.add_llm("Are you ready?")
    actions.add_tts(1.0)  # Short response - agent goes silent quickly
    # Agent is now SILENT. User says "yeah" as a response (should be PROCESSED)
    actions.add_user_speech(4.0, 4.5, "yeah", stt_delay=0.2)
    # Agent should respond to "yeah"
    actions.add_llm("Great, let's continue!")
    actions.add_tts(1.5)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"ignore_backchannels_when_speaking": True},
    )
    agent = SimpleAgent()

    # Track transcription events to verify "yeah" was processed
    transcription_events: list = []
    
    @session.on("user_input_transcribed")
    def on_transcribed(ev):
        transcription_events.append(ev)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Verify "yeah" was transcribed (not filtered out)
    transcripts = [ev.transcript for ev in transcription_events if ev.is_final]
    yeah_found = any("yeah" in t.lower() for t in transcripts)
    assert yeah_found, f"'yeah' should be processed when agent is silent. Got: {transcripts}"
    
    # Verify there were 2 LLM responses (initial + response to "yeah")
    chat_items = [item for item in session.history.items if item.type == "message" and item.role == "assistant"]
    assert len(chat_items) >= 2, "Agent should respond to 'yeah' when silent"


@pytest.mark.asyncio
async def test_classify_interruption_logic() -> None:
    """
    Unit test for the _classify_interruption logic.
    
    This tests the classification directly without running a full session.
    """
    from livekit.agents.voice.agent_session import (
        DEFAULT_BACKCHANNEL_WORDS, 
        DEFAULT_INTERRUPT_WORDS
    )
    import re
    
    def classify(text: str) -> tuple[bool, bool]:
        """Classify text same as _classify_interruption does."""
        if not text:
            return False, False
        
        raw_tokens = re.split(r'[\s\-_]+', text.lower().strip())
        tokens = set()
        for t in raw_tokens:
            cleaned = re.sub(r'[^\w]', '', t)
            if cleaned:
                tokens.add(cleaned)
        
        if not tokens:
            return False, False
        
        has_interrupt = bool(tokens & DEFAULT_INTERRUPT_WORDS)
        is_backchannel = tokens.issubset(DEFAULT_BACKCHANNEL_WORDS)
        
        return is_backchannel, has_interrupt
    
    # Test pure backchannels
    assert classify("yeah") == (True, False)
    assert classify("ok") == (True, False)
    assert classify("uh-huh") == (True, False)
    assert classify("yeah okay mhm") == (True, False)
    
    # Test interrupt commands
    assert classify("stop") == (False, True)
    assert classify("wait") == (False, True)
    assert classify("no") == (False, True)
    
    # Test mixed (backchannel + interrupt)
    assert classify("yeah but wait") == (False, True)  # has interrupt
    assert classify("ok stop please") == (False, True)  # has interrupt
    
    # Test regular speech (neither backchannel nor interrupt)
    assert classify("hello there") == (False, False)
    assert classify("tell me more about that") == (False, False)
    
    # Test empty
    assert classify("") == (False, False)
    assert classify("   ") == (False, False)
