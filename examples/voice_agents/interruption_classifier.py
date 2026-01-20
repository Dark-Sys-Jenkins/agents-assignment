from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Set


class InterruptionIntent(Enum):
    IGNORE_BACKCHANNEL = "ignore_backchannel"
    INTERRUPT_COMMAND = "interrupt_command"
    INTERRUPT_OTHER = "interrupt_other"

@dataclass
class InterruptionClassifierConfig:
    # one word backchannels (passive acknowledgements)
    backchannel_words: Set[str] = field(
        default_factory=lambda: {
            "yeah",
            "alright",
            "i see",
            "yes",
            "yep",
            "yup",
            "ok",
            "okay",
            "hmm",
            "hm",
            "mhm",
            "uh-huh",
            "uh huh",
            "uhuh",
            "mm-hmm",
            "mm hmm",
            "mmhmm",
            "right",
            "sure",
            "ah",
            "oh",
            "i see",
            "got it",
            "gotcha",
            "accha",
            "theek hai",
            "samajh gaya",
            "samajh gayi"
        }
    )

    # Explicit interruption commands
    command_phrases: Set[str] = field(
        default_factory=lambda: {
            "stop",
            "wait",
            "no",
            "cancel",
            "hold on",
            "hold",
            "pause",
            "quiet",
            "shut up",
            "enough",
            "never mind",
            "nevermind",
            "actually",
            "but",
            "nahi",
            "ruko",
        }
    )

    # user can choose if other words (non backchannel) should interrupt the agent or not
    interrupt_on_non_backchannel: bool = True


class InterruptionClassifier:

    def __init__(self, config: InterruptionClassifierConfig | None = None):
        self.config = config or InterruptionClassifierConfig()
        self._setup_patterns()

    def _setup_patterns(self) -> None:
        # regex matching, because lowercase/uppercase were causing issues
        self._backchannels = {self._normalize(b) for b in self.config.backchannel_words}
        self._commands = {self._normalize(c) for c in self.config.command_phrases}

        escaped_commands = [re.escape(cmd) for cmd in sorted(self._commands, key=len, reverse=True)]
        if escaped_commands:
            self._command_pattern = re.compile(
                r"\b(" + "|".join(escaped_commands) + r")\b", re.IGNORECASE
            )
        else:
            self._command_pattern = None

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _is_backchannel_only(self, normalized_text: str) -> bool:
        # chekcing if the entire sentence consists of only backchannels
        if not normalized_text:
            return True 

        if normalized_text in self._backchannels:
            return True

        words = normalized_text.split()
        if not words:
            return True

        if len(words) == 1:
            return words[0] in self._backchannels

        if normalized_text in self._backchannels:
            return True

        for word in words:
            if word not in self._backchannels:
                found_as_part_of_phrase = False
                for bc in self._backchannels:
                    if " " in bc and word in bc.split():
                        # if the word is part of a multi-word backchannel, check if the full phrase is in the text
                        if bc in normalized_text:
                            found_as_part_of_phrase = True
                            break
                if not found_as_part_of_phrase:
                    return False

        return True

    def classify(self, transcript: str, debug: bool = False) -> InterruptionIntent:
    #    classification of sentences, to determine if the agent should interrupt or not
        if not transcript:
            return InterruptionIntent.IGNORE_BACKCHANNEL

        normalized = self._normalize(transcript)

        if debug:
            print(f"[CLASSIFIER DEBUG] Original: '{transcript}' -> Normalized: '{normalized}'")
            print(f"[CLASSIFIER DEBUG] Is in backchannels: {normalized in self._backchannels}")

        if not normalized:
            return InterruptionIntent.IGNORE_BACKCHANNEL

        if self._command_pattern and self._command_pattern.search(normalized):
            if debug:
                print(f"[CLASSIFIER DEBUG] Matched command pattern")
            return InterruptionIntent.INTERRUPT_COMMAND

        if self._is_backchannel_only(normalized):
            if debug:
                print(f"[CLASSIFIER DEBUG] Is backchannel only")
            return InterruptionIntent.IGNORE_BACKCHANNEL

        if debug:
            print(f"[CLASSIFIER DEBUG] Not a backchannel, treating as interrupt_other")
        if self.config.interrupt_on_non_backchannel:
            return InterruptionIntent.INTERRUPT_OTHER
        else:
            return InterruptionIntent.IGNORE_BACKCHANNEL

    def should_interrupt(self, transcript: str) -> bool:
        intent = self.classify(transcript)
        return intent in (InterruptionIntent.INTERRUPT_COMMAND, InterruptionIntent.INTERRUPT_OTHER)


# default_classifier = InterruptionClassifier()  # Unused singleton
