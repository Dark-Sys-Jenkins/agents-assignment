from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Iterable, Literal


def _parse_words_env(key: str, default: str) -> set[str]:
    raw = os.getenv(key, default)
    parts = [p.strip().lower() for p in raw.split(",")]
    return {p for p in parts if p}


DEFAULT_IGNORE_WORDS = "yeah,ok,okay,hmm,aha,right,uh-huh,uh huh,mm-hmm,mm hmm,yes"
DEFAULT_INTERRUPT_WORDS = "stop,wait,no,cancel,hold on,shut up,pause"

IGNORE_WORDS = _parse_words_env("LK_IGNORE_WORDS", DEFAULT_IGNORE_WORDS)
INTERRUPT_WORDS = _parse_words_env("LK_INTERRUPT_WORDS", DEFAULT_INTERRUPT_WORDS)

_WORD_RE = re.compile(r"[a-zA-Z']+")


def normalize_and_tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    return _WORD_RE.findall(text)


def classify_transcript(text: str) -> Literal["ignore", "interrupt"]:
    """
    ignore:
      - ONLY contains backchannel/filler words (ignore list)
    interrupt:
      - contains any meaningful token OR explicit interrupt keyword
    """
    tokens = normalize_and_tokenize(text)

    if not tokens:
        return "ignore"

    # If any interrupt phrase/word appears, interrupt immediately
    # We check both token-level words and raw normalized text for phrases like "hold on"
    norm_text = " ".join(tokens)
    for w in INTERRUPT_WORDS:
        w = w.strip().lower()
        if not w:
            continue
        if " " in w:
            if w in norm_text:
                return "interrupt"
        else:
            if w in tokens:
                return "interrupt"

    # If ALL tokens are in ignore list, ignore
    if all(tok in IGNORE_WORDS for tok in tokens):
        return "ignore"

    return "interrupt"


@dataclass
class PendingInterrupt:
    active: bool = False
    created_at: float = 0.0
    timer: asyncio.TimerHandle | None = None


class PendingInterruptController:
    """
    Controls the VAD->STT interrupt deferral window.

    Goal:
      - When agent is speaking and VAD triggers: do NOT interrupt immediately.
      - Start a short pending interrupt window.
      - When STT final transcript arrives:
          - if filler only => cancel pending
          - else => commit interrupt
    """

    def __init__(self, defer_seconds: float = 0.35):
        self.defer_seconds = defer_seconds
        self._pending = PendingInterrupt()

    @property
    def is_pending(self) -> bool:
        return self._pending.active

    def start(self, loop: asyncio.AbstractEventLoop, on_timeout_interrupt) -> None:
        """
        Start a pending interrupt window.
        If transcript never arrives, timeout triggers interrupt.
        """
        self.cancel()

        self._pending.active = True
        self._pending.created_at = time.time()

        def _timeout():
            # If still pending after defer window -> treat as real interrupt
            self._pending.active = False
            self._pending.timer = None
            on_timeout_interrupt()

        self._pending.timer = loop.call_later(self.defer_seconds, _timeout)

    def cancel(self) -> None:
        if self._pending.timer:
            self._pending.timer.cancel()
        self._pending = PendingInterrupt()

    def commit(self) -> None:
        # commit means: we want interrupt now, cancel timer and mark inactive
        if self._pending.timer:
            self._pending.timer.cancel()
        self._pending.active = False
        self._pending.timer = None
