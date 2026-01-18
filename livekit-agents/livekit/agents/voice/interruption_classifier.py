"""
Context-aware interruption handler for LiveKit voice agents.

Handles backchanneling detection - distinguishing between passive
acknowledgements ("yeah", "ok") and actual interruption commands ("stop", "wait").
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Set

logger = logging.getLogger("livekit.agents.interruption")


class InterruptionDecision(Enum):
    """Possible outcomes when classifying user speech."""
    IGNORE = "ignore"
    INTERRUPT = "interrupt"
    RESPOND = "respond"


@dataclass
class InterruptionConfig:
    """
    Settings for interruption classification.

    Can be configured via environment variables:
        SOFT_WORDS - comma-separated filler words
        HARD_INTERRUPT_WORDS - comma-separated interrupt commands
        INTERRUPTION_DEBUG - set to "true" for verbose logging
    """

    soft_words: Set[str] = field(default_factory=lambda: {
        # Affirmatives
        "yeah", "yea", "yep", "yup", "yes",
        # Acknowledgements
        "ok", "okay", "k",
        # Fillers/backchannels
        "hmm", "hm", "mm", "mmm", "mhm", "mm-hmm", "mmhmm",
        "uh-huh", "uh huh", "uhuh", "aha", "ah",
        # Agreement
        "right", "sure", "alright", "alrighty",
        "got it", "gotcha", "i see", "oh",
        "cool", "nice", "great", "good",
        "true", "exactly", "indeed",
    })

    hard_interrupt_words: Set[str] = field(default_factory=lambda: {
        # Direct commands
        "stop", "wait", "no", "pause", "hold", "hold on",
        "shut up", "quiet", "enough", "silence",
        "cancel", "abort", "quit", "exit",
        # Redirections
        "actually", "but", "however", "wait a second",
        "hold on a second", "one moment", "just a moment",
        "hang on", "never mind", "nevermind",
    })

    debug: bool = False

    def __post_init__(self) -> None:
        self._load_env_config()

    def _load_env_config(self) -> None:
        if env_soft := os.getenv("SOFT_WORDS"):
            self.soft_words = {w.strip().lower() for w in env_soft.split(",")}

        if env_hard := os.getenv("HARD_INTERRUPT_WORDS"):
            self.hard_interrupt_words = {w.strip().lower() for w in env_hard.split(",")}

        if env_debug := os.getenv("INTERRUPTION_DEBUG"):
            self.debug = env_debug.lower() in ("true", "1", "yes")

    def add_soft_word(self, word: str) -> None:
        self.soft_words.add(word.lower().strip())

    def remove_soft_word(self, word: str) -> None:
        self.soft_words.discard(word.lower().strip())

    def add_hard_interrupt_word(self, word: str) -> None:
        self.hard_interrupt_words.add(word.lower().strip())

    def remove_hard_interrupt_word(self, word: str) -> None:
        self.hard_interrupt_words.discard(word.lower().strip())


class InterruptionClassifier:
    """
    Determines whether user speech should interrupt the agent.

    Decision matrix:
        - Soft word + agent speaking = IGNORE (continue)
        - Hard word + agent speaking = INTERRUPT (stop)
        - Any word + agent silent = RESPOND (process normally)
        - Mixed input with hard word = INTERRUPT
    """

    def __init__(self, config: InterruptionConfig | None = None) -> None:
        self.config = config or InterruptionConfig()
        self._build_normalized_sets()

    def _build_normalized_sets(self) -> None:
        """Pre-normalize word lists for faster matching."""
        self._norm_soft = {self._normalize(w) for w in self.config.soft_words}
        self._norm_hard = {self._normalize(w) for w in self.config.hard_interrupt_words}

        # Extract multi-word phrases (sorted longest first for greedy matching)
        self._soft_phrases = sorted(
            [w for w in self._norm_soft if " " in w],
            key=len, reverse=True
        )
        self._hard_phrases = sorted(
            [w for w in self._norm_hard if " " in w],
            key=len, reverse=True
        )

    def _normalize(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _has_hard_interrupt(self, text: str) -> bool:
        """Check for any interrupt command in text."""
        for phrase in self._hard_phrases:
            if phrase in text:
                logger.debug(f"Hard interrupt phrase detected: '{phrase}'")
                return True

        single_hard = {w for w in self._norm_hard if " " not in w}
        for word in text.split():
            if word in single_hard:
                logger.debug(f"Hard interrupt word detected: '{word}'")
                return True
        return False

    def _is_all_soft(self, text: str) -> bool:
        """Check if text contains only soft/filler words."""
        remaining = text
        for phrase in self._soft_phrases:
            remaining = remaining.replace(phrase, " ")

        single_soft = {w for w in self._norm_soft if " " not in w}
        for word in remaining.split():
            if word and word not in single_soft:
                logger.debug(f"Non-soft word found: '{word}'")
                return False
        return True

    def classify(self, transcript: str, is_agent_speaking: bool) -> InterruptionDecision:
        """
        Classify user input and determine action.

        Args:
            transcript: What the user said
            is_agent_speaking: True if agent is currently outputting audio

        Returns:
            IGNORE - agent continues speaking
            INTERRUPT - agent stops immediately
            RESPOND - agent processes input (when silent)
        """
        if not transcript or not transcript.strip():
            return InterruptionDecision.IGNORE

        normalized = self._normalize(transcript)

        # Agent is silent - always process input
        if not is_agent_speaking:
            logger.info(f"[RESPOND] Agent silent, processing: '{transcript}'")
            return InterruptionDecision.RESPOND

        # Agent is speaking - check for interrupt commands first
        if self._has_hard_interrupt(normalized):
            logger.info(f"[INTERRUPT] Hard command while speaking: '{transcript}'")
            return InterruptionDecision.INTERRUPT

        # Only soft words - ignore and continue
        if self._is_all_soft(normalized):
            logger.info(f"[IGNORE] Backchannel while speaking: '{transcript}'")
            return InterruptionDecision.IGNORE

        # Unknown/mixed content while speaking - default to interrupt
        logger.info(f"[INTERRUPT] Unknown input while speaking: '{transcript}'")
        return InterruptionDecision.INTERRUPT

    def should_interrupt(self, transcript: str, is_agent_speaking: bool) -> bool:
        return self.classify(transcript, is_agent_speaking) == InterruptionDecision.INTERRUPT

    def should_ignore(self, transcript: str, is_agent_speaking: bool) -> bool:
        return self.classify(transcript, is_agent_speaking) == InterruptionDecision.IGNORE


# Module-level default instance
_default_classifier: InterruptionClassifier | None = None


def get_default_classifier() -> InterruptionClassifier:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = InterruptionClassifier()
    return _default_classifier


def set_default_classifier(classifier: InterruptionClassifier) -> None:
    global _default_classifier
    _default_classifier = classifier
