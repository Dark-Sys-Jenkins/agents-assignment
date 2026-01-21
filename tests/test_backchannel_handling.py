from __future__ import annotations

import asyncio

import pytest

from livekit.agents import Agent
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
from livekit.agents.voice.interruption_filter import (
    DEFAULT_BACKCHANNEL_WORDS,
    DEFAULT_INTERRUPT_WORDS,
    is_backchannel_only,
    should_interrupt_while_speaking,
)
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session


class NoopAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        return


SESSION_TIMEOUT = 60.0


def _user_messages(agent: Agent) -> list[str]:
    return [
        item.text_content
        for item in agent.chat_ctx.items
        if item.type == "message" and item.role == "user"
    ]


def test_backchannel_classifier() -> None:
    assert is_backchannel_only("Okay... yeah... uh-huh", backchannel_words=DEFAULT_BACKCHANNEL_WORDS)
    assert is_backchannel_only("Yes", backchannel_words=DEFAULT_BACKCHANNEL_WORDS)
    assert is_backchannel_only("Mhmm", backchannel_words=DEFAULT_BACKCHANNEL_WORDS)
    assert is_backchannel_only("Hmmm", backchannel_words=DEFAULT_BACKCHANNEL_WORDS)
    assert not should_interrupt_while_speaking(
        "Okay... yeah... uh-huh",
        backchannel_words=DEFAULT_BACKCHANNEL_WORDS,
        interrupt_words=DEFAULT_INTERRUPT_WORDS,
    )
    assert not should_interrupt_while_speaking(
        "Yes",
        backchannel_words=DEFAULT_BACKCHANNEL_WORDS,
        interrupt_words=DEFAULT_INTERRUPT_WORDS,
    )
    assert not should_interrupt_while_speaking(
        "Mhmm",
        backchannel_words=DEFAULT_BACKCHANNEL_WORDS,
        interrupt_words=DEFAULT_INTERRUPT_WORDS,
    )

    assert should_interrupt_while_speaking(
        "No stop",
        backchannel_words=DEFAULT_BACKCHANNEL_WORDS,
        interrupt_words=DEFAULT_INTERRUPT_WORDS,
    )
    assert should_interrupt_while_speaking(
        "Yeah wait a second",
        backchannel_words=DEFAULT_BACKCHANNEL_WORDS,
        interrupt_words=DEFAULT_INTERRUPT_WORDS,
    )


@pytest.mark.asyncio
async def test_backchannel_ignored_while_agent_speaking() -> None:
    """
    Scenario A:
    Agent speaking; user says "Okay... yeah... uh-huh" -> do not interrupt, do not create a user turn.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.2, "Okay... yeah... uh-huh", stt_delay=0.0)

    session = create_session(actions, speed_factor=speed)
    agent = NoopAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
    assert _user_messages(agent) == ["Tell me a story."]


@pytest.mark.asyncio
async def test_backchannel_is_not_interrupted_when_stt_lags_gate_timeout() -> None:
    """
    Regression: if STT lags the gate timeout, do not fall back to a VAD-only interruption.

    This would otherwise reintroduce "hiccups" for short backchannels that don't produce an
    immediate transcript.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)
    # Make STT slightly slower than the gate timeout so the pending timer fires before any transcript.
    actions.add_user_speech(5.0, 5.2, "Yeah", stt_delay=0.4)

    session = create_session(actions, speed_factor=speed)
    agent = NoopAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
    assert _user_messages(agent) == ["Tell me a story."]


@pytest.mark.asyncio
async def test_backchannel_is_valid_input_while_agent_silent() -> None:
    """
    Scenario B:
    Agent silent; user says "Yeah" -> treat as input and respond normally.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 1.0, "Yeah", stt_delay=0.0)
    actions.add_llm("Great, let's continue.")
    actions.add_tts(1.0)

    session = create_session(actions, speed_factor=speed)
    agent = NoopAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
    assert _user_messages(agent) == ["Yeah"]


@pytest.mark.asyncio
async def test_mixed_input_interrupts_while_agent_speaking() -> None:
    """
    Scenario C:
    Agent speaking; user says "Yeah wait a second" -> interrupt.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.")
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.2, "Yeah wait a second", stt_delay=0.0)

    session = create_session(actions, speed_factor=speed)
    agent = NoopAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True
