"""
Backchannel filter for intelligent interruption handling.

This module provides context-aware filtering of user inputs to distinguish
between passive acknowledgements (backchannels like "yeah", "ok", "hmm") and
active interruptions ("stop", "wait", "no").

The filter is state-aware:
- When agent is speaking: backchannels are ignored, commands trigger interrupts
- When agent is silent: all inputs (including backchannels) are processed normally
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

# Default backchannel words that should be ignored when agent is speaking
DEFAULT_BACKCHANNEL_WORDS: frozenset[str] = frozenset({
    # Affirmatives
    "yeah",
    "yep", 
    "yes",
    "ok",
    "okay",
    "aha",
    "yup",
    "sure",
    "right",
    "alright",
    # Partials/Colloquial
    "ye",
    "yea",
    "oh",
    "ah",
    "uh",
    "um",
    "uhm",
    "uhh",
    "er",
    # Sounds/vocalizations
    "hmm",
    "mhm",
    "mhmm",
    "uh-huh",
    "uhuh",
    "uh huh",
    "mm",
    "mm-hmm",
    "mmhmm",
    "hm",
    "oops",
    # Acknowledgements
    "got it",
    "i see",
    "interesting",
    # Encouragements (to continue speaking)
    "go on",
    "go ahead",
    "continue",
    "keep going",
})

# Words that force interruption even if mixed with backchannels
DEFAULT_INTERRUPT_WORDS: frozenset[str] = frozenset({
    "stop",
    "wait",
    "hold on",
    "hold",
    "no",
    "pause",
    "actually",
    "but",
    "however",
    "hang on",
    "one second",
    "second",
    "minute",
    "question",
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
})


@dataclass
class BackchannelFilterOptions:
    """Options for backchannel filtering.
    
    Attributes:
        enabled: Whether backchannel filtering is enabled (default: True).
        backchannel_words: Set of words considered as backchannels.
        interrupt_words: Set of words that force interruption.
    """
    enabled: bool = True
    backchannel_words: frozenset[str] | None = None
    interrupt_words: frozenset[str] | None = None
    
    def __post_init__(self) -> None:
        if self.backchannel_words is None:
            self.backchannel_words = DEFAULT_BACKCHANNEL_WORDS
        if self.interrupt_words is None:
            self.interrupt_words = DEFAULT_INTERRUPT_WORDS


class BackchannelFilter:
    """
    Filters user inputs to distinguish between backchannels and interruptions.
    
    This filter implements state-based logic:
    - When the agent is speaking, backchannels are ignored
    - When the agent is silent, all inputs are treated as valid
    - Interrupt words always trigger an interruption regardless of context
    
    Example usage:
        filter = BackchannelFilter()
        
        # Agent speaking, user says "yeah"
        filter.should_interrupt("yeah", agent_speaking=True)  # Returns False
        
        # Agent speaking, user says "stop"
        filter.should_interrupt("stop", agent_speaking=True)  # Returns True
        
        # Agent silent, user says "yeah"
        filter.should_interrupt("yeah", agent_speaking=False)  # Returns True
    """
    
    def __init__(
        self,
        *,
        backchannel_words: frozenset[str] | Sequence[str] | None = None,
        interrupt_words: frozenset[str] | Sequence[str] | None = None,
    ) -> None:
        """Initialize the BackchannelFilter.
        
        Args:
            backchannel_words: Custom set of backchannel words. Defaults to 
                DEFAULT_BACKCHANNEL_WORDS if None.
            interrupt_words: Custom set of interrupt words. Defaults to
                DEFAULT_INTERRUPT_WORDS if None.
        """
        if backchannel_words is None:
            self._backchannel_words = DEFAULT_BACKCHANNEL_WORDS
        elif isinstance(backchannel_words, frozenset):
            self._backchannel_words = backchannel_words
        else:
            self._backchannel_words = frozenset(w.lower() for w in backchannel_words)
            
        if interrupt_words is None:
            self._interrupt_words = DEFAULT_INTERRUPT_WORDS
        elif isinstance(interrupt_words, frozenset):
            self._interrupt_words = interrupt_words
        else:
            self._interrupt_words = frozenset(w.lower() for w in interrupt_words)
    
    @property
    def backchannel_words(self) -> frozenset[str]:
        """Get the set of backchannel words."""
        return self._backchannel_words
    
    @property
    def interrupt_words(self) -> frozenset[str]:
        """Get the set of interrupt words."""
        return self._interrupt_words
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing punctuation and lowercasing."""
        # Remove punctuation except hyphens (for words like "uh-huh")
        cleaned = re.sub(r"[^\w\s\-]", "", text).lower().strip()
        # Normalize multiple spaces
        return re.sub(r"\s+", " ", cleaned)
    
    def _split_words(self, text: str) -> list[str]:
        """Split text into individual words."""
        return self._normalize_text(text).split()
    
    def contains_interrupt_word(self, text: str) -> bool:
        """Check if the text contains any interrupt word.
        
        This also checks for multi-word interrupt phrases like "hold on".
        
        Args:
            text: The user input text.
            
        Returns:
            True if the text contains an interrupt word/phrase.
        """
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        # Check for single-word interrupts
        for word in words:
            if word in self._interrupt_words:
                return True
        
        # Check for multi-word interrupt phrases
        for phrase in self._interrupt_words:
            if " " in phrase and phrase in normalized:
                return True
                
        return False
    
    def is_pure_backchannel(self, text: str) -> bool:
        """Check if the text consists entirely of backchannel words.
        
        Args:
            text: The user input text.
            
        Returns:
            True if all words in the text are backchannels.
        """
        normalized = self._normalize_text(text)
        if not normalized:
            return False
            
        words = normalized.split()
        if not words:
            return False
        
        # First check if it contains any interrupt words
        if self.contains_interrupt_word(text):
            return False
        
        # Check if entire phrase is a known backchannel
        if normalized in self._backchannel_words:
            return True
        
        # Check if all individual words are backchannels
        return all(word in self._backchannel_words for word in words)
    
    def should_interrupt(self, text: str, *, agent_speaking: bool) -> bool:
        """Determine if the given text should trigger an interruption.
        
        The logic follows this matrix:
        
        | User Input      | Agent Speaking | Result    |
        |-----------------|----------------|-----------|
        | Backchannel     | Yes            | No interrupt (ignore) |
        | Interrupt word  | Yes            | Interrupt |
        | Mixed input     | Yes            | Interrupt |
        | Any input       | No             | Process (return True) |
        
        Args:
            text: The user input text (from STT).
            agent_speaking: Whether the agent is currently speaking.
            
        Returns:
            True if the input should trigger an interrupt/be processed.
            False if the input should be ignored (pure backchannel while speaking).
        """
        if not text or not text.strip():
            return False
        
        # When agent is not speaking, always process all inputs
        if not agent_speaking:
            return True
        
        # When agent is speaking:
        # 1. Check for interrupt words first - they always interrupt
        if self.contains_interrupt_word(text):
            return True
        
        # 2. Check if it's a pure backchannel - ignore these
        if self.is_pure_backchannel(text):
            return False
        
        # 3. Any other input should interrupt
        return True
    
    def is_valid_input_when_silent(self, text: str) -> bool:
        """Check if text is valid user input when agent is silent.
        
        When the agent is silent, all inputs including backchannels 
        should be treated as valid user input.
        
        Args:
            text: The user input text.
            
        Returns:
            True if there is any content to process.
        """
        return bool(text and text.strip())
