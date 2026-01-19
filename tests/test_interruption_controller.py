from __future__ import annotations

from livekit.agents.voice.interruption_controller import (
    InterruptionController,
    InterruptionDecision,
)


def _make_controller() -> InterruptionController:
    return InterruptionController(window_ms=250, active_threshold_ms=120)


def test_backchannel_while_speaking_ignored() -> None:
    ctrl = _make_controller()
    ctrl.set_agent_state("speaking")
    ctrl.on_user_activity(active=True, now=0.0)
    ctrl.on_user_activity(active=True, now=0.08)
    decision = ctrl.on_stt_text("yeah", is_final=True, now=0.14)
    assert decision == InterruptionDecision.IGNORE


def test_stop_while_speaking_interrupts() -> None:
    ctrl = _make_controller()
    ctrl.set_agent_state("speaking")
    ctrl.on_user_activity(active=True, now=0.0)
    ctrl.on_user_activity(active=True, now=0.1)
    decision = ctrl.on_stt_text("stop", is_final=True, now=0.13)
    assert decision == InterruptionDecision.INTERRUPT


def test_mixed_backchannel_interrupts() -> None:
    ctrl = _make_controller()
    ctrl.set_agent_state("speaking")
    ctrl.on_user_activity(active=True, now=0.0)
    ctrl.on_user_activity(active=True, now=0.12)
    decision = ctrl.on_stt_text("yeah wait a second", is_final=True, now=0.14)
    assert decision == InterruptionDecision.INTERRUPT


def test_backchannel_while_silent_responds() -> None:
    ctrl = _make_controller()
    ctrl.set_agent_state("silent")
    decision = ctrl.on_stt_text("yeah", is_final=True, now=0.05)
    assert decision == InterruptionDecision.RESPOND
