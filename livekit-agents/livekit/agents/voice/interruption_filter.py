"""
Intelligent Interruption Filter for LiveKit Agents

This module provides context-aware filtering of user speech to distinguish between:
- Backchanneling (passive acknowledgements like "yeah", "ok", "hmm") while agent is speaking
- Active interruptions that should stop the agent
- Valid input when the agent is silent

The filter ensures the agent continues speaking seamlessly when users provide
backchanneling feedback, while still responding appropriately to actual interruptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# Default list of backchanneling/filler words that should be ignored while agent is speaking
DEFAULT_BACKCHANNELING_WORDS = frozenset([
    # English acknowledgements
    "yeah", "yea", "yep", "yes", "yup", "ya",
    "ok", "okay", "k",
    "hmm", "hm", "mm", "mmhmm", "mhm", "uh-huh", "uhuh", "uh huh",
    "right", "alright", "sure",
    "i see", "got it", "gotcha",
    "ah", "aha", "oh", "ooh",
    "nice", "cool", "great", "good", "fine",
    "true", "indeed",
    # Common fillers
    "uh", "um", "er", "like",
])

# Words that always trigger interruption regardless of backchanneling
DEFAULT_INTERRUPT_KEYWORDS = frozenset([
    "wait", "stop", "hold on", "hold", "pause", "no",
    "actually", "but", "however", "excuse me",
    "question", "what", "why", "how", "when", "where", "who",
    "can you", "could you", "would you",
    "i have", "i need", "i want",
    "let me", "hang on", "one second", "one moment",
    "sorry", "pardon",
])


@dataclass
class InterruptionFilterConfig:
    """Configuration for the intelligent interruption filter."""

    # Words to ignore when agent is speaking (backchanneling)
    backchanneling_words: frozenset[str] = field(default_factory=lambda: DEFAULT_BACKCHANNELING_WORDS)

    # Words that always trigger interruption
    interrupt_keywords: frozenset[str] = field(default_factory=lambda: DEFAULT_INTERRUPT_KEYWORDS)

    # Whether to enable the intelligent filtering (can be disabled to revert to default behavior)
    enabled: bool = True

    # Minimum word count in transcript to bypass backchanneling filter
    # If user says more than this many words, treat as real input
    max_backchanneling_words: int = 3


@dataclass
class InterruptionDecision:
    """Result of the interruption filter analysis."""

    # The decision: "ignore", "interrupt", or "respond"
    action: Literal["ignore", "interrupt", "respond"]

    # Reason for the decision (for logging/debugging)
    reason: str

    # The analyzed transcript
    transcript: str

    # Whether the agent was speaking when this was analyzed
    agent_was_speaking: bool


class InterruptionFilter:
    """
    Context-aware filter for handling user speech interruptions.

    This filter implements the logic matrix:
    - "Yeah/Ok/Hmm" + Agent Speaking → IGNORE (continue speaking)
    - "Wait/Stop/No" + Agent Speaking → INTERRUPT (stop immediately)
    - "Yeah/Ok/Hmm" + Agent Silent → RESPOND (treat as valid input)
    - Any speech + Agent Silent → RESPOND (normal conversation)
    """

    def __init__(self, config: InterruptionFilterConfig | None = None):
        self._config = config or InterruptionFilterConfig()
        # Normalization logic
        self._config.backchanneling_words = frozenset(
            self._normalize_text(w) for w in self._config.backchanneling_words
        )
        self._config.interrupt_keywords = frozenset(
            self._normalize_text(w) for w in self._config.interrupt_keywords
        )

    @property
    def config(self) -> InterruptionFilterConfig:
        return self._config

    @config.setter
    def config(self, value: InterruptionFilterConfig) -> None:
        self._config = value

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase and remove extra whitespace
        text = text.lower().strip()
        # Remove punctuation except hyphens (for "uh-huh")
        text = re.sub(r'[^\w\s\-]', '', text)
        return text

    def _extract_words(self, text: str) -> list[str]:
        """Extract individual words from text."""
        normalized = self._normalize_text(text)
        return normalized.split()

    def _is_only_backchanneling(self, text: str) -> bool:
        """Check if the text contains only backchanneling words."""
        normalized = self._normalize_text(text)
        words = self._extract_words(text)

        if not words:
            return True

        # Check if word count exceeds threshold
        if len(words) > self._config.max_backchanneling_words:
            return False

        # Check if the entire normalized text matches a backchanneling phrase
        if normalized in self._config.backchanneling_words:
            return True

        # Check if all individual words are backchanneling
        for word in words:
            if word not in self._config.backchanneling_words:
                return False

        return True

    def _contains_interrupt_keyword(self, text: str) -> bool:
        """Check if the text contains any interrupt keywords."""
        normalized = self._normalize_text(text)

        # Check for exact phrase matches first
        for keyword in self._config.interrupt_keywords:
            if keyword in normalized:
                return True

        return False

    def analyze(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> InterruptionDecision:
        """
        Analyze a transcript and determine the appropriate action.

        Args:
            transcript: The user's speech transcript
            agent_is_speaking: Whether the agent is currently speaking/generating audio

        Returns:
            InterruptionDecision with the recommended action
        """
        if not self._config.enabled:
            # Filter disabled - always allow interruption
            return InterruptionDecision(
                action="interrupt" if agent_is_speaking else "respond",
                reason="Filter disabled",
                transcript=transcript,
                agent_was_speaking=agent_is_speaking,
            )

        transcript = transcript.strip()

        if not transcript:
            return InterruptionDecision(
                action="ignore",
                reason="Empty transcript",
                transcript=transcript,
                agent_was_speaking=agent_is_speaking,
            )

        # Case 1: Agent is NOT speaking - always respond to any input
        if not agent_is_speaking:
            return InterruptionDecision(
                action="respond",
                reason="Agent is silent, treating as valid input",
                transcript=transcript,
                agent_was_speaking=agent_is_speaking,
            )

        # Case 2: Agent IS speaking - need to determine if this is backchanneling or real interruption

        # Check for interrupt keywords first (higher priority)
        if self._contains_interrupt_keyword(transcript):
            return InterruptionDecision(
                action="interrupt",
                reason=f"Contains interrupt keyword",
                transcript=transcript,
                agent_was_speaking=agent_is_speaking,
            )

        # Check if it's only backchanneling
        if self._is_only_backchanneling(transcript):
            return InterruptionDecision(
                action="ignore",
                reason="Backchanneling while agent speaking",
                transcript=transcript,
                agent_was_speaking=agent_is_speaking,
            )

        # Default: treat as real interruption
        return InterruptionDecision(
            action="interrupt",
            reason="Non-backchanneling speech while agent speaking",
            transcript=transcript,
            agent_was_speaking=agent_is_speaking,
        )

    def should_interrupt(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> bool:
        """
        Convenience method to check if an interruption should occur.

        Returns True if the agent should stop speaking, False if it should continue.
        """
        decision = self.analyze(transcript, agent_is_speaking)
        return decision.action == "interrupt"

    def should_ignore(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> bool:
        """
        Convenience method to check if input should be ignored.

        Returns True if the input should be completely ignored (backchanneling while speaking).
        """
        decision = self.analyze(transcript, agent_is_speaking)
        return decision.action == "ignore"
