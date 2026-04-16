from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal




@dataclass
class BackchannelConfig:
    """Configuration for backchannel detection.

    Backchannels are short user utterances like "yeah", "ok", "hmm" that indicate
    the user is listening rather than trying to interrupt the agent.

    When backchannel filtering is enabled:
    - If the agent is speaking and the user says a backchannel word, the agent continues
    - If the agent is silent, backchannel words are treated as normal input
    - Commands like "wait", "stop", "no" always interrupt regardless of agent state
    """

    enabled: bool = True
    """Enable backchannel filtering. When False, all user speech is treated equally."""

    backchannel_words: set[str] = field(
        default_factory=lambda: {
            "yeah",
            "yes",
            "ok",
            "okay",
            "hmm",
            "hm",
            "right",
            "uh-huh",
            "uh huh",
            "mhm",
            "aha",
            "sure",
            "got it",
            "i see",
            "uh-huh",
            "yep",
            "yup",
            "mm-hmm",
            "mm hmm",
        }
    )
    """Words/phrases that indicate passive acknowledgement rather than interruption intent."""

    interruption_commands: set[str] = field(
        default_factory=lambda: {
            "wait",
            "stop",
            "no",
            "hold on",
            "hang on",
            "pause",
            "slow down",
            "not yet",
            "let me",
            "can i",
            "could i",
            "i want",
            "i need",
            "actually",
            "sorry",
            "excuse me",
            "hey",
            "hello",
            "start",
            "begin",
        }
    )
    """Words/phrases that should always interrupt, even when mixed with backchannel words."""

    min_words_for_interruption: int = 1
    """Minimum number of non-backchannel words required to trigger interruption when agent is speaking.

    When the agent is speaking, user input must contain at least this many non-backchannel words
    to be considered a real interruption. Set to 0 to disable this check.
    """

    check_semantic_interruption: bool = True
    """If True, check if backchannel words are mixed with interruption commands.

    For example, "yeah wait a second" contains "yeah" (backchannel) but also "wait" (command),
    so it should still interrupt.
    """

    stt_settling_delay_ms: int = 300
    """Delay in milliseconds to wait for STT transcript to settle before making interrupt decision.

    This compensates for the fact that VAD fires before STT completes. The delay allows
    partial transcripts to accumulate for more accurate classification.
    Increase for slower STT providers, decrease for faster response.
    """


class BackchannelFilter:
    """Filters user input to distinguish between backchannel acknowledgements and real interruptions.

    This filter helps agents determine when to ignore user speech (backchannel) vs when to
    respond (real interruption or user input during agent silence).
    """

    def __init__(self, config: BackchannelConfig | None = None) -> None:
        self.config = config or BackchannelConfig()
        self._backchannel_pattern = self._build_pattern(self.config.backchannel_words)
        self._command_pattern = self._build_pattern(self.config.interruption_commands)

    def _build_pattern(self, words: set[str]) -> re.Pattern[str]:
        """Build a regex pattern to match multi-word phrases."""
        if not words:
            # Return a pattern that will never match anything
            return re.compile(r"(?!x)x", re.IGNORECASE)
        sorted_words = sorted(words, key=len, reverse=True)
        escaped = [re.escape(w) for w in sorted_words]
        return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)

    def is_backchannel(self, text: str) -> bool:
        """Check if the text is purely a backchannel utterance.

        Works by stripping all matched backchannel phrases from the text
        and checking if any meaningful words remain.
        """
        text_lower = text.lower().strip()

        if not text_lower:
            return False

        if self.has_interruption_command(text):
            return False

        # Remove all matched backchannel phrases from the text
        remaining = self._backchannel_pattern.sub("", text_lower)

        # Find remaining meaningful words (ignoring punctuation/whitespace)
        remaining_words = re.findall(r"\b\w+\b", remaining)

        # If nothing meaningful remains, it's all backchannel
        if not remaining_words:
            return True

        # Check if remaining non-backchannel words are below the threshold
        return len(remaining_words) < self.config.min_words_for_interruption

    def has_interruption_command(self, text: str) -> bool:
        """Check if the text contains an interruption command."""
        text_lower = text.lower()
        matches = self._command_pattern.findall(text_lower)
        return len(matches) > 0

    def should_interrupt(self, text: str, agent_is_speaking: bool):

        text_lower = text.lower().strip()

        if not text_lower:
            return "ignore"

        if not agent_is_speaking:
            return "respond"

        if not self.config.enabled:
            return "interrupt"

        if self.has_interruption_command(text):
            return "interrupt"

        if self.is_backchannel(text):
            return "ignore"

        return "interrupt"
