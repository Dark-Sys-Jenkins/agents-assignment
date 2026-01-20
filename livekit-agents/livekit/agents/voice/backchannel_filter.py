from typing import Iterable
from ._utils import split_words
from __future__ import annotations

import re
from typing import Sequence


class BackchannelFilter:
    """
    Context-aware backchannel filter.

    Purpose:
    - Ignore filler words like 'yeah', 'ok', 'hmm' when the agent is speaking
    - Allow real interruptions like 'stop', 'wait', 'no'
    - Correctly handle mixed input: 'yeah okay but wait' → interrupt
    """

    DEFAULT_IGNORE_WORDS = {
        "yeah", "ok", "okay", "hmm", "right",
        "uh", "uh-huh", "um", "umm",
        "yep", "sure", "aha",
        "mm", "mmm", "mm-hmm", "mhm", "mhmm",
    }

    INTERRUPT_WORDS = {
        "stop", "wait", "hold", "pause", "no",
        "don't", "dont", "cancel",
    }

    def __init__(self, ignore_words: Iterable[str] | None = None):
        self.ignore_words = {
            w.lower() for w in (ignore_words or self.DEFAULT_IGNORE_WORDS)
        }

    def _normalize(self, text: str) -> list[str]:
        words = split_words(text, split_character=True)
        return [
            w.strip(".,!?;:()[]{}\"'").lower()
            for w in words
            if w.strip(".,!?;:()[]{}\"'")
        ]

    def is_backchannel_only(self, text: str) -> bool:
        """
        Returns True if text consists ONLY of backchannel words.
        """
        if not text:
            return True

        words = self._normalize(text)
        if not words:
            return True

        return all(word in self.ignore_words for word in words)

    def contains_interrupt_command(self, text: str) -> bool:
        """
        Returns True if text contains any explicit interruption command.
        """
        words = self._normalize(text)
        if not words:
            return False

        if any(word in self.INTERRUPT_WORDS for word in words):
            return True

        joined = " ".join(words)
        return any(
        joined == cmd
        or joined.startswith(cmd + " ")
        or joined.endswith(" " + cmd)
        for cmd in self.INTERRUPT_WORDS
        )
    def should_interrupt(self, *, agent_speaking: bool, text: str | None) -> bool:
        """
        Final decision function.

        Rules:
        - If agent is NOT speaking → never interrupt
        - If agent IS speaking:
            - Explicit interrupt command → interrupt
            - Pure backchannel → ignore
            - Mixed content → interrupt
        """
        if not agent_speaking:
            return False

        if not text:
            # VAD fired before STT → wait, do NOT interrupt yet
            return False

        if self.contains_interrupt_command(text):
            return True

        if self.is_backchannel_only(text):
            return False

        # Mixed content (not pure backchannel)
        return True
