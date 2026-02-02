"""
Backchannel filtering module for context-aware interruption handling.

This module provides functionality to detect passive acknowledgement words 
like "yeah", "ok", "hmm" that users say while listening to indicate engagement,
without intending to interrupt the speaker.

When the agent is speaking, these filler words should be ignored to allow
seamless continuation of speech without pause or stutter.
"""

from __future__ import annotations

import re
from typing import FrozenSet


# Default words commonly used for backchanneling / passive acknowledgement
DEFAULT_BACKCHANNEL_WORDS: FrozenSet[str] = frozenset({
    "yeah", "yea", "ya", "yep", "yup", "yes", "yess", 
    "ok", "okay", "okie", "k", "kay", 
    "right", "alright", "aight", "sure", "surely",
    "aha", "ah ha", "a-ha", 
    "hmm", "hm", "hmm-hmm", "hmmm", "mm", "mmm", "mhm", "mm-hmm", "mmhmm",
    "uh huh", "uh-huh", "uhuh", 
    "got it", "gotcha", "gotchu", "i see", "see", "oh i see",
    "oh", "ohh", "oh ok", "oh okay", "cool", "nice", "great", "good",
    "uh", "um", "er", "ah", "eh"
})

# Words that indicate real intent/commands, not backchanneling
COMMAND_WORDS: FrozenSet[str] = frozenset({
    "stop", "wait", "hold", "pause", "halt", "quiet", "silence", "enough",
    "what", "why", "how", "when", "where", "who", "which",
    "no", "not", "never",
    "can", "could", "would", "should", "will", "do", "does", "did",
    "however", "actually", "instead", "rather",
    "also", "plus", "another",
    "hey", "listen", "excuse", "sorry",
    "repeat", "again", "pardon", "huh"
})


class BackchannelFilter:
    # A class to detect and filter backchannel (passive acknowledgement) speech.
    
    def __init__(
        self,
        backchannel_words: FrozenSet[str] | None = None,
        command_words: FrozenSet[str] | None = None,
        max_words: int = 5
    ):
        # Initialize the BackchannelFilter.

        self._backchannel_words = backchannel_words or DEFAULT_BACKCHANNEL_WORDS
        self._command_words = command_words or COMMAND_WORDS
        self._max_words = max_words
        self._pattern: re.Pattern | None = None
    
    @property
    def backchannel_words(self) -> FrozenSet[str]:
        return self._backchannel_words
    
    @property
    def command_words(self) -> FrozenSet[str]:
        return self._command_words
    
    @property
    def max_words(self) -> int:
        return self._max_words
    
    def _get_pattern(self) -> re.Pattern:
        # Get or create the regex pattern for backchannel matching.
        if self._pattern is None:
            sorted_words = sorted(self._backchannel_words, key=len, reverse=True)
            pattern = "|".join(re.escape(word) for word in sorted_words)
            self._pattern = re.compile(f"^({pattern})$", re.IGNORECASE)
        return self._pattern
    
    @staticmethod
    def normalize(transcript: str) -> str:
        # Normalize transcript for comparison.
        text = transcript.lower().strip()
        text = re.sub(r"[.,!?;:'\"-]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def is_backchannel(self, transcript: str) -> bool:
        # Determine if a transcript is a passive acknowledgement (backchannel).
        # True if the transcript is a passive acknowledgement, False otherwise
        if not transcript:
            return False
        
        normalized = self.normalize(transcript)
        if not normalized:
            return False
        
        words = normalized.split()
        word_count = len(words)
        
        # Too many words = likely a real statement
        if word_count > self._max_words:
            return False
        
        # Contains command words = likely a real interruption
        if self.contains_command_words(normalized):
            return False
        
        # Check if entire transcript matches a known backchannel phrase
        if normalized in self._backchannel_words:
            return True
        
        # Single word check
        if word_count == 1 and words[0] in self._backchannel_words:
            return True
        
        # All words are fillers (handles "ok ok ok", "yeah yeah yeah")
        if all(word in self._backchannel_words for word in words):
            return True
        
        # Pattern match for variations
        if self._get_pattern().match(normalized):
            return True
        
        return False
    
    def contains_command_words(self, transcript: str) -> bool:
        # Check if transcript contains words indicating command intent.
        if not transcript:
            return False
        
        words = set(transcript.lower().split())
        return bool(words & self._command_words)
    
    def is_likely_continuation(self, transcript: str) -> bool:
        # Check if transcript looks like the user is continuing their thought.
        normalized = self.normalize(transcript)
        words = normalized.split()
        
        if len(words) <= 2:
            return False
        
        first_word = words[0] if words else ""
        if first_word in self._backchannel_words and len(words) > 2:
            return True
        
        return False


# Module-level functions for backward compatibility
_default_filter: BackchannelFilter | None = None


def _get_default_filter() -> BackchannelFilter:
    # Get or create the default filter instance.
    global _default_filter
    if _default_filter is None:
        _default_filter = BackchannelFilter()
    return _default_filter


def normalize_transcript(transcript: str) -> str:
    # Normalize transcript for comparison.
    return BackchannelFilter.normalize(transcript)


def is_backchannel(
    transcript: str,
    *,
    max_words: int = 5,
    custom_words: FrozenSet[str] | None = None,
) -> bool:
    # Determine if a transcript is a passive acknowledgement (backchannel).
    if custom_words is not None or max_words != 5:
        # Create a custom filter instance
        filter_instance = BackchannelFilter(
            backchannel_words=custom_words,
            max_words=max_words
        )
        return filter_instance.is_backchannel(transcript)
    
    return _get_default_filter().is_backchannel(transcript)


def contains_command_words(transcript: str) -> bool:
    # Check if transcript contains words indicating command intent.
    return _get_default_filter().contains_command_words(transcript)


def is_likely_continuation(transcript: str) -> bool:
    # Check if transcript looks like the user is continuing their thought.
    return _get_default_filter().is_likely_continuation(transcript)