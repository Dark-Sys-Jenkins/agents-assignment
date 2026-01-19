"""
Smart Interruption Configuration

Configurable lists of passive and command words for intelligent interruption handling.
"""

import os
from typing import Set


# Passive words that should be ignored while agent is speaking
# but processed when agent is silent
DEFAULT_PASSIVE_WORDS: Set[str] = {
    "yeah", "yes", "yep", "yup", "okay", "ok", "alright",
    "uhuh", "mhm", "mmhm", "mhmm", "hmm",
    "right", "sure", "gotcha",
    "understood",
    "cool", "nice", "great", "perfect", "good",
    "fine", "agreed", "indeed", "absolutely",
    "correct", "exactly", "definitely", "certainly"
}

# Command words that should always interrupt the agent
DEFAULT_COMMAND_WORDS: Set[str] = {
    "stop", "wait", "hold on", "hold up", "hang on",
    "pause", "no", "nope", "actually", "but",
    "however", "cancel", "interrupt", "excuse me",
    "sorry", "pardon", "one moment", "one second",
    "just a second", "let me", "can you", "could you",
    "would you", "please", "listen", "hey",
    "excuse", "question"
}

# Additional passive phrases (multi-word)
DEFAULT_PASSIVE_PHRASES: Set[str] = {
    "i see", "got it", "makes sense", "mm-hmm", "uh-huh"
}

# Command phrases (multi-word) that should always interrupt
DEFAULT_COMMAND_PHRASES: Set[str] = {
    "hold on", "hold up", "hang on", "one moment", "one second",
    "just a second", "excuse me", "let me", "can you", "could you",
    "would you"
}


class InterruptionConfig:
    """Configuration for smart interruption handling."""
    
    def __init__(
        self,
        passive_words: Set[str] | None = None,
        command_words: Set[str] | None = None,
        passive_phrases: Set[str] | None = None,
        command_phrases: Set[str] | None = None
    ):
        """
        Initialize interruption configuration.
        
        Args:
            passive_words: Set of words to ignore while agent is speaking
            command_words: Set of words that always trigger interruption
            passive_phrases: Set of multi-word phrases to ignore while speaking
            command_phrases: Set of multi-word phrases that always trigger interruption
        """
        self.passive_words = passive_words or DEFAULT_PASSIVE_WORDS.copy()
        self.command_words = command_words or DEFAULT_COMMAND_WORDS.copy()
        self.passive_phrases = passive_phrases or DEFAULT_PASSIVE_PHRASES.copy()
        self.command_phrases = command_phrases or DEFAULT_COMMAND_PHRASES.copy()
    
    def add_passive_word(self, word: str) -> None:
        """Add a passive word to the ignore list."""
        self.passive_words.add(word.lower())
    
    def add_command_word(self, word: str) -> None:
        """Add a command word to the interrupt list."""
        self.command_words.add(word.lower())
    
    def remove_passive_word(self, word: str) -> None:
        """Remove a passive word from the ignore list."""
        self.passive_words.discard(word.lower())
    
    def remove_command_word(self, word: str) -> None:
        """Remove a command word from the interrupt list."""
        self.command_words.discard(word.lower())
    
    @classmethod
    def from_env(cls) -> "InterruptionConfig":
        """
        Create configuration from environment variables.
        
        Environment variables:
            SMART_INTERRUPT_PASSIVE_WORDS: Comma-separated list of passive words
            SMART_INTERRUPT_COMMAND_WORDS: Comma-separated list of command words
            SMART_INTERRUPT_PASSIVE_PHRASES: Comma-separated list of passive phrases
            SMART_INTERRUPT_COMMAND_PHRASES: Comma-separated list of command phrases
        """
        passive_words = DEFAULT_PASSIVE_WORDS.copy()
        command_words = DEFAULT_COMMAND_WORDS.copy()
        passive_phrases = DEFAULT_PASSIVE_PHRASES.copy()
        command_phrases = DEFAULT_COMMAND_PHRASES.copy()
        
        # Load from environment
        if env_passive := os.getenv("SMART_INTERRUPT_PASSIVE_WORDS"):
            passive_words.update(word.strip().lower() for word in env_passive.split(","))
        
        if env_command := os.getenv("SMART_INTERRUPT_COMMAND_WORDS"):
            command_words.update(word.strip().lower() for word in env_command.split(","))
        
        if env_passive_phrases := os.getenv("SMART_INTERRUPT_PASSIVE_PHRASES"):
            passive_phrases.update(phrase.strip().lower() for phrase in env_passive_phrases.split(","))
        
        if env_command_phrases := os.getenv("SMART_INTERRUPT_COMMAND_PHRASES"):
            command_phrases.update(phrase.strip().lower() for phrase in env_command_phrases.split(","))
        
        return cls(
            passive_words=passive_words,
            command_words=command_words,
            passive_phrases=passive_phrases,
            command_phrases=command_phrases
        )
