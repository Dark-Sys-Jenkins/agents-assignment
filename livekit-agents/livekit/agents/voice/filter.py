from __future__ import annotations

import os
import string
import logging
from typing import Set, Optional
from dataclasses import dataclass

log = logging.getLogger("livekit.agents")


@dataclass(frozen=True)
class SpeechResult:
    allow: bool
    kind: str
    text: str


class SpeechChecker:
    def __init__(
        self,
        fillers: Optional[Set[str]] = None,
        commands: Optional[Set[str]] = None,
    ):
        self.fillers = fillers or self._read_words("AGENT_PASSIVE_LEXICON")
        self.commands = commands or self._read_words("AGENT_DIRECTIVE_COMMANDS")

    def _read_words(self, key: str) -> Set[str]:
        value = os.getenv(key, "")
        if not value:
            log.warning(f"SpeechChecker: {key} is missing or empty.")
            return set()

        return {w.strip().lower() for w in value.split(",") if w.strip()}

    def check(self, text: str, agent_talking: bool) -> SpeechResult:
        if not agent_talking:
            return SpeechResult(False, "NEW_TURN", text)

        clean = text.lower().translate(str.maketrans("", "", string.punctuation)).strip()
        words = clean.split()

        if not words:
            return SpeechResult(True, "NOISE", text)

        if any(w in self.commands for w in words):
            return SpeechResult(False, "DIRECTIVE", text)

        only_fillers = all(w in self.fillers for w in words)

        return SpeechResult(
            only_fillers,
            "BACKCHANNEL" if only_fillers else "VALID_INPUT",
            text,
        )
