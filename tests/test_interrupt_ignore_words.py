"""Tests for interrupt_ignore_words functionality.

These tests verify that the agent correctly handles backchanneling words
like "yeah", "ok", "hmm" when the agent is speaking vs. when silent.
"""

from __future__ import annotations

import asyncio

import pytest

from livekit.agents import Agent, AgentStateChangedEvent
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session


class SimpleAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")


SESSION_TIMEOUT = 60.0


def check_timestamp(
    t_event: float, t_target: float, *, speed_factor: float = 1.0, max_abs_diff: float = 0.5
) -> None:
    t_event = t_event * speed_factor
    assert abs(t_event - t_target) <= max_abs_diff, (
        f"event timestamp {t_event} is not within {max_abs_diff} of target {t_target}"
    )


async def test_ignore_backchanneling_while_speaking() -> None:
    """Test that agent ignores 'yeah', 'ok', 'hmm' while speaking and continues without pause."""
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.1)
    actions.add_user_speech(7.0, 7.3, "ok", stt_delay=0.1)
    actions.add_user_speech(9.0, 9.2, "hmm", stt_delay=0.1)
    # Agent should NOT be interrupted by these

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": ["yeah", "ok", "hmm", "right", "uh-huh"],
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    agent_state_events: list[AgentStateChangedEvent] = []
    session.on("agent_state_changed", agent_state_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # The agent should complete the full 10s audio without interruption
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
    check_timestamp(playback_finished_events[0].playback_position, 10.0, speed_factor=speed)


async def test_interrupt_on_stop_command() -> None:
    """Test that agent stops immediately when user says 'stop' or 'wait'."""
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)  # playout starts at 3.5s
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.1)
    # Agent SHOULD be interrupted by "stop"

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": ["yeah", "ok", "hmm"],
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Agent should be interrupted
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True


async def test_mixed_input_with_command() -> None:
    """Test that 'yeah wait' causes interruption because it contains 'wait'."""
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)  # playout starts at 3.5s
    actions.add_user_speech(5.0, 5.8, "yeah wait", stt_delay=0.1)
    # Agent SHOULD be interrupted because "wait" is an interrupt command

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": ["yeah", "ok", "hmm"],
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Agent should be interrupted due to "wait"
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True


async def test_respond_to_backchanneling_when_silent() -> None:
    """Test that agent responds to 'yeah' when it's not speaking (valid input)."""
    speed = 5.0
    actions = FakeActions()
    # Agent says something short
    actions.add_user_speech(0.5, 1.5, "Hello")
    actions.add_llm("Hi! Are you ready?")
    actions.add_tts(2.0)  # ends at ~4.5s
    # User says "yeah" after agent finishes speaking (agent is silent)
    actions.add_user_speech(5.0, 5.3, "yeah", stt_delay=0.1)
    # Agent should process this as valid input
    actions.add_llm("Great, let's continue!", input="yeah")
    actions.add_tts(2.0)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": ["yeah", "ok", "hmm"],
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Agent should have played both responses (not ignored "yeah" when silent)
    assert len(playback_finished_events) == 2
    assert playback_finished_events[0].interrupted is False
    assert playback_finished_events[1].interrupted is False


async def test_empty_ignore_words_list() -> None:
    """Test that empty ignore list allows normal interruption behavior."""
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.1)
    # "yeah" should cause interruption since empty ignore list

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": [],  # empty list
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # With empty ignore list, "yeah" should cause interruption
    assert len(playback_finished_events) >= 1
    assert playback_finished_events[0].interrupted is True


async def test_multiple_backchanneling_words() -> None:
    """Test that multiple ignore words in sequence are all ignored."""
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me about history.")
    actions.add_llm("History is fascinating... and that's the story.")
    actions.add_tts(15.0)  # long audio
    # Multiple backchanneling words
    actions.add_user_speech(4.0, 4.3, "ok", stt_delay=0.1)
    actions.add_user_speech(6.0, 6.3, "yeah", stt_delay=0.1)
    actions.add_user_speech(8.0, 8.4, "uh-huh", stt_delay=0.1)
    actions.add_user_speech(10.0, 10.3, "right", stt_delay=0.1)

    session = create_session(
        actions,
        speed_factor=speed,
        extra_kwargs={
            "interrupt_ignore_words": ["yeah", "ok", "uh-huh", "right", "hmm"],
        },
    )
    agent = SimpleAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # All backchanneling should be ignored, audio completes uninterrupted
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
