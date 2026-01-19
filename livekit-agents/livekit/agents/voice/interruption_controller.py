from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ..log import logger


class InterruptionDecision(str, Enum):
    IGNORE = "ignore"
    CANDIDATE = "candidate"
    INTERRUPT = "interrupt"
    RESPOND = "respond"


DEFAULT_IGNORE_BACKCHANNELS: list[str] = [
    "yeah",
    "yea",
    "ok",
    "okay",
    "hmm",
    "aha",
    "uh-huh",
    "uh huh",
    "right",
    "mm-hm",
    "mm hm",
    "mhm",
]

DEFAULT_INTERRUPT_KEYWORDS: list[str] = [
    "stop",
    "wait",
    "hold on",
    "cancel",
    "pause",
    "no",
    "listen",
    "actually",
    "scratch that",
]


@dataclass
class _ActivityPoint:
    timestamp: float
    active: bool


class InterruptionController:
    def __init__(
        self,
        *,
        window_ms: int = 250,
        active_threshold_ms: int = 120,
        ignore_backchannels: Iterable[str] = DEFAULT_IGNORE_BACKCHANNELS,
        interrupt_keywords: Iterable[str] = DEFAULT_INTERRUPT_KEYWORDS,
    ) -> None:
        self._window_s = max(window_ms, 10) / 1000.0
        self._active_threshold_ms = max(active_threshold_ms, 10)
        if self._active_threshold_ms > window_ms:
            self._active_threshold_ms = window_ms

        self._ignore_phrases = [self._normalize_text(p) for p in ignore_backchannels]
        self._ignore_phrase_tokens = [
            tuple(p.split()) for p in self._ignore_phrases if p
        ]
        self._interrupt_patterns = [
            re.compile(r"\b" + re.escape(self._normalize_text(p)) + r"\b")
            for p in interrupt_keywords
            if p
        ]

        self._activity: deque[_ActivityPoint] = deque()
        self._agent_speaking = False
        self._pending_interrupt_intent = False
        self._last_text: str = ""

    def set_agent_state(self, state: str) -> None:
        speaking = state == "speaking"
        if speaking == self._agent_speaking:
            return

        self._agent_speaking = speaking
        self._activity.clear()
        self._pending_interrupt_intent = False
        self._last_text = ""

    def on_user_activity(
        self,
        *,
        active: bool,
        now: float | None = None,
    ) -> InterruptionDecision:
        now = time.monotonic() if now is None else now
        self._activity.append(_ActivityPoint(timestamp=now, active=active))
        self._prune_activity(now)

        decision = InterruptionDecision.IGNORE
        active_ms = self._active_time_ms(now)
        sustained = active_ms >= self._active_threshold_ms

        if self._agent_speaking:
            if sustained:
                decision = (
                    InterruptionDecision.INTERRUPT
                    if self._pending_interrupt_intent
                    else InterruptionDecision.CANDIDATE
                )
        else:
            decision = InterruptionDecision.RESPOND

        logger.debug(
            "interruption_controller activity",
            extra={
                "agent_state": "speaking" if self._agent_speaking else "silent",
                "active": active,
                "active_ms": round(active_ms, 1),
                "window_ms": round(self._window_s * 1000, 1),
                "decision": decision.value,
            },
        )
        if decision == InterruptionDecision.INTERRUPT:
            self._pending_interrupt_intent = False
        return decision

    def on_stt_text(
        self,
        text: str,
        *,
        is_final: bool,
        now: float | None = None,
    ) -> InterruptionDecision:
        now = time.monotonic() if now is None else now
        normalized = self._normalize_text(text)
        self._last_text = normalized

        if not self._agent_speaking:
            decision = InterruptionDecision.RESPOND
        else:
            if self._contains_interrupt_keyword(normalized):
                self._pending_interrupt_intent = True
                active_ms = self._active_time_ms(now)
                if active_ms >= self._active_threshold_ms:
                    decision = InterruptionDecision.INTERRUPT
                else:
                    decision = InterruptionDecision.CANDIDATE
            elif self._is_only_backchannels(normalized):
                self._pending_interrupt_intent = False
                decision = InterruptionDecision.IGNORE
            else:
                self._pending_interrupt_intent = False
                decision = InterruptionDecision.IGNORE

        logger.debug(
            "interruption_controller stt",
            extra={
                "agent_state": "speaking" if self._agent_speaking else "silent",
                "text": text,
                "normalized": normalized,
                "is_final": is_final,
                "active_ms": round(self._active_time_ms(now), 1),
                "decision": decision.value,
            },
        )

        if decision == InterruptionDecision.INTERRUPT:
            self._pending_interrupt_intent = False
        return decision

    def _contains_interrupt_keyword(self, normalized: str) -> bool:
        if not normalized:
            return False
        for pattern in self._interrupt_patterns:
            if pattern.search(normalized):
                return True
        return False

    def _is_only_backchannels(self, normalized: str) -> bool:
        if not normalized:
            return True

        tokens = normalized.split()
        idx = 0
        while idx < len(tokens):
            matched = False
            for phrase_tokens in self._ignore_phrase_tokens:
                if tokens[idx : idx + len(phrase_tokens)] == list(phrase_tokens):
                    idx += len(phrase_tokens)
                    matched = True
                    break
            if not matched:
                return False
        return True

    def _normalize_text(self, text: str) -> str:
        cleaned = text.lower().replace("-", " ")
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _prune_activity(self, now: float) -> None:
        cutoff = now - self._window_s
        while len(self._activity) >= 2 and self._activity[1].timestamp <= cutoff:
            self._activity.popleft()
        if self._activity and self._activity[0].timestamp < cutoff:
            self._activity[0] = _ActivityPoint(timestamp=cutoff, active=self._activity[0].active)

    def _active_time_ms(self, now: float) -> float:
        if not self._activity:
            return 0.0

        active_s = 0.0
        for idx in range(len(self._activity) - 1):
            cur = self._activity[idx]
            nxt = self._activity[idx + 1]
            if cur.active:
                active_s += max(0.0, nxt.timestamp - cur.timestamp)

        last = self._activity[-1]
        if last.active:
            active_s += max(0.0, now - last.timestamp)

        return active_s * 1000.0
