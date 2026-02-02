"""Intelligent interruption filtering for voice agents.

This module provides state-aware filtering to distinguish between passive
acknowledgements (backchanneling) and active interruptions during voice 
conversations.

When the agent is speaking:
- Backchannel words like "yeah", "ok", "hmm" are ignored
- Command words like "stop", "wait", "no" trigger interruption
- Mixed inputs like "yeah but wait" trigger interruption (due to "wait")

When the agent is silent:
- All user input is processed normally, including backchannel words
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ..log import logger

if TYPE_CHECKING:
    from .events import AgentState


# Default backchannel words - words that indicate passive listening
DEFAULT_BACKCHANNEL_WORDS: set[str] = {
    # Affirmative sounds
    "yeah", "yea", "yes", "yep", "yup", "ya",
    # OK variations
    "ok", "okay", "k", "okey",
    # Acknowledgement sounds (various spellings from different STT engines)
    "uh-huh", "uh huh", "uhuh", "uh", "uhhuh",
    "hmm", "hm", "mmm", "mm", "hmmm",
    "mhm", "mhmm", "mm-hmm", "mmhmm", "mm hmm", "m-hm",
    "uh-hm", "uhm", "umhm",
    # Agreement words
    "right", "sure", "alright", "all right", "aight",
    "gotcha", "got it", "i see", "see", "i understand",
    # Sounds
    "aha", "ah", "oh", "ooh", "aah", "ahh",
    # Filler words
    "um", "erm", "like", "well",
    # Continuers
    "go on", "continue", "uh huh go on",
}

# Default interrupt words - words that should always trigger interruption
DEFAULT_INTERRUPT_WORDS: set[str] = {
    # Stop commands
    "stop", "wait", "hold", "hold on", "pause",
    # Negatives
    "no", "nope", "never", "never mind", "nevermind",
    # Corrections/changes
    "actually", "but", "however", "although",
    "hang on", "one second", "one moment",
    # Attention getters
    "excuse me", "sorry", "pardon",
    "question", "hey", "listen",
    # Topic changes
    "anyway", "by the way", "btw",
}


@dataclass
class InterruptionFilterConfig:
    """Configuration for intelligent interruption handling.
    
    Attributes:
        backchannel_words: Set of words to ignore when agent is speaking.
            These represent passive acknowledgements that don't require response.
        interrupt_words: Set of words that always trigger interruption.
            These represent commands or topic changes that need attention.
        enabled: Whether the filter is active. When False, all speech
            triggers interruption (default behavior).
    """
    
    backchannel_words: set[str] = field(
        default_factory=lambda: DEFAULT_BACKCHANNEL_WORDS.copy()
    )
    interrupt_words: set[str] = field(
        default_factory=lambda: DEFAULT_INTERRUPT_WORDS.copy()
    )
    enabled: bool = True


class InterruptionFilter:
    """State-aware filter for distinguishing interruptions from backchanneling.
    
    This filter analyzes user transcripts in the context of the agent's current
    state to determine if the input should trigger an interruption.
    
    Example:
        ```python
        filter = InterruptionFilter()
        
        # Agent is speaking, user says "yeah" -> no interruption
        filter.should_interrupt("yeah", "speaking")  # Returns False
        
        # Agent is silent, user says "yeah" -> process as input
        filter.should_interrupt("yeah", "listening")  # Returns True
        
        # Agent is speaking, user says "stop" -> interrupt
        filter.should_interrupt("stop", "speaking")  # Returns True
        
        # Agent is speaking, user says "yeah but wait" -> interrupt
        filter.should_interrupt("yeah but wait", "speaking")  # Returns True
        ```
    """
    
    def __init__(self, config: InterruptionFilterConfig | None = None) -> None:
        """Initialize the interruption filter.
        
        Args:
            config: Filter configuration. Uses defaults if not provided.
        """
        self._config = config or InterruptionFilterConfig()
        
        # Pre-compile word patterns for efficient matching
        self._backchannel_pattern = self._compile_word_pattern(
            self._config.backchannel_words
        )
        self._interrupt_pattern = self._compile_word_pattern(
            self._config.interrupt_words
        )
    
    @property
    def config(self) -> InterruptionFilterConfig:
        """Get the current filter configuration."""
        return self._config
    
    def _compile_word_pattern(self, words: set[str]) -> re.Pattern[str] | None:
        """Compile a regex pattern for word matching.
        
        Creates a pattern that matches any of the words as complete words
        (not substrings), case-insensitive. Hyphenated words are converted
        to flexible patterns that match hyphen, space, or no separator.
        """
        if not words:
            return None
        
        patterns = []
        for word in words:
            # Convert hyphens and spaces to flexible separators
            # This allows "uh-huh" to match "uh-huh", "uh huh", or "uhhuh"
            parts = re.split(r'[-\s]+', word)
            if len(parts) > 1:
                # Multi-part word: create flexible pattern
                # Each separator can be hyphen, space, or nothing
                escaped_parts = [re.escape(part) for part in parts if part]
                flexible = r'[-\s]*'.join(escaped_parts)
                patterns.append(flexible)
            else:
                # Single word: just escape it
                patterns.append(re.escape(word))
        
        # Join all patterns with OR
        combined = "|".join(patterns)
        return re.compile(rf"\b({combined})\b", re.IGNORECASE)
    
    def _normalize_transcript(self, transcript: str) -> str:
        """Normalize transcript for matching.
        
        Removes punctuation and extra whitespace, converts to lowercase.
        """
        # Remove common punctuation
        normalized = re.sub(r"[,.!?;:'\"-]", " ", transcript)
        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip().lower()
    
    def _contains_interrupt_word(self, transcript: str) -> bool:
        """Check if transcript contains any interrupt words."""
        if self._interrupt_pattern is None:
            return False
        return bool(self._interrupt_pattern.search(transcript))
    
    def _is_only_backchannel(self, transcript: str) -> bool:
        """Check if transcript consists entirely of backchannel words.
        
        Returns True only if:
        - The transcript is not empty
        - All words in the transcript are backchannel words
        """
        if not transcript or self._backchannel_pattern is None:
            return False
        
        normalized = self._normalize_transcript(transcript)
        if not normalized:
            return False
        
        # Find all backchannel matches
        matches = self._backchannel_pattern.findall(normalized)
        if not matches:
            return False
        
        # Remove all backchannel words and see if anything remains
        remaining = self._backchannel_pattern.sub("", normalized)
        remaining = re.sub(r"\s+", "", remaining)  # Remove whitespace
        
        return len(remaining) == 0
    
    def should_interrupt(
        self,
        transcript: str,
        agent_state: AgentState,
    ) -> bool:
        """Determine if a transcript should trigger an interruption.
        
        Decision logic:
        1. If filter is disabled, always return True (allow interrupt)
        2. If agent is NOT speaking, always return True (process input)
        3. If agent IS speaking:
           a. If transcript contains interrupt words → return True
           b. If transcript is ONLY backchannel words → return False
           c. Otherwise → return True (unknown words may be important)
        
        Args:
            transcript: The user's speech transcript
            agent_state: Current state of the agent
            
        Returns:
            True if the transcript should trigger an interruption,
            False if it should be ignored as backchanneling.
        """
        # Disabled filter = allow all interruptions
        if not self._config.enabled:
            return True
        
        # Only filter when agent is speaking
        if agent_state != "speaking":
            logger.debug(
                "allowing input, agent not speaking",
                extra={"transcript": transcript, "agent_state": agent_state}
            )
            return True
        
        # Normalize for matching
        normalized = self._normalize_transcript(transcript)
        
        if not normalized:
            # Empty transcript - don't interrupt
            return False
        
        # Check for interrupt words first (highest priority)
        if self._contains_interrupt_word(normalized):
            logger.debug(
                "interrupt word detected",
                extra={"transcript": transcript}
            )
            return True
        
        # Check if it's only backchannel words
        if self._is_only_backchannel(normalized):
            logger.debug(
                "filtering backchannel input while agent speaking",
                extra={"transcript": transcript}
            )
            return False
        
        # Unknown words - allow interruption to be safe
        logger.debug(
            "allowing potential interruption (unknown words)",
            extra={"transcript": transcript}
        )
        return True
    
    def update_config(
        self,
        *,
        backchannel_words: set[str] | None = None,
        interrupt_words: set[str] | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Update filter configuration dynamically.
        
        Args:
            backchannel_words: New backchannel word set (replaces existing)
            interrupt_words: New interrupt word set (replaces existing)
            enabled: Whether filter is enabled
        """
        if backchannel_words is not None:
            self._config.backchannel_words = backchannel_words
            self._backchannel_pattern = self._compile_word_pattern(backchannel_words)
        
        if interrupt_words is not None:
            self._config.interrupt_words = interrupt_words
            self._interrupt_pattern = self._compile_word_pattern(interrupt_words)
        
        if enabled is not None:
            self._config.enabled = enabled