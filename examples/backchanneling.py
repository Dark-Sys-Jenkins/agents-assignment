"""
Backchanneling Detection for LiveKit Agents

This module provides intelligent filtering of backchanneling words (like "yeah", "ok", "hmm")
to prevent false interruptions when the agent is speaking.

The key insight is that the same word ("yeah") should be:
- IGNORED when the agent is speaking (it's just acknowledgement)
- PROCESSED when the agent is silent (it's a real response)
"""

from __future__ import annotations

import os
import re
from typing import Set, List

from ..log import logger


# Default words that indicate passive acknowledgement (backchanneling)
DEFAULT_BACKCHANNELING_WORDS: Set[str] = {
    "yeah", "yep", "yes", "ok", "okay", "uh-huh", "huh",
    "hmm", "um", "uh", "ah", "right", "sure",
    "i see", "got it", "understood", "mm-hmm", "mhm",
    "alright", "uh huh", "yup", "ya", "yea",
}

# Default words that should always trigger an interruption
DEFAULT_INTERRUPT_WORDS: Set[str] = {
    "wait", "stop", "pause", "hold", "hold on", "no", "dont", "don't",
    "shut up", "quiet", "stop talking", "enough",
    "never mind", "nevermind", "actually", "cancel",
    "hang on", "one second", "excuse me",
}


def _split_phrases(items: Set[str]) -> tuple[Set[str], Set[str]]:
    """Split a set into (single_words, multi_word_phrases)."""
    singles: Set[str] = set()
    phrases: Set[str] = set()
    for x in items:
        x = x.strip().lower()
        if not x:
            continue
        if " " in x:
            phrases.add(x)
        else:
            singles.add(x)
    return singles, phrases


class BackchannelingFilter:
    """
    Filters backchanneling words to prevent false interruptions.
    
    This filter checks if user speech is just passive acknowledgement
    (backchanneling) or an active attempt to interrupt/communicate.
    """
    
    def __init__(
        self,
        backchanneling_words: Set[str] | None = None,
        interrupt_words: Set[str] | None = None,
    ):
        """
        Initialize the backchanneling filter.
        
        Args:
            backchanneling_words: Words to ignore when agent is speaking.
                                  If None, uses DEFAULT_BACKCHANNELING_WORDS.
            interrupt_words: Words that always trigger interruption.
                            If None, uses DEFAULT_INTERRUPT_WORDS.
        """
        self._backchanneling_words = backchanneling_words or DEFAULT_BACKCHANNELING_WORDS.copy()
        self._interrupt_words = interrupt_words or DEFAULT_INTERRUPT_WORDS.copy()
        
        # Load from environment variables if set
        self._load_from_env()
        
        # Pre-split for efficient matching
        self._bc_single, self._bc_phrases = _split_phrases(self._backchanneling_words)
        self._int_single, self._int_phrases = _split_phrases(self._interrupt_words)
    
    def _load_from_env(self) -> None:
        """Load word lists from environment variables."""
        bc_env = os.getenv("BACKCHANNELING_WORDS", "").strip()
        if bc_env:
            self._backchanneling_words = {
                w.lower().strip() for w in bc_env.split(",") if w.strip()
            }
        
        int_env = os.getenv("INTERRUPT_WORDS", "").strip()
        if int_env:
            self._interrupt_words = {
                w.lower().strip() for w in int_env.split(",") if w.strip()
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        t = text.lower().strip()
        # Remove punctuation but keep spaces
        t = re.sub(r"[^a-z0-9\s]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    
    def _tokenize(self, text: str) -> List[str]:
        """Split text into tokens."""
        norm = self._normalize_text(text)
        return [w for w in norm.split(" ") if w]
    
    def contains_interrupt_word(self, text: str) -> bool:
        """
        Check if text contains any interrupt words.
        
        Interrupt words like "wait", "stop", "no" should always
        trigger an interruption regardless of context.
        """
        norm = self._normalize_text(text)
        tokens = self._tokenize(text)
        
        # Check multi-word phrases first
        for phrase in self._int_phrases:
            if f" {phrase} " in f" {norm} ":
                return True
        
        # Check single words
        return any(tok in self._int_single for tok in tokens)
    
    def is_pure_backchanneling(self, text: str) -> bool:
        """
        Check if text consists entirely of backchanneling words.
        
        Returns True if the text is only passive acknowledgement
        like "yeah", "ok", "uh-huh", "yeah ok hmm", etc.
        """
        norm = self._normalize_text(text)
        if not norm:
            return True  # Empty is considered backchanneling (noise)
        
        tokens = self._tokenize(text)
        if not tokens:
            return True
        
        # Check if entire text matches a known phrase
        if norm in self._bc_phrases:
            return True
        
        # Check if all tokens are backchanneling words
        return all(tok in self._bc_single for tok in tokens)
    
    def should_filter_interruption(self, transcript: str) -> bool:
        """
        Determine if this transcript should be filtered (not cause interruption).
        
        This is the main method to call when deciding whether to interrupt.
        
        Args:
            transcript: The user's speech transcript
            
        Returns:
            True if the transcript should be FILTERED (agent continues speaking)
            False if the transcript should cause an INTERRUPTION
        """
        if not transcript or not transcript.strip():
            return True  # Empty transcript - filter it
        
        # If it contains explicit interrupt words, don't filter
        if self.contains_interrupt_word(transcript):
            logger.debug(
                "backchanneling filter: contains interrupt word, allowing interruption",
                extra={"transcript": transcript}
            )
            return False
        
        # If it's pure backchanneling, filter it
        if self.is_pure_backchanneling(transcript):
            logger.debug(
                "backchanneling filter: pure backchanneling detected, filtering",
                extra={"transcript": transcript}
            )
            return True
        
        # Unknown content - allow interruption (conservative)
        logger.debug(
            "backchanneling filter: unknown content, allowing interruption",
            extra={"transcript": transcript}
        )
        return False
    
    @property
    def backchanneling_words(self) -> Set[str]:
        """Get the current set of backchanneling words."""
        return self._backchanneling_words.copy()
    
    @property
    def interrupt_words(self) -> Set[str]:
        """Get the current set of interrupt words."""
        return self._interrupt_words.copy()

