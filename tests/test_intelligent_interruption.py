"""
Tests for intelligent interruption handling.

This module contains:
1. Unit tests for the InterruptionClassifier
2. Integration tests verifying the full interruption handling behavior

Test scenarios from the assignment:
- Agent speaking + "yeah/ok/hmm" → IGNORE (no interruption)
- Agent speaking + "stop/wait/no" → INTERRUPT
- Agent speaking + "yeah wait a second" → INTERRUPT (mixed utterance)
- Agent silent + "yeah/ok" → Normal response (handled by framework)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Add examples directory to path so we can import the classifier
sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "voice_agents"))

from interruption_classifier import (
    InterruptionClassifier,
    InterruptionClassifierConfig,
    InterruptionIntent,
)

from livekit.agents import (
    Agent,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session


# =============================================================================
# Unit Tests for InterruptionClassifier
# =============================================================================


class TestInterruptionClassifier:
    """Unit tests for the InterruptionClassifier."""

    def test_default_config(self):
        """Test that default configuration is created correctly."""
        config = InterruptionClassifierConfig()
        assert "yeah" in config.backchannel_words
        assert "stop" in config.command_phrases
        assert config.interrupt_on_non_backchannel is True

    def test_single_word_backchannel(self):
        """Test classification of single-word backchannels."""
        classifier = InterruptionClassifier()

        # Standard backchannels should be ignored
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("okay") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("right") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("sure") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_multi_word_backchannel(self):
        """Test classification of multi-word backchannels."""
        classifier = InterruptionClassifier()

        # Multi-word backchannels
        assert classifier.classify("uh huh") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("uh-huh") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("mm hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("mm-hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("i see") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("got it") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_backchannel_case_insensitive(self):
        """Test that backchannel detection is case-insensitive."""
        classifier = InterruptionClassifier()

        assert classifier.classify("Yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("YEAH") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("OK") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("Uh Huh") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_backchannel_with_punctuation(self):
        """Test that punctuation doesn't affect backchannel detection."""
        classifier = InterruptionClassifier()

        assert classifier.classify("yeah.") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok!") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("hmm...") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("yeah?") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_command_detection(self):
        """Test detection of interruption commands."""
        classifier = InterruptionClassifier()

        assert classifier.classify("stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("no") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("cancel") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("hold on") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("pause") == InterruptionIntent.INTERRUPT_COMMAND

    def test_command_case_insensitive(self):
        """Test that command detection is case-insensitive."""
        classifier = InterruptionClassifier()

        assert classifier.classify("Stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("STOP") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("Wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("NO") == InterruptionIntent.INTERRUPT_COMMAND

    def test_command_with_punctuation(self):
        """Test that commands are detected with punctuation."""
        classifier = InterruptionClassifier()

        assert classifier.classify("stop!") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("wait.") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("no!") == InterruptionIntent.INTERRUPT_COMMAND

    def test_mixed_utterance_with_command(self):
        """Test that mixed utterances containing commands are classified as interrupts."""
        classifier = InterruptionClassifier()

        # Command takes priority even with backchannels
        assert classifier.classify("yeah wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("yeah wait a second") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("ok stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("hmm no") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("ok but stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("yeah but wait") == InterruptionIntent.INTERRUPT_COMMAND

    def test_non_backchannel_content(self):
        """Test that non-backchannel content triggers INTERRUPT_OTHER."""
        classifier = InterruptionClassifier()

        # Regular speech should interrupt
        assert classifier.classify("hello") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("what about") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("I have a question") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("tell me more") == InterruptionIntent.INTERRUPT_OTHER

    def test_empty_input(self):
        """Test handling of empty input."""
        classifier = InterruptionClassifier()

        assert classifier.classify("") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("   ") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify(None) == InterruptionIntent.IGNORE_BACKCHANNEL  # type: ignore

    def test_should_interrupt_convenience_method(self):
        """Test the should_interrupt convenience method."""
        classifier = InterruptionClassifier()

        # Should NOT interrupt
        assert classifier.should_interrupt("yeah") is False
        assert classifier.should_interrupt("ok") is False
        assert classifier.should_interrupt("uh huh") is False

        # Should interrupt
        assert classifier.should_interrupt("stop") is True
        assert classifier.should_interrupt("wait") is True
        assert classifier.should_interrupt("hello there") is True
        assert classifier.should_interrupt("yeah wait") is True

    def test_custom_config(self):
        """Test classifier with custom configuration."""
        config = InterruptionClassifierConfig(
            backchannel_words={"yep", "cool"},
            command_phrases={"halt", "cease"},
            interrupt_on_non_backchannel=False,
        )
        classifier = InterruptionClassifier(config)

        # Custom backchannels
        assert classifier.classify("yep") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("cool") == InterruptionIntent.IGNORE_BACKCHANNEL

        # Default backchannels no longer recognized
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL  # Because interrupt_on_non_backchannel=False

        # Custom commands
        assert classifier.classify("halt") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("cease") == InterruptionIntent.INTERRUPT_COMMAND

        # Default commands no longer recognized
        assert classifier.classify("stop") == InterruptionIntent.IGNORE_BACKCHANNEL  # Because interrupt_on_non_backchannel=False

    def test_interrupt_on_non_backchannel_disabled(self):
        """Test with interrupt_on_non_backchannel disabled."""
        config = InterruptionClassifierConfig(interrupt_on_non_backchannel=False)
        classifier = InterruptionClassifier(config)

        # Commands still interrupt
        assert classifier.classify("stop") == InterruptionIntent.INTERRUPT_COMMAND

        # Non-backchannel content is ignored (only commands interrupt)
        assert classifier.classify("hello") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("I have a question") == InterruptionIntent.IGNORE_BACKCHANNEL


# =============================================================================
# Integration Tests for Intelligent Interruption Handling
# =============================================================================


class TestAgentWithHandler(Agent):
    """Test agent that uses the intelligent interruption handler."""

    def __init__(self, classifier: InterruptionClassifier) -> None:
        super().__init__(instructions="You are a test assistant.")
        self.classifier = classifier
        self.interrupt_calls: list[str] = []
        self.ignored_backchannels: list[str] = []

    async def on_enter(self) -> None:
        pass

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        pass


SESSION_TIMEOUT = 60.0


def check_timestamp(
    t_event: float, t_target: float, *, speed_factor: float = 1.0, max_abs_diff: float = 0.5
) -> None:
    """Check if the event timestamp is within the target timestamp +/- max_abs_diff."""
    t_event = t_event * speed_factor
    assert abs(t_event - t_target) <= max_abs_diff, (
        f"event timestamp {t_event} is not within {max_abs_diff} of target {t_target}"
    )


async def test_backchannel_does_not_interrupt():
    """
    Test that backchannels while agent is speaking do NOT interrupt.

    Scenario:
    - User says "Tell me a story" (0.5-2.5s)
    - Agent produces long TTS (10s starting at ~3.5s)
    - While agent speaking, user says "yeah" (5.0-5.5s)

    Expected:
    - Playback completes WITHOUT interruption
    - Playback position equals full audio duration
    """
    speed = 5.0
    actions = FakeActions()

    # User asks for a story
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you. Once upon a time...")
    actions.add_tts(10.0)  # Long TTS output

    # User says "yeah" while agent is speaking (backchannel)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.2)

    # Create session with interruptions DISABLED (as per the intelligent handler approach)
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"allow_interruptions": False},
    )

    agent = TestAgentWithHandler(InterruptionClassifier())
    classifier = agent.classifier

    agent_state_events: list[AgentStateChangedEvent] = []
    playback_finished_events: list[PlaybackFinishedEvent] = []
    transcription_events: list[UserInputTranscribedEvent] = []

    session.on("agent_state_changed", agent_state_events.append)
    session.on("user_input_transcribed", transcription_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)

    # Register our intelligent interruption handler
    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if session.agent_state == "speaking":
            if classifier.should_interrupt(ev.transcript):
                agent.interrupt_calls.append(ev.transcript)
                session.interrupt(force=True)
            else:
                agent.ignored_backchannels.append(ev.transcript)

    session.on("user_input_transcribed", on_user_input_transcribed)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Verify backchannel was ignored
    assert "yeah" in agent.ignored_backchannels or any(
        "yeah" in bc for bc in agent.ignored_backchannels
    ), f"Backchannel 'yeah' should have been ignored, got: {agent.ignored_backchannels}"

    # Verify no interrupt was called for the backchannel
    assert not any(
        "yeah" in call and "wait" not in call.lower() and "stop" not in call.lower()
        for call in agent.interrupt_calls
    ), f"Backchannel should not have triggered interrupt: {agent.interrupt_calls}"

    # Verify playback was NOT interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False, (
        "Playback should NOT have been interrupted by backchannel"
    )

    # Verify full audio played
    check_timestamp(playback_finished_events[0].playback_position, 10.0, speed_factor=speed)


async def test_command_interrupts_while_speaking():
    """
    Test that commands while agent is speaking DO interrupt.

    Scenario:
    - User says "Tell me a story" (0.5-2.5s)
    - Agent produces long TTS (10s starting at ~3.5s)
    - While agent speaking, user says "stop" (5.0-5.5s)

    Expected:
    - Playback is interrupted
    - Agent state transitions to listening
    """
    speed = 5.0
    actions = FakeActions()

    # User asks for a story
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you. Once upon a time...")
    actions.add_tts(10.0)  # Long TTS output

    # User says "stop" while agent is speaking (command)
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.2)

    # Create session with interruptions DISABLED (we handle manually)
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"allow_interruptions": False},
    )

    agent = TestAgentWithHandler(InterruptionClassifier())
    classifier = agent.classifier

    agent_state_events: list[AgentStateChangedEvent] = []
    playback_finished_events: list[PlaybackFinishedEvent] = []

    session.on("agent_state_changed", agent_state_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)

    # Register our intelligent interruption handler
    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if session.agent_state == "speaking":
            if classifier.should_interrupt(ev.transcript):
                agent.interrupt_calls.append(ev.transcript)
                try:
                    session.interrupt(force=True)
                except RuntimeError:
                    pass  # May already be interrupted

    session.on("user_input_transcribed", on_user_input_transcribed)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Verify command triggered interrupt
    assert any(
        "stop" in call.lower() for call in agent.interrupt_calls
    ), f"Command 'stop' should have triggered interrupt: {agent.interrupt_calls}"

    # Verify playback WAS interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True, (
        "Playback SHOULD have been interrupted by command"
    )

    # Verify playback stopped early (not full duration)
    assert playback_finished_events[0].playback_position < 10.0 / speed * 0.8, (
        f"Playback should have stopped early, got position: {playback_finished_events[0].playback_position}"
    )


async def test_mixed_utterance_interrupts():
    """
    Test that mixed utterances (backchannel + command) DO interrupt.

    Scenario:
    - User says "Tell me a story" (0.5-2.5s)
    - Agent produces long TTS (10s starting at ~3.5s)
    - While agent speaking, user says "yeah wait a second" (5.0-6.0s)

    Expected:
    - Playback is interrupted (command takes priority)
    """
    speed = 5.0
    actions = FakeActions()

    # User asks for a story
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you. Once upon a time...")
    actions.add_tts(10.0)  # Long TTS output

    # User says "yeah wait a second" while agent is speaking (mixed)
    actions.add_user_speech(5.0, 6.0, "yeah wait a second", stt_delay=0.2)

    # Create session with interruptions DISABLED (we handle manually)
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"allow_interruptions": False},
    )

    agent = TestAgentWithHandler(InterruptionClassifier())
    classifier = agent.classifier

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    # Register our intelligent interruption handler
    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if session.agent_state == "speaking":
            if classifier.should_interrupt(ev.transcript):
                agent.interrupt_calls.append(ev.transcript)
                try:
                    session.interrupt(force=True)
                except RuntimeError:
                    pass

    session.on("user_input_transcribed", on_user_input_transcribed)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Verify mixed utterance triggered interrupt
    assert any(
        "wait" in call.lower() for call in agent.interrupt_calls
    ), f"Mixed utterance with 'wait' should have triggered interrupt: {agent.interrupt_calls}"

    # Verify playback WAS interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True, (
        "Playback SHOULD have been interrupted by mixed utterance containing command"
    )


async def test_multiple_backchannels_no_interrupt():
    """
    Test that multiple backchannels in sequence don't interrupt.

    Scenario:
    - User asks for explanation
    - Agent gives long response
    - User says "ok" then "yeah" then "uh huh" during speech

    Expected:
    - All backchannels ignored
    - Full playback completes
    """
    speed = 5.0
    actions = FakeActions()

    # User asks for explanation
    actions.add_user_speech(0.5, 2.5, "Explain quantum physics to me.")
    actions.add_llm("Quantum physics is a fascinating field of study...")
    actions.add_tts(15.0)  # Very long TTS output

    # Multiple backchannels while agent is speaking
    actions.add_user_speech(5.0, 5.3, "ok", stt_delay=0.1)
    actions.add_user_speech(7.0, 7.3, "yeah", stt_delay=0.1)
    actions.add_user_speech(9.0, 9.5, "uh huh", stt_delay=0.1)

    # Create session with interruptions DISABLED
    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"allow_interruptions": False},
    )

    agent = TestAgentWithHandler(InterruptionClassifier())
    classifier = agent.classifier

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    # Register our intelligent interruption handler
    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if session.agent_state == "speaking":
            if classifier.should_interrupt(ev.transcript):
                agent.interrupt_calls.append(ev.transcript)
                try:
                    session.interrupt(force=True)
                except RuntimeError:
                    pass
            else:
                agent.ignored_backchannels.append(ev.transcript)

    session.on("user_input_transcribed", on_user_input_transcribed)

    await asyncio.wait_for(run_session(session, agent, drain_delay=2.0), timeout=SESSION_TIMEOUT)

    # Verify all backchannels were ignored
    assert len(agent.ignored_backchannels) >= 2, (
        f"Expected at least 2 backchannels to be ignored, got: {agent.ignored_backchannels}"
    )

    # Verify no interrupts
    assert len(agent.interrupt_calls) == 0, (
        f"No interrupts should have been called for backchannels: {agent.interrupt_calls}"
    )

    # Verify playback was NOT interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False


async def test_non_backchannel_content_interrupts():
    """
    Test that genuine new content (not backchannel, not command) interrupts.

    Scenario:
    - Agent is speaking
    - User says "actually I have a different question"

    Expected:
    - Playback is interrupted (non-backchannel content)
    """
    speed = 5.0
    actions = FakeActions()

    # User asks initial question
    actions.add_user_speech(0.5, 2.5, "Tell me about dogs.")
    actions.add_llm("Dogs are wonderful companions. They have been...")
    actions.add_tts(10.0)

    # User interrupts with new content (not a command, not a backchannel)
    actions.add_user_speech(5.0, 6.0, "actually I want to know about cats", stt_delay=0.2)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={"allow_interruptions": False},
    )

    agent = TestAgentWithHandler(InterruptionClassifier())
    classifier = agent.classifier

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if session.agent_state == "speaking":
            if classifier.should_interrupt(ev.transcript):
                agent.interrupt_calls.append(ev.transcript)
                try:
                    session.interrupt(force=True)
                except RuntimeError:
                    pass

    session.on("user_input_transcribed", on_user_input_transcribed)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Verify non-backchannel content triggered interrupt
    assert len(agent.interrupt_calls) > 0, (
        f"Non-backchannel content should have triggered interrupt: {agent.interrupt_calls}"
    )

    # Verify playback WAS interrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True
