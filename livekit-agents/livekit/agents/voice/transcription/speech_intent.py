from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet


@dataclass
class SpeechIntentResult:
    allow_interrupt: bool
    category: str
    text: str


class SpeechIntentEvaluator:
    DEFAULT_ACKS: FrozenSet[str] = frozenset({
        "yeah", "yes", "yep", "uh huh", "ok", "okay",
        "hmm", "right", "sure", "got it", "i see",
        "ah", "oh", "alright"
    })

    DEFAULT_COMMANDS: FrozenSet[str] = frozenset({
        "stop", "wait", "pause", "hold on",
        "excuse me", "sorry", "question"
    })

    def __init__(
        self,
        acknowledgements: FrozenSet[str] | None = None,
        commands: FrozenSet[str] | None = None
    ) -> None:
        self._acks = acknowledgements or self.DEFAULT_ACKS
        self._commands = commands or self.DEFAULT_COMMANDS

    def _normalize(self, text: str) -> str:
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    def _is_acknowledgement(self, text: str) -> bool:
        if not text:
            return True

        normalized = self._normalize(text)
        if normalized in self._acks:
            return True

        tokens = normalized.split()
        return all(tok in self._acks for tok in tokens)

    def _contains_command(self, text: str) -> bool:
        normalized = self._normalize(text)
        return any(cmd in normalized for cmd in self._commands)

    def evaluate(self, text: str, agent_speaking: bool) -> SpeechIntentResult:
        if not agent_speaking:
            return SpeechIntentResult(True, "agent_idle", text)

        if self._contains_command(text):
            return SpeechIntentResult(True, "command", text)

        if self._is_acknowledgement(text):
            return SpeechIntentResult(False, "acknowledgement", text)

        return SpeechIntentResult(True, "meaningful_input", text)
