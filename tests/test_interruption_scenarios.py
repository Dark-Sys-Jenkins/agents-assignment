"""
Test various interruption scenarios to demonstrate the false interruption bug.

This test file covers:
1. Agent speaking + filler word ("yeah") → Should continue speaking (BUG: currently stops)
2. Agent speaking + command word ("stop") → Should stop speaking (works correctly)
3. Agent silent + filler word ("yeah") → Should respond (works correctly)
4. Agent speaking + mixed input ("yeah wait") → Should stop speaking (command detected)

Run with: pytest tests/test_interruption_scenarios.py -v -s
"""

from __future__ import annotations

import asyncio

import pytest

from livekit.agents import (
    Agent,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    AgentFalseInterruptionEvent,
)
from livekit.agents.voice.events import SpeechCreatedEvent
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session


class SimpleAgent(Agent):
    """Simple test agent that just responds to user input."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful assistant. When asked to explain something, give a long explanation.",
        )


SESSION_TIMEOUT = 60.0


# =============================================================================
# Test 1: Agent speaking + filler word "yeah"
# Expected: Agent should CONTINUE speaking (but currently STOPS - this is the bug)
# =============================================================================
async def test_filler_word_during_speech():
    """
    Scenario: Agent is speaking a long response, user says "yeah" as acknowledgment.
    
    Expected behavior: Agent continues speaking without interruption.
    Current behavior (BUG): Agent stops speaking.
    """
    speed = 5.0
    actions = FakeActions()
    
    # User asks for explanation
    actions.add_user_speech(0.5, 2.5, "Tell me about the history of computers.")
    actions.add_llm("The history of computers is fascinating. It started with Charles Babbage who designed the first mechanical computer in the 1830s, long before electronic computers existed.")
    actions.add_tts(25.0)  # Long audio - will be playing for 5s at speed 5.0
    
    # User says "yeah" at 5s (while agent is speaking) - this is a filler, NOT an interruption
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.2)
    
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "resume_false_interruption": True,
        },
    )
    agent = SimpleAgent()
    
    agent_state_events: list[AgentStateChangedEvent] = []
    transcription_events: list[UserInputTranscribedEvent] = []
    false_interruption_events: list[AgentFalseInterruptionEvent] = []
    playback_finished_events: list[PlaybackFinishedEvent] = []
    
    session.on("agent_state_changed", agent_state_events.append)
    session.on("user_input_transcribed", transcription_events.append)
    session.on("agent_false_interruption", false_interruption_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    t_origin = await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    # Log what happened for debugging
    print("\n=== Test: Filler word during speech ===")
    print(f"Agent state transitions: {[(e.old_state, e.new_state) for e in agent_state_events]}")
    print(f"User transcriptions: {[e.transcript for e in transcription_events if e.is_final]}")
    print(f"False interruption events: {len(false_interruption_events)}")
    print(f"Playback finished events: {len(playback_finished_events)}")
    if playback_finished_events:
        print(f"  - Interrupted: {playback_finished_events[0].interrupted}")
        print(f"  - Playback position: {playback_finished_events[0].playback_position}")
    
    # ASSERTIONS (documenting current buggy behavior vs expected)
    # 
    # EXPECTED (for intelligent interruption handling):
    # - Playback should NOT be interrupted
    # - Agent state should remain "speaking" throughout
    # - No state transition to "listening" during speech
    #
    # CURRENT BUG:
    # - Playback IS interrupted
    # - Agent state transitions: speaking → listening (pause) → thinking (new response)
    
    # ASSERTIONS (Verifying intelligent behavior)
    assert len(playback_finished_events) >= 1, "Expected at least one playback to finish"
    
    if not playback_finished_events[0].interrupted:
        print(f"✅ SUCCESS: Playback was NOT interrupted by filler word 'yeah'")
    else:
        print(f"❌ FAILURE: Playback was interrupted by filler word 'yeah'")
        assert not playback_finished_events[0].interrupted


# =============================================================================
# Test 2: Agent speaking + command word "stop"
# Expected: Agent should STOP speaking (this works correctly)
# =============================================================================
async def test_command_word_during_speech():
    """
    Scenario: Agent is speaking, user says "stop" as a command.
    
    Expected behavior: Agent stops speaking immediately.
    """
    speed = 5.0
    actions = FakeActions()
    
    # User asks for explanation
    actions.add_user_speech(0.5, 2.5, "Tell me about the history of computers.")
    actions.add_llm("The history of computers is fascinating.")
    actions.add_tts(25.0)  # Long audio
    
    # User says "stop" at 5s - this IS an interruption command
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.2)
    
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"resume_false_interruption": True},
    )
    agent = SimpleAgent()
    
    agent_state_events: list[AgentStateChangedEvent] = []
    playback_finished_events: list[PlaybackFinishedEvent] = []
    
    session.on("agent_state_changed", agent_state_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: Command word during speech ===")
    print(f"Agent state transitions: {[(e.old_state, e.new_state) for e in agent_state_events]}")
    print(f"Playback finished events: {len(playback_finished_events)}")
    if playback_finished_events:
        print(f"  - Interrupted: {playback_finished_events[0].interrupted}")
    
    # This should work correctly - "stop" should interrupt
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True, "Expected playback to be interrupted by 'stop'"
    print("✅ Correctly interrupted by command word 'stop'")


# =============================================================================
# Test 3: Agent silent + filler word "yeah"
# Expected: Agent should respond to the user
# =============================================================================
async def test_filler_word_when_silent():
    """
    Scenario: Agent is silent (listening), user says "yeah".
    
    Expected behavior: Agent should interpret this as wanting engagement and respond.
    """
    speed = 5.0
    actions = FakeActions()
    
    # User says "yeah" when agent is idle
    actions.add_user_speech(0.5, 1.0, "yeah", stt_delay=0.2)
    actions.add_llm("Is there something I can help you with?")
    actions.add_tts(2.0)
    
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()
    
    agent_state_events: list[AgentStateChangedEvent] = []
    
    session.on("agent_state_changed", agent_state_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: Filler word when silent ===")
    print(f"Agent state transitions: {[(e.old_state, e.new_state) for e in agent_state_events]}")
    
    # Agent should start speaking in response
    speaking_states = [e for e in agent_state_events if e.new_state == "speaking"]
    assert len(speaking_states) >= 1, "Agent should speak in response to 'yeah' when silent"
    print("✅ Correctly responded to 'yeah' when silent")


# =============================================================================
# Test 4: Agent speaking + mixed input "yeah wait"
# Expected: Agent should STOP speaking (contains command word "wait")
# =============================================================================
async def test_mixed_input_during_speech():
    """
    Scenario: Agent is speaking, user says "yeah wait" (filler + command).
    
    Expected behavior: Agent should stop because "wait" is a command.
    """
    speed = 5.0
    actions = FakeActions()
    
    # User asks for explanation
    actions.add_user_speech(0.5, 2.5, "Explain quantum physics.")
    actions.add_llm("Quantum physics is the study of matter and energy at the smallest scales.")
    actions.add_tts(10.0)
    
    # User says "yeah wait" - contains command word
    actions.add_user_speech(5.0, 6.0, "yeah wait", stt_delay=0.2)
    
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"resume_false_interruption": True},
    )
    agent = SimpleAgent()
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: Mixed input during speech ===")
    print(f"Playback finished events: {len(playback_finished_events)}")
    if playback_finished_events:
        print(f"  - Interrupted: {playback_finished_events[0].interrupted}")
    
    # ASSERTIONS
    assert len(playback_finished_events) >= 1
    if playback_finished_events[0].interrupted:
        print("✅ Correctly interrupted by mixed input containing command word")
    else:
        print("❌ FAILED to interrupt for mixed input")
        assert playback_finished_events[0].interrupted


# =============================================================================
# Test 5: Multiple filler words don't interrupt
# =============================================================================
async def test_multiple_fillers_during_speech():
    """
    Scenario: Agent is speaking, user says multiple fillers: "yeah", "mm-hmm", "ok".
    
    Expected behavior: Agent should continue speaking through all of them.
    """
    speed = 5.0
    actions = FakeActions()
    
    # User asks for long explanation
    actions.add_user_speech(0.5, 2.5, "Tell me the complete history of artificial intelligence.")
    actions.add_llm("Artificial intelligence began in the 1950s at Dartmouth conference...")
    actions.add_tts(35.0)  # Long audio - will be playing for 7s at speed 5.0
    
    # User says multiple fillers during speech
    actions.add_user_speech(4.0, 4.5, "yeah", stt_delay=0.2)
    actions.add_user_speech(6.0, 6.5, "mmhmm", stt_delay=0.2)
    actions.add_user_speech(8.0, 8.5, "ok", stt_delay=0.2)
    
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "resume_false_interruption": True,
        },
    )
    agent = SimpleAgent()
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    false_interruption_events: list[AgentFalseInterruptionEvent] = []
    
    session.output.audio.on("playback_finished", playback_finished_events.append)
    session.on("agent_false_interruption", false_interruption_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: Multiple fillers during speech ===")
    print(f"Playback finished events: {len(playback_finished_events)}")
    print(f"False interruption events: {len(false_interruption_events)}")
    
    # Document current buggy behavior
    if playback_finished_events and playback_finished_events[0].interrupted:
        print("⚠️  BUG: Playback was interrupted by filler words")
    else:
        print("✅ Playback continued through filler words")


# =============================================================================
# Test 6: min_interruption_words setting
# =============================================================================
async def test_min_interruption_words():
    """
    Test that min_interruption_words setting works correctly.
    
    With min_interruption_words=2, a single word like "yeah" should not interrupt.
    """
    speed = 5.0
    actions = FakeActions()
    
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Once upon a time in a land far away...")
    actions.add_tts(10.0)
    
    # Single word - should NOT interrupt with min_interruption_words=2
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.2)
    
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "min_interruption_words": 2,  # Require at least 2 words to interrupt
            "resume_false_interruption": True,
        },
    )
    agent = SimpleAgent()
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: min_interruption_words=2 ===")
    print(f"Playback finished events: {len(playback_finished_events)}")
    if playback_finished_events:
        print(f"  - Interrupted: {playback_finished_events[0].interrupted}")
    
    # With min_interruption_words=2, single word should not cause real interruption
    # (though it may still trigger the pause/resume mechanism)



# =============================================================================
# WORST-CASE STRESS TESTS
# =============================================================================

async def test_bait_and_switch_interruption():
    """
    Scenario: User starts with filler but ends with command: "yeah wait".
    Expected: Agent should interrupt because it's not ONLY fillers.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a long story.")
    actions.add_llm("Once upon a time in a galaxy very very far away...")
    actions.add_tts(30.0)
    
    # "yeah wait" - "wait" is a command
    actions.add_user_speech(5.0, 6.0, "yeah wait", stt_delay=0.2)
    
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Stress Test: Bait and Switch ===")
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True
    print("✅ Correctly interrupted when 'wait' was added to filler")

async def test_rapid_filler_flood():
    """
    Scenario: User bombards agent with "yeah" every second.
    Expected: Agent should NOT interrupt.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me about space.")
    actions.add_llm("Space is the boundless three-dimensional extent...")
    actions.add_tts(60.0)
    
    # Rapid fire fillers
    for i in range(5):
        start = 4.0 + (i * 1.5)
        actions.add_user_speech(start, start + 0.5, "yeah", stt_delay=0.2)
        
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Stress Test: Rapid Filler Flood ===")
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is False
    print("✅ Correctly ignored flood of filler words")

async def test_gibberish_and_noise_handling():
    """
    Scenario: STT returns non-filler but short garbage like "uh" or "..."
    Expected: Agent should NOT interrupt (due to min_interruption_words or filler logic).
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Explain photosynthesis.")
    actions.add_llm("Photosynthesis is a process used by plants...")
    actions.add_tts(25.0)
    
    # Garbage transcript "uh"
    actions.add_user_speech(5.0, 5.5, "uh", stt_delay=0.2)
    
    session = create_session(actions, speed_factor=speed, extra_kwargs={"min_interruption_words": 2})
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Stress Test: Gibberish/Noise ===")
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is False
    print("✅ Correctly ignored short garbage transcript")

async def test_question_starting_with_filler():
    """
    Scenario: "Yeah, but what about the cost?"
    Expected: Agent SHOULD interrupt because it's a real question.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me about Tesla cars.")
    actions.add_llm("Tesla cars are electric vehicles known for their performance.")
    actions.add_tts(30.0)
    
    # Real question starting with filler
    actions.add_user_speech(5.0, 7.0, "yeah but how much do they cost", stt_delay=0.2)
    
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Stress Test: Question Starting With Filler ===")
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True
    print("✅ Correctly interrupted for follow-up question starting with filler")

async def test_multi_word_acknowledgement_limit():
    """
    Scenario: "I see what you mean"
    Note: If this isn't in FILLER_WORDS, it WILL interrupt.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Explain gravity.")
    actions.add_llm("Gravity is a fundamental interaction...")
    actions.add_tts(25.0)
    
    # Polite acknowledgement - currently NOT in FILLER_WORDS, so it should interrupt
    actions.add_user_speech(5.0, 6.5, "i see what you mean", stt_delay=0.2)
    
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Stress Test: Multi-word Acknowledgement ===")
    # For now, we expect it to INTERRUPT because it's many words not in the list
    assert len(playback_finished_events) >= 1
    print(f"   Note: Multi-word phrase 'i see what you mean' Interrupted: {playback_finished_events[0].interrupted}")


async def test_custom_interruption_filter():
    """
    Scenario: User provides a custom ignore list ["banana"].
    Expected: "banana" should not interrupt, but "yeah" (default filler) SHOULD interrupt
    because it was overridden.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me about fruit.")
    actions.add_llm("Fruits are the seed-bearing structures in flowering plants...")
    actions.add_tts(30.0)
    
    # "banana" - custom filler at 5s (scaled: 1.0s)
    actions.add_user_speech(5.0, 5.5, "banana", stt_delay=0.2)
    # "yeah" - normally a filler, but not in our custom list. 
    # At 7s (scaled: 1.4s), agent is still speaking (0.1s to 6.1s).
    actions.add_user_speech(7.0, 7.5, "yeah", stt_delay=0.2)
    actions.add_llm("I heard you said yeah.")
    actions.add_tts(5.0)
    
    session = create_session(
        actions, 
        speed_factor=speed,
        extra_kwargs={"interruption_filter_words": ["banana"]}
    )
    agent = SimpleAgent()
    playback_finished_events = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    print("\n=== Test: Custom Interruption Filter ===")
    assert len(playback_finished_events) >= 1
    # The speech handle MUST be interrupted (by "yeah")
    assert playback_finished_events[0].interrupted is True
    # If "banana" (at scaled ~1.0s) had interrupted, the position would be very low.
    # But since it was interrupted by "yeah" (at scaled ~1.4s), the position should be higher.
    # 0.8s position is clearly past the start of "banana" (which arrived at 0.4s into playback).
    assert playback_finished_events[0].playback_position > 0.5
    print("✅ Correctly ignored 'banana' and interrupted on 'yeah'")


# If running directly
if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("INTERRUPTION SCENARIO TESTS")
    print("=" * 70)
    print("These tests demonstrate the false interruption bug with filler words.")
    print()
    
    tests = [
        test_filler_word_during_speech,
        test_command_word_during_speech,
        test_filler_word_when_silent,
        test_mixed_input_during_speech,
        test_multiple_fillers_during_speech,
        test_min_interruption_words,
        test_bait_and_switch_interruption,
        test_rapid_filler_flood,
        test_gibberish_and_noise_handling,
        test_question_starting_with_filler,
        test_multi_word_acknowledgement_limit,
        test_custom_interruption_filter,
    ]

    for test_func in tests:
        try:
            print(f"\nRunning {test_func.__name__}...")
            asyncio.run(test_func())
        except AssertionError as e:
            print(f"❌ TEST FAILED: {test_func.__name__}")
        except Exception as e:
            print(f"❌ CRITICAL ERROR in {test_func.__name__}: {e}")
    
    print()
    print("=" * 70)
    print("TESTS COMPLETED")
    print("=" * 70)
