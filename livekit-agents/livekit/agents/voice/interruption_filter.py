"""
Intelligent Interruption Filter for LiveKit Voice Agents

This module implements context-aware filtering of user speech to distinguish between:
- Passive acknowledgements (backchanneling): "yeah", "ok", "hmm" - ignored when agent is speaking
- Active interruptions: "wait", "stop", "no" - always processed
- Mixed inputs: "yeah but wait" - processed because it contains meaningful content

The filter is state-aware and only ignores backchannel words when the agent is actively speaking.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Sequence

from ..tokenize.basic import split_words


# Default backchannel words that indicate passive listening
DEFAULT_BACKCHANNEL_WORDS: frozenset[str] = frozenset([
    # English affirmations
    "yeah", "yes", "yep", "yup", "yea", "ya",
    "ok", "okay", "k", "kk",
    "hmm", "hm", "mmm", "mm", "mhm", "uh-huh", "uhuh", "uh huh", "uhhuh",
    "right", "alright", "sure",
    "ah", "aha", "ahh", "aah",
    "oh", "ohh", "ooh",
    # Filler sounds
    "uh", "um", "er", "eh", "huh",
    # Other acknowledgements
    "gotcha", "got it", "i see", "see",
    "cool", "nice", "great", "good", "fine",
    "true", "exactly", "absolutely", "definitely", "certainly",
    "interesting", "indeed",
])

# Words that indicate an active interruption request - these should NEVER be ignored
DEFAULT_INTERRUPT_WORDS: frozenset[str] = frozenset([
    # Stop commands
    "stop", "wait", "hold", "pause", "halt", "enough",
    # Negations and corrections
    "no", "nope", "nah", "wrong", "incorrect", "actually",
    # Questions and requests
    "what", "why", "how", "when", "where", "who", "which",
    "can", "could", "would", "should", "will",
    "please", "help", "explain", "repeat", "again",
    # Transitions that indicate user wants to speak
    "but", "however", "although", "though", "except",
    "let", "tell", "give", "show", "listen",
    # Greetings (when agent is silent, these should trigger response)
    "hello", "hi", "hey", "start", "begin",
])


@dataclass
class InterruptionFilterConfig:
    """Configuration for the intelligent interruption filter.

    Attributes:
        backchannel_words: Set of words to ignore when agent is speaking.
            These are passive acknowledgements that don't require agent to stop.
        interrupt_words: Set of words that always trigger an interruption.
            These indicate the user wants the agent to stop and listen.
        enabled: Whether the filter is active. If False, all inputs trigger interruption.
        case_sensitive: Whether word matching is case-sensitive. Default False.
    """
    backchannel_words: frozenset[str] = field(default_factory=lambda: DEFAULT_BACKCHANNEL_WORDS)
    interrupt_words: frozenset[str] = field(default_factory=lambda: DEFAULT_INTERRUPT_WORDS)
    enabled: bool = True
    case_sensitive: bool = False

    @classmethod
    def from_env(cls) -> "InterruptionFilterConfig":
        """Create configuration from environment variables.

        Environment variables:
            BACKCHANNEL_WORDS: Comma-separated list of words to ignore (extends defaults)
            INTERRUPT_WORDS: Comma-separated list of words that trigger interruption (extends defaults)
            BACKCHANNEL_FILTER_ENABLED: "true" or "false" to enable/disable filter
        """
        config = cls()

        # Extend backchannel words from environment
        env_backchannel = os.environ.get("BACKCHANNEL_WORDS", "")
        if env_backchannel:
            additional_words = frozenset(w.strip().lower() for w in env_backchannel.split(",") if w.strip())
            config = InterruptionFilterConfig(
                backchannel_words=config.backchannel_words | additional_words,
                interrupt_words=config.interrupt_words,
                enabled=config.enabled,
                case_sensitive=config.case_sensitive,
            )

        # Extend interrupt words from environment
        env_interrupt = os.environ.get("INTERRUPT_WORDS", "")
        if env_interrupt:
            additional_words = frozenset(w.strip().lower() for w in env_interrupt.split(",") if w.strip())
            config = InterruptionFilterConfig(
                backchannel_words=config.backchannel_words,
                interrupt_words=config.interrupt_words | additional_words,
                enabled=config.enabled,
                case_sensitive=config.case_sensitive,
            )

        # Check if filter is enabled
        env_enabled = os.environ.get("BACKCHANNEL_FILTER_ENABLED", "").lower()
        if env_enabled in ("false", "0", "no", "disabled"):
            config = InterruptionFilterConfig(
                backchannel_words=config.backchannel_words,
                interrupt_words=config.interrupt_words,
                enabled=False,
                case_sensitive=config.case_sensitive,
            )

        return config


@dataclass
class FilterResult:
    """Result of the interruption filter analysis.

    Attributes:
        should_interrupt: Whether the agent should interrupt/stop speaking.
        reason: Human-readable explanation of the decision.
        transcript: The original transcript that was analyzed.
        meaningful_words: List of words that are not backchannel words.
        backchannel_words_found: List of backchannel words found in the transcript.
    """
    should_interrupt: bool
    reason: str
    transcript: str
    meaningful_words: list[str] = field(default_factory=list)
    backchannel_words_found: list[str] = field(default_factory=list)


class InterruptionFilter:
    """Intelligent filter for distinguishing backchannels from real interruptions.

    This filter implements context-aware logic to determine whether user speech
    should trigger an interruption of the agent's current speech.

    The core logic:
    - When agent is SPEAKING and user says only backchannel words -> IGNORE
    - When agent is SPEAKING and user says interrupt words -> INTERRUPT
    - When agent is SPEAKING and user says mixed input -> INTERRUPT (contains meaningful content)
    - When agent is SILENT -> RESPOND to all input (backchannel words become valid responses)

    Example:
        >>> filter = InterruptionFilter()
        >>> # Agent is speaking, user says "yeah"
        >>> result = filter.should_interrupt("yeah", agent_is_speaking=True)
        >>> result.should_interrupt
        False
        >>> # Agent is silent, user says "yeah"
        >>> result = filter.should_interrupt("yeah", agent_is_speaking=False)
        >>> result.should_interrupt
        True
        >>> # Agent is speaking, user says "yeah but wait"
        >>> result = filter.should_interrupt("yeah but wait", agent_is_speaking=True)
        >>> result.should_interrupt
        True
    """

    def __init__(self, config: InterruptionFilterConfig | None = None):
        """Initialize the interruption filter.

        Args:
            config: Filter configuration. If None, uses default configuration
                    with environment variable overrides.
        """
        self._config = config or InterruptionFilterConfig.from_env()

    @property
    def config(self) -> InterruptionFilterConfig:
        """Get the current filter configuration."""
        return self._config

    def _normalize_word(self, word: str) -> str:
        """Normalize a word for comparison."""
        if self._config.case_sensitive:
            return word.strip()
        return word.strip().lower()

    def _extract_words(self, transcript: str) -> list[str]:
        """Extract individual words from a transcript.

        Uses the LiveKit tokenizer for consistent word splitting.
        """
        if not transcript:
            return []

        # Use the existing split_words function
        word_tuples = split_words(transcript, ignore_punctuation=True, split_character=True)
        return [self._normalize_word(w[0]) for w in word_tuples if w[0].strip()]

    def _is_backchannel_word(self, word: str) -> bool:
        """Check if a word is a backchannel/filler word."""
        normalized = self._normalize_word(word)
        return normalized in self._config.backchannel_words

    def _is_interrupt_word(self, word: str) -> bool:
        """Check if a word is an explicit interrupt word."""
        normalized = self._normalize_word(word)
        return normalized in self._config.interrupt_words

    def _contains_interrupt_phrase(self, transcript: str) -> bool:
        """Check if transcript contains multi-word interrupt phrases."""
        normalized = transcript.lower() if not self._config.case_sensitive else transcript

        # Check for common interrupt phrases
        interrupt_phrases = [
            "wait a", "hold on", "one moment", "just a", "hang on",
            "let me", "i have", "i need", "can you", "could you",
            "what about", "what if", "how about",
        ]

        for phrase in interrupt_phrases:
            if phrase in normalized:
                return True
        return False

    def should_interrupt(self, transcript: str, *, agent_is_speaking: bool) -> FilterResult:
        """Determine if user speech should interrupt the agent.

        Args:
            transcript: The transcribed user speech.
            agent_is_speaking: Whether the agent is currently speaking/generating audio.

        Returns:
            FilterResult with the decision and analysis details.
        """
        # If filter is disabled, always interrupt
        if not self._config.enabled:
            return FilterResult(
                should_interrupt=True,
                reason="Filter disabled - all input triggers interruption",
                transcript=transcript,
            )

        # If agent is NOT speaking, all input should be processed (including "yeah")
        if not agent_is_speaking:
            return FilterResult(
                should_interrupt=True,
                reason="Agent is silent - processing all user input",
                transcript=transcript,
            )

        # Agent IS speaking - apply intelligent filtering
        words = self._extract_words(transcript)

        if not words:
            return FilterResult(
                should_interrupt=False,
                reason="Empty transcript - no interruption",
                transcript=transcript,
            )

        # Categorize words
        backchannel_found: list[str] = []
        meaningful_words: list[str] = []
        has_interrupt_word = False

        for word in words:
            if self._is_interrupt_word(word):
                meaningful_words.append(word)
                has_interrupt_word = True
            elif self._is_backchannel_word(word):
                backchannel_found.append(word)
            else:
                # Word is neither backchannel nor explicit interrupt
                # Treat as meaningful content
                meaningful_words.append(word)

        # Check for multi-word interrupt phrases
        if self._contains_interrupt_phrase(transcript):
            return FilterResult(
                should_interrupt=True,
                reason=f"Contains interrupt phrase in: '{transcript}'",
                transcript=transcript,
                meaningful_words=meaningful_words,
                backchannel_words_found=backchannel_found,
            )

        # Decision logic
        if has_interrupt_word:
            return FilterResult(
                should_interrupt=True,
                reason=f"Contains interrupt word(s): {meaningful_words}",
                transcript=transcript,
                meaningful_words=meaningful_words,
                backchannel_words_found=backchannel_found,
            )

        if meaningful_words:
            # Has words that are neither backchannel nor explicit interrupt
            # This could be a real question or statement
            return FilterResult(
                should_interrupt=True,
                reason=f"Contains meaningful content: {meaningful_words}",
                transcript=transcript,
                meaningful_words=meaningful_words,
                backchannel_words_found=backchannel_found,
            )

        # Only backchannel words found - ignore while agent is speaking
        return FilterResult(
            should_interrupt=False,
            reason=f"Only backchannel words while agent speaking: {backchannel_found}",
            transcript=transcript,
            meaningful_words=[],
            backchannel_words_found=backchannel_found,
        )

    def is_only_backchannel(self, transcript: str) -> bool:
        """Quick check if transcript contains only backchannel words.

        This is a convenience method for simple checks without full analysis.
        """
        words = self._extract_words(transcript)
        if not words:
            return False

        return all(self._is_backchannel_word(w) for w in words)


# Global default filter instance
_default_filter: InterruptionFilter | None = None


def get_default_filter() -> InterruptionFilter:
    """Get the global default interruption filter instance."""
    global _default_filter
    if _default_filter is None:
        _default_filter = InterruptionFilter()
    return _default_filter


def should_interrupt_speech(
    transcript: str,
    *,
    agent_is_speaking: bool,
    filter_instance: InterruptionFilter | None = None,
) -> FilterResult:
    """Convenience function to check if speech should interrupt the agent.

    Args:
        transcript: The transcribed user speech.
        agent_is_speaking: Whether the agent is currently speaking.
        filter_instance: Optional custom filter. Uses default if None.

    Returns:
        FilterResult with the decision.
    """
    filter_to_use = filter_instance or get_default_filter()
    return filter_to_use.should_interrupt(transcript, agent_is_speaking=agent_is_speaking)
