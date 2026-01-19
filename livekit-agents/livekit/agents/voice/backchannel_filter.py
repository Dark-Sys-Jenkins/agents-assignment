from __future__ import annotations

import re
from typing import Sequence

from ..tokenize.basic import split_words


class BackchannelFilter:
    """Filters backchanneling (filler words) when agent is speaking.
    
    This filter distinguishes between passive acknowledgements (like "yeah", "ok")
    and active interruptions (like "wait", "stop", "no") based on whether the
    agent is currently speaking.
    """

    # Default list of filler words that should be ignored when agent is speaking
    DEFAULT_IGNORE_WORDS = [
        "yeah",
        "ok",
        "okay",
        "hmm",
        "right",
        "uh-huh",
        "uh",
        "um",
        "yep",
        "sure",
        "mhm",
        "mm-hmm",
        "mm",
        "aha",
        "uh-huh",
        "mhmm",
    ]

    # Words that indicate an interruption command
    INTERRUPTION_COMMANDS = [
        "wait",
        "stop",
        "no",
        "hold",
        "pause",
        "cancel",
        "nevermind",
        "never mind",
    ]

    def __init__(self, ignore_words: Sequence[str] | None = None) -> None:
        """Initialize the backchannel filter.
        
        Args:
            ignore_words: Custom list of words to ignore when agent is speaking.
                If None, uses DEFAULT_IGNORE_WORDS.
        """
        if ignore_words is None:
            ignore_words = self.DEFAULT_IGNORE_WORDS
        
        # Normalize to lowercase for case-insensitive matching
        self._ignore_words = {word.lower().strip() for word in ignore_words}
        self._interruption_commands = {cmd.lower().strip() for cmd in self.INTERRUPTION_COMMANDS}

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()

    def _extract_words(self, text: str) -> list[str]:
        """Extract words from text, handling punctuation."""
        if not text or not text.strip():
            return []
        
        # Split words using the same logic as the existing codebase
        word_tuples = split_words(text, split_character=True, ignore_punctuation=True)
        # Extract just the word text (first element of each tuple)
        words = [word for word, _, _ in word_tuples]
        # Normalize to lowercase
        return [w.lower().strip() for w in words if w.strip()]

    def should_ignore(self, text: str) -> bool:
        """Check if text contains only filler words.
        
        Args:
            text: The transcribed text to check.
            
        Returns:
            True if text contains only filler words (should be ignored),
            False otherwise.
        """
        if not text or not text.strip():
            return True  # Empty text should be ignored
        
        words = self._extract_words(text)
        if not words:
            return True  # No words found, ignore
        
        # Check if all words are in the ignore list
        return all(word in self._ignore_words for word in words)

    def contains_interruption_command(self, text: str) -> bool:
        """Check if text contains interruption commands.
        
        Args:
            text: The transcribed text to check.
            
        Returns:
            True if text contains any interruption command,
            False otherwise.
        """
        if not text or not text.strip():
            return False
        
        words = self._extract_words(text)
        if not words:
            return False
        
        # Check if any word matches an interruption command
        # Also check for multi-word commands like "never mind"
        normalized_text = self._normalize_text(text)
        for cmd in self._interruption_commands:
            if cmd in normalized_text:
                return True
        
        return False

    def should_interrupt(self, text: str, agent_is_speaking: bool) -> bool:
        """Main decision logic for whether to interrupt agent speech.
        
        Args:
            text: The transcribed user input.
            agent_is_speaking: Whether the agent is currently speaking.
            
        Returns:
            True if the agent should be interrupted,
            False if the input should be ignored.
        """
        if not agent_is_speaking:
            # When agent is NOT speaking, process all input normally
            return False  # Don't interrupt (there's nothing to interrupt)
        
        # When agent IS speaking:
        # 1. If text contains interruption commands, always interrupt
        if self.contains_interruption_command(text):
            return True
        
        # 2. If text contains only filler words, ignore (don't interrupt)
        if self.should_ignore(text):
            return False
        
        # 3. Otherwise, let normal interruption logic decide
        # (This will be handled by existing min_interruption_words/duration checks)
        return True
