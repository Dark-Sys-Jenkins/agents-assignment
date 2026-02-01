"""
Interruption Filter for LiveKit Voice Agents

This module provides intelligent filtering of user speech during agent playback,
distinguishing between backchannels (e.g., "yeah", "ok", "hmm") that should be
ignored and real interruptions (e.g., "stop", "wait", "no") that should halt
the agent.

The filter runs parallel to STT and makes real-time decisions based on transcript
content without modifying the underlying VAD kernel.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Sequence

logger = logging.getLogger(__name__)

# Default backchannel words that should NOT interrupt the agent when it's speaking
DEFAULT_IGNORE_WORDS: frozenset[str] = frozenset(
    {
        # English backchannels
        "yeah",
        "yea",
        "yep",
        "yes",
        "yup",
        "ok",
        "okay",
        "hmm",
        "hm",
        "mm",
        "mhm",
        "uh-huh",
        "uh huh",
        "uhuh",
        "ah",
        "aha",
        "oh",
        "right",
        "sure",
        "got it",
        "gotcha",
        "i see",
        "alright",
        "cool",
        "nice",
        "great",
        "good",
        "fine",
        "true",
        "exactly",
        "totally",
        "absolutely",
        "definitely",
        "certainly",
        "indeed",
        "understood",
        "interesting",
        "really",
        "wow",
        # Short affirmations
        "k",
        "kk",
        "ya",
        "yah",
        "yea",
        "aye",
        # Filler sounds
        "um",
        "uh",
        "er",
        "eh",
        "huh",
        "hmm",
        "mmm",
    }
)

# Default words that MUST interrupt the agent immediately when detected
DEFAULT_INTERRUPT_WORDS: frozenset[str] = frozenset(
    {
        # Stop commands
        "stop",
        "wait",
        "hold on",
        "hold up",
        "pause",
        "quiet",
        "silence",
        "shut up",
        "enough",
        "hang on",
        # Negations/corrections
        "no",
        "nope",
        "wrong",
        "incorrect",
        "actually",
        "but",
        "however",
        "excuse me",
        "sorry but",
        "let me",
        "i want to",
        "i need to",
        "i have a",
        "can i",
        "could i",
        "may i",
        "what about",
        "what if",
        "how about",
        # Questions indicating the user wants to speak
        "question",
        "one thing",
        "one second",
        "one moment",
        "just a second",
        "just a moment",
        "before you",
        "before that",
        "wait a",
    }
)


class InterruptDecision(Enum):
    """Decision result from the interruption filter."""

    IGNORE = "ignore"
    """Backchannel detected - agent should continue speaking."""

    INTERRUPT = "interrupt"
    """Real interruption detected - agent should stop immediately."""

    PENDING = "pending"
    """Not enough information yet - wait for more STT context."""

    PASSTHROUGH = "passthrough"
    """No filter applied - use default behavior (agent not speaking or no STT)."""


@dataclass
class InterruptionContext:
    """Context passed to the filter for making interruption decisions."""

    transcript: str
    """Current STT transcript (partial or final)."""

    is_final: bool
    """Whether this is a final transcript."""

    agent_speaking: bool
    """Whether the agent is currently speaking."""

    speech_duration: float
    """Duration of detected user speech in seconds."""

    word_count: int
    """Number of words in the transcript."""


@dataclass
class InterruptionFilterConfig:
    """Configuration for the InterruptionFilter."""

    ignore_words: frozenset[str] = field(default_factory=lambda: DEFAULT_IGNORE_WORDS)
    """Words/phrases that should be ignored when agent is speaking."""

    interrupt_words: frozenset[str] = field(default_factory=lambda: DEFAULT_INTERRUPT_WORDS)
    """Words/phrases that should always interrupt the agent."""

    grace_period_ms: int = 150
    """Milliseconds to wait for STT before making a decision on VAD-only triggers."""

    min_words_for_ignore: int = 1
    """Minimum word count to classify as ignore (single backchannels)."""

    max_words_for_ignore: int = 3
    """Maximum word count that can still be classified as ignore-only."""

    case_sensitive: bool = False
    """Whether word matching should be case-sensitive."""

    @classmethod
    def from_env(cls) -> InterruptionFilterConfig:
        """Create config from environment variables.

        Environment variables:
            LIVEKIT_IGNORE_WORDS: Comma-separated list of ignore words
            LIVEKIT_INTERRUPT_WORDS: Comma-separated list of interrupt words
            LIVEKIT_INTERRUPTION_GRACE_PERIOD_MS: Grace period in milliseconds
        """
        config = cls()

        if env_ignore := os.environ.get("LIVEKIT_IGNORE_WORDS"):
            custom_ignore = frozenset(w.strip().lower() for w in env_ignore.split(",") if w.strip())
            config = InterruptionFilterConfig(
                ignore_words=config.ignore_words | custom_ignore,
                interrupt_words=config.interrupt_words,
                grace_period_ms=config.grace_period_ms,
            )

        if env_interrupt := os.environ.get("LIVEKIT_INTERRUPT_WORDS"):
            custom_interrupt = frozenset(
                w.strip().lower() for w in env_interrupt.split(",") if w.strip()
            )
            config = InterruptionFilterConfig(
                ignore_words=config.ignore_words,
                interrupt_words=config.interrupt_words | custom_interrupt,
                grace_period_ms=config.grace_period_ms,
            )

        if env_grace := os.environ.get("LIVEKIT_INTERRUPTION_GRACE_PERIOD_MS"):
            try:
                config = InterruptionFilterConfig(
                    ignore_words=config.ignore_words,
                    interrupt_words=config.interrupt_words,
                    grace_period_ms=int(env_grace),
                )
            except ValueError:
                logger.warning(f"Invalid LIVEKIT_INTERRUPTION_GRACE_PERIOD_MS: {env_grace}")

        return config


class InterruptionFilter:
    """
    Filters user speech to distinguish backchannels from real interruptions.

    This filter is designed to work in parallel with STT processing. When VAD
    detects speech while the agent is speaking, this filter analyzes the
    transcript to determine if the speech is:

    1. A backchannel (e.g., "yeah", "ok") - agent continues speaking
    2. A real interruption (e.g., "stop", "wait") - agent stops immediately
    3. Pending - waiting for more STT context before deciding

    The filter prioritizes interrupt words over ignore words, so mixed
    utterances like "yeah wait a second" will always interrupt.

    Example:
        ```python
        filter = InterruptionFilter()

        # Agent is speaking, user says "yeah"
        decision = filter.should_interrupt(
            InterruptionContext(
                transcript="yeah",
                is_final=True,
                agent_speaking=True,
                speech_duration=0.3,
                word_count=1,
            )
        )
        assert decision == InterruptDecision.IGNORE

        # Agent is speaking, user says "wait a second"
        decision = filter.should_interrupt(
            InterruptionContext(
                transcript="wait a second",
                is_final=True,
                agent_speaking=True,
                speech_duration=0.8,
                word_count=3,
            )
        )
        assert decision == InterruptDecision.INTERRUPT
        ```
    """

    def __init__(
        self,
        config: InterruptionFilterConfig | None = None,
        *,
        ignore_words: Sequence[str] | None = None,
        interrupt_words: Sequence[str] | None = None,
        custom_classifier: Callable[[InterruptionContext], InterruptDecision | None] | None = None,
    ) -> None:
        """
        Initialize the InterruptionFilter.

        Args:
            config: Full configuration object. If provided, ignore_words and
                interrupt_words parameters are ignored.
            ignore_words: Additional words to ignore (merged with defaults).
            interrupt_words: Additional words that interrupt (merged with defaults).
            custom_classifier: Optional custom classifier function. If it returns
                a decision, that decision is used. If it returns None, the default
                word-matching logic is applied.
        """
        if config is not None:
            self._config = config
        else:
            base_config = InterruptionFilterConfig.from_env()
            merged_ignore = base_config.ignore_words
            merged_interrupt = base_config.interrupt_words

            if ignore_words:
                merged_ignore = merged_ignore | frozenset(
                    w.lower() if not base_config.case_sensitive else w for w in ignore_words
                )
            if interrupt_words:
                merged_interrupt = merged_interrupt | frozenset(
                    w.lower() if not base_config.case_sensitive else w for w in interrupt_words
                )

            self._config = InterruptionFilterConfig(
                ignore_words=merged_ignore,
                interrupt_words=merged_interrupt,
                grace_period_ms=base_config.grace_period_ms,
                case_sensitive=base_config.case_sensitive,
            )

        self._custom_classifier = custom_classifier

        # Pre-compile regex patterns for multi-word phrases
        self._interrupt_patterns: list[re.Pattern[str]] = []
        self._ignore_patterns: list[re.Pattern[str]] = []

        flags = 0 if self._config.case_sensitive else re.IGNORECASE

        for phrase in self._config.interrupt_words:
            if " " in phrase:
                # Multi-word phrase - use word boundary matching
                pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", flags)
                self._interrupt_patterns.append(pattern)

        for phrase in self._config.ignore_words:
            if " " in phrase:
                pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", flags)
                self._ignore_patterns.append(pattern)

    @property
    def config(self) -> InterruptionFilterConfig:
        """Get the current filter configuration."""
        return self._config

    @property
    def grace_period_ms(self) -> int:
        """Get the grace period in milliseconds."""
        return self._config.grace_period_ms

    def should_interrupt(self, ctx: InterruptionContext) -> InterruptDecision:
        """
        Determine whether the user's speech should interrupt the agent.

        Args:
            ctx: The interruption context containing transcript and state info.

        Returns:
            InterruptDecision indicating whether to IGNORE, INTERRUPT, or wait (PENDING).
        """
        # If agent is not speaking, treat everything as valid input
        if not ctx.agent_speaking:
            return InterruptDecision.PASSTHROUGH

        # If transcript is empty, we need to wait for STT
        transcript = ctx.transcript.strip()
        if not transcript:
            return InterruptDecision.PENDING

        # Apply custom classifier first if provided
        if self._custom_classifier is not None:
            custom_decision = self._custom_classifier(ctx)
            if custom_decision is not None:
                return custom_decision

        # Normalize transcript for matching
        normalized = transcript if self._config.case_sensitive else transcript.lower()

        # Check for interrupt words/phrases first (they take priority)
        if self._contains_interrupt_word(normalized):
            logger.info(f"Intent: INTERRUPT transcript={transcript!r}")
            return InterruptDecision.INTERRUPT

        # Check if it's purely a backchannel
        if self._is_backchannel_only(normalized, ctx.word_count):
            logger.info(f"Intent: IGNORE transcript={transcript!r}")
            return InterruptDecision.IGNORE

        # If we have a final transcript with words but no clear classification,
        # treat as a real interruption (user is saying something substantive)
        if ctx.is_final and ctx.word_count > self._config.max_words_for_ignore:
            logger.info(f"Intent: INTERRUPT transcript={transcript!r}")
            return InterruptDecision.INTERRUPT

        # For non-final transcripts with partial content, wait for more
        if not ctx.is_final:
            return InterruptDecision.PENDING

        # Final transcript, short, no interrupt words - likely a backchannel variant
        if ctx.word_count <= self._config.max_words_for_ignore:
            logger.info(f"Intent: IGNORE transcript={transcript!r}")
            return InterruptDecision.IGNORE

        # Default: unclear, treat as interruption to be safe
        logger.info(f"Intent: INTERRUPT transcript={transcript!r}")
        return InterruptDecision.INTERRUPT

    def _contains_interrupt_word(self, normalized_text: str) -> bool:
        """Check if the text contains any interrupt words or phrases."""
        # Check multi-word patterns first
        for pattern in self._interrupt_patterns:
            if pattern.search(normalized_text):
                return True

        # Check single words
        words = self._split_words(normalized_text)
        single_interrupt_words = {
            w for w in self._config.interrupt_words if " " not in w
        }
        matched = words & single_interrupt_words
        if matched:
            return True
        return False

    def _is_backchannel_only(self, normalized_text: str, word_count: int) -> bool:
        """Check if the text consists only of backchannel words/phrases."""
        # Too many words to be just a backchannel
        if word_count > self._config.max_words_for_ignore:
            return False

        # Check if entire text matches a multi-word ignore phrase
        for pattern in self._ignore_patterns:
            if pattern.fullmatch(normalized_text.strip()):
                return True

        # Check if all words are ignore words
        words = self._split_words(normalized_text)
        if not words:
            return False

        single_ignore_words = {w for w in self._config.ignore_words if " " not in w}
        return words.issubset(single_ignore_words)

    def _split_words(self, text: str) -> set[str]:
        """Split text into a set of words, removing punctuation."""
        # Remove common punctuation and split
        cleaned = re.sub(r"[^\w\s-]", "", text)
        return {w.strip() for w in cleaned.split() if w.strip()}

    def on_interruption_suppressed(self, ctx: InterruptionContext) -> None:
        """
        Called when an interruption is suppressed by this filter.

        Override this method to add custom logging or metrics.

        Args:
            ctx: The interruption context that was suppressed.
        """
        pass
