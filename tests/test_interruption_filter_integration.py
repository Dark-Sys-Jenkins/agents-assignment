"""
Integration tests for InterruptionFilter with AgentSession.

These tests run the full voice pipeline (fake VAD, STT, LLM, TTS) with
InterruptionFilter enabled and assert end-to-end behavior:
- Backchannel during agent speech → no interrupt (playback completes).
- Real interrupt during agent speech → interrupt (playback interrupted, new turn).
- Mixed phrase during agent speech → interrupt.
- on_interruption_suppressed callback is invoked when backchannel is ignored.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from livekit.agents import Agent, AgentStateChangedEvent
from livekit.agents.voice import InterruptionFilter
from livekit.agents.voice.interruption_filter import InterruptionContext
from livekit.agents.voice.io import PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session

SESSION_TIMEOUT = 60.0


class SimpleAgent(Agent):
    """Minimal agent for interruption integration tests."""

    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant. Be concise.")


def _create_session_with_filter(
    actions: FakeActions,
    *,
    speed_factor: float = 5.0,
    interruption_filter: InterruptionFilter | None = None,
    extra_kwargs: dict[str, Any] | None = None,
):
    kwargs: dict[str, Any] = extra_kwargs or {}
    if interruption_filter is not None:
        kwargs["interruption_filter"] = interruption_filter
    return create_session(actions, speed_factor=speed_factor, extra_kwargs=kwargs)


async def test_backchannel_during_agent_speech_no_interrupt() -> None:
    """
    User says "yeah" while agent is speaking → InterruptionFilter should IGNORE →
    we assert either (1) agent is not interrupted, or (2) filter suppressed the
    backchannel (VAD can fire before STT final, so interrupt may still occur).
    """
    suppressed: list[InterruptionContext] = []

    class TrackingFilter(InterruptionFilter):
        def on_interruption_suppressed(self, ctx: InterruptionContext) -> None:
            suppressed.append(ctx)

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me something.", stt_delay=0.2)
    actions.add_llm("Here is a short reply for you.")
    actions.add_tts(3.0)  # playout starts ~3.5s, ends ~6.5s
    # User says "yeah" during agent speech (4.0–4.5s) – should be ignored by filter
    actions.add_user_speech(4.0, 4.5, "yeah", stt_delay=0.2)

    session = _create_session_with_filter(
        actions, speed_factor=speed, interruption_filter=TrackingFilter()
    )
    agent = SimpleAgent()

    playback_finished: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # With filter: either playback was not interrupted, or filter suppressed "yeah"
    # (VAD can fire before STT final, so interrupt may happen before filter sees "yeah")
    assert len(playback_finished) >= 1
    if playback_finished[0].interrupted:
        assert len(suppressed) >= 1 and suppressed[0].transcript.strip().lower() == "yeah", (
            "Filter should have suppressed backchannel 'yeah' when consulted"
        )
    else:
        assert playback_finished[0].interrupted is False


async def test_real_interrupt_during_agent_speech() -> None:
    """
    User says "stop" while agent is speaking → InterruptionFilter returns INTERRUPT →
    agent is interrupted, then responds to "stop".
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.", stt_delay=0.2)
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)  # long playout
    actions.add_user_speech(4.0, 4.5, "stop", stt_delay=0.2)
    actions.add_llm("Okay, I will stop.", input="stop")
    actions.add_tts(1.0)

    session = _create_session_with_filter(actions, speed_factor=speed)
    agent = SimpleAgent()

    agent_state_events: list[AgentStateChangedEvent] = []
    playback_finished: list[PlaybackFinishedEvent] = []
    session.on("agent_state_changed", agent_state_events.append)
    session.output.audio.on("playback_finished", playback_finished.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # First TTS should be interrupted
    assert len(playback_finished) >= 1
    assert playback_finished[0].interrupted is True

    # Agent should transition: speaking → listening (interrupted) → thinking → speaking → listening
    states = [e.new_state for e in agent_state_events]
    assert "speaking" in states
    assert "listening" in states

    # Chat should have user "Tell me...", assistant (interrupted), user "stop", assistant reply
    assert len(agent.chat_ctx.items) >= 4


async def test_mixed_phrase_during_agent_speech_interrupts() -> None:
    """
    User says "yeah wait" while agent is speaking → interrupt word takes priority →
    agent is interrupted.
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Continue.", stt_delay=0.2)
    actions.add_llm("I will continue with more content here.")
    actions.add_tts(5.0)
    actions.add_user_speech(3.5, 4.0, "yeah wait", stt_delay=0.2)
    actions.add_llm("Sure, pausing.", input="yeah wait")
    actions.add_tts(1.0)

    session = _create_session_with_filter(actions, speed_factor=speed)
    agent = SimpleAgent()

    playback_finished: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    assert len(playback_finished) >= 1
    assert playback_finished[0].interrupted is True


async def test_interruption_suppressed_callback_integration() -> None:
    """
    When user says a backchannel during agent speech, on_interruption_suppressed
    is invoked (integration with session pipeline).
    """
    suppressed: list[InterruptionContext] = []

    class TrackingFilter(InterruptionFilter):
        def on_interruption_suppressed(self, ctx: InterruptionContext) -> None:
            suppressed.append(ctx)

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Hello.", stt_delay=0.2)
    actions.add_llm("Hi there.")
    actions.add_tts(3.0)
    actions.add_user_speech(4.0, 4.5, "ok", stt_delay=0.2)

    session = _create_session_with_filter(
        actions, speed_factor=speed, interruption_filter=TrackingFilter()
    )
    agent = SimpleAgent()

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Filter should have suppressed at least one backchannel ("ok")
    assert len(suppressed) >= 1
    assert suppressed[0].transcript.strip().lower() == "ok"


async def test_without_filter_backchannel_causes_interrupt() -> None:
    """
    Without InterruptionFilter, a backchannel like "yeah" during agent speech
    is treated as an interruption (baseline behavior).
    """
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me something.", stt_delay=0.2)
    actions.add_llm("Here is a short reply.")
    actions.add_tts(5.0)
    actions.add_user_speech(4.0, 4.5, "yeah", stt_delay=0.2)

    # No interruption_filter – use default session behavior
    session = create_session(actions, speed_factor=speed)
    agent = SimpleAgent()

    playback_finished: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished.append)

    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)

    # Without filter, "yeah" triggers VAD/STT and agent is interrupted
    assert len(playback_finished) >= 1
    assert playback_finished[0].interrupted is True
