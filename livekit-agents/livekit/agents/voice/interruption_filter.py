"""
Intelligent Interruption Filter for LiveKit Voice Agents

This module provides context-aware interruption handling that distinguishes between
passive acknowledgements (backchanneling) and active interruptions based on whether
the agent is currently speaking or silent.

The filter implements the following logic matrix:
- "Yeah/Ok/Hmm" + Agent Speaking = IGNORE (agent continues seamlessly)
- "Wait/Stop/No" + Agent Speaking = INTERRUPT (agent stops immediately)
- "Yeah/Ok/Hmm" + Agent Silent = RESPOND (treat as valid input)
- Any input + Agent Silent = RESPOND (normal conversational behavior)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal


# Default list of backchannel/filler words that should be ignored while agent is speaking
DEFAULT_BACKCHANNEL_WORDS = [
    # English acknowledgements
    "yeah", "yea", "yes", "yep", "yup", "ya",
    "ok", "okay", "k",
    "hmm", "hm", "mm", "mmm", "mhm", "uh-huh", "uhuh", "uh huh",
    "right", "alright", "all right",
    "sure", "surely",
    "got it", "gotcha",
    "i see", "see",
    "aha", "ah", "oh",
    "cool", "nice", "great",
    "true", "indeed",
    "go on", "go ahead", "continue",
]

# Words that should ALWAYS trigger an interruption, even if mixed with filler words
DEFAULT_INTERRUPT_WORDS = [
    "wait", "stop", "no", "hold", "pause", "hang on",
    "actually", "but", "however", "question",
    "what", "why", "how", "when", "where", "who",
    "repeat", "again", "sorry", "pardon",
    "help", "cancel", "exit", "quit", "end",
    "different", "change", "wrong", "incorrect",
]


@dataclass
class InterruptionFilterConfig:
    """Configuration for the intelligent interruption filter."""

    # List of backchannel words to ignore while agent is speaking
    backchannel_words: list[str] = field(default_factory=lambda: list(DEFAULT_BACKCHANNEL_WORDS))

    # List of words that always trigger an interruption
    interrupt_words: list[str] = field(default_factory=lambda: list(DEFAULT_INTERRUPT_WORDS))

    # Whether the filter is enabled
    enabled: bool = True

    # Minimum word count to consider as potential interruption (helps with noise)
    min_words_for_interruption: int = 1

    @classmethod
    def from_env(cls) -> "InterruptionFilterConfig":
        """Create config from environment variables.

        Environment variables:
            LIVEKIT_BACKCHANNEL_WORDS: Comma-separated list of backchannel words
            LIVEKIT_INTERRUPT_WORDS: Comma-separated list of interrupt words
            LIVEKIT_INTERRUPTION_FILTER_ENABLED: "true" or "false"
        """
        config = cls()

        backchannel_env = os.getenv("LIVEKIT_BACKCHANNEL_WORDS")
        if backchannel_env:
            config.backchannel_words = [w.strip().lower() for w in backchannel_env.split(",")]

        interrupt_env = os.getenv("LIVEKIT_INTERRUPT_WORDS")
        if interrupt_env:
            config.interrupt_words = [w.strip().lower() for w in interrupt_env.split(",")]

        enabled_env = os.getenv("LIVEKIT_INTERRUPTION_FILTER_ENABLED")
        if enabled_env is not None:
            config.enabled = enabled_env.lower() in ("true", "1", "yes")

        return config


InterruptionDecision = Literal["ignore", "interrupt", "respond"]


class InterruptionFilter:
    """
    Context-aware filter for determining whether user speech should interrupt the agent.

    This filter implements intelligent interruption handling that:
    1. Ignores backchannel words ("yeah", "ok", "hmm") when agent is speaking
    2. Allows interruption for command words ("wait", "stop", "no")
    3. Handles mixed sentences ("yeah but wait") by detecting command words
    4. Treats all input as valid when agent is silent
    """

    def __init__(self, config: InterruptionFilterConfig | None = None):
        self.config = config or InterruptionFilterConfig()

        # Pre-compile regex patterns for efficiency
        self._backchannel_patterns = self._compile_patterns(self.config.backchannel_words)
        self._interrupt_patterns = self._compile_patterns(self.config.interrupt_words)

    def _compile_patterns(self, words: list[str]) -> list[re.Pattern]:
        """Compile word list into regex patterns for word boundary matching."""
        patterns = []
        for word in words:
            # Escape special regex chars and add word boundaries
            escaped = re.escape(word.lower())
            pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
            patterns.append(pattern)
        return patterns

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove punctuation, extra spaces, and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_words(self, text: str) -> list[str]:
        """Extract individual words from text."""
        normalized = self._normalize_text(text)
        return normalized.split() if normalized else []

    def contains_backchannel_only(self, text: str) -> bool:
        """
        Check if the text contains ONLY backchannel/filler words.

        Args:
            text: The transcribed speech to check

        Returns:
            True if text contains only backchannel words, False otherwise
        """
        if not text or not text.strip():
            return False

        normalized = self._normalize_text(text)
        words = self._extract_words(text)

        if not words:
            return False

        # Check if all words are backchannel words
        remaining_text = normalized
        for pattern in self._backchannel_patterns:
            remaining_text = pattern.sub('', remaining_text)

        # If nothing remains after removing backchannel words, it's backchannel-only
        remaining_text = re.sub(r'\s+', '', remaining_text).strip()
        return len(remaining_text) == 0

    def contains_interrupt_word(self, text: str) -> bool:
        """
        Check if the text contains any interrupt/command words.

        These words should ALWAYS trigger an interruption, even if mixed with
        backchannel words (e.g., "yeah but wait" should interrupt).

        Args:
            text: The transcribed speech to check

        Returns:
            True if text contains interrupt words, False otherwise
        """
        if not text or not text.strip():
            return False

        normalized = self._normalize_text(text)

        for pattern in self._interrupt_patterns:
            if pattern.search(normalized):
                return True

        return False

    def decide(
        self,
        transcript: str,
        agent_is_speaking: bool
    ) -> InterruptionDecision:
        """
        Decide how to handle the user's speech based on content and agent state.

        Args:
            transcript: The transcribed user speech
            agent_is_speaking: Whether the agent is currently speaking/generating audio

        Returns:
            - "ignore": The agent should continue speaking without interruption
            - "interrupt": The agent should stop immediately and listen
            - "respond": The agent should treat this as valid input (when silent)
        """
        if not self.config.enabled:
            # Filter disabled - always interrupt if agent is speaking, respond if silent
            return "interrupt" if agent_is_speaking else "respond"

        if not transcript or not transcript.strip():
            return "ignore"

        words = self._extract_words(transcript)

        # If not enough words, ignore (helps filter noise)
        if len(words) < self.config.min_words_for_interruption:
            # Still check for interrupt words even with few words
            if not self.contains_interrupt_word(transcript):
                return "ignore"

        # Case 1: Agent is NOT speaking - always respond to any valid input
        if not agent_is_speaking:
            return "respond"

        # Case 2: Agent IS speaking - apply filtering logic

        # Check for interrupt words first (highest priority)
        # Even "yeah but wait" should interrupt because of "wait"
        if self.contains_interrupt_word(transcript):
            return "interrupt"

        # Check if it's backchannel-only
        if self.contains_backchannel_only(transcript):
            return "ignore"

        # Not backchannel-only and no explicit interrupt words
        # This means it's actual speech content - should interrupt
        return "interrupt"

    def should_ignore_for_speaking_agent(self, transcript: str) -> bool:
        """
        Convenience method to check if transcript should be ignored when agent is speaking.

        Args:
            transcript: The transcribed user speech

        Returns:
            True if the transcript should be ignored (backchannel-only, no commands)
        """
        return self.decide(transcript, agent_is_speaking=True) == "ignore"

    def add_backchannel_word(self, word: str) -> None:
        """Add a word to the backchannel list."""
        word = word.lower().strip()
        if word not in self.config.backchannel_words:
            self.config.backchannel_words.append(word)
            self._backchannel_patterns = self._compile_patterns(self.config.backchannel_words)

    def add_interrupt_word(self, word: str) -> None:
        """Add a word to the interrupt list."""
        word = word.lower().strip()
        if word not in self.config.interrupt_words:
            self.config.interrupt_words.append(word)
            self._interrupt_patterns = self._compile_patterns(self.config.interrupt_words)

    def remove_backchannel_word(self, word: str) -> None:
        """Remove a word from the backchannel list."""
        word = word.lower().strip()
        if word in self.config.backchannel_words:
            self.config.backchannel_words.remove(word)
            self._backchannel_patterns = self._compile_patterns(self.config.backchannel_words)

    def remove_interrupt_word(self, word: str) -> None:
        """Remove a word from the interrupt list."""
        word = word.lower().strip()
        if word in self.config.interrupt_words:
            self.config.interrupt_words.remove(word)
            self._interrupt_patterns = self._compile_patterns(self.config.interrupt_words)


# Global default filter instance (can be customized at runtime)
_default_filter: InterruptionFilter | None = None


def get_default_filter() -> InterruptionFilter:
    """Get the default interruption filter instance."""
    global _default_filter
    if _default_filter is None:
        _default_filter = InterruptionFilter(InterruptionFilterConfig.from_env())
    return _default_filter


def set_default_filter(filter_instance: InterruptionFilter) -> None:
    """Set a custom interruption filter as the default."""
    global _default_filter
    _default_filter = filter_instance
