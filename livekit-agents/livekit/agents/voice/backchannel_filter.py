"""
Backchannel Filter for Intelligent Interruption Handling.

This module provides O(1) classification of user transcripts to distinguish
between backchannels (acknowledgements like "yeah", "ok") and real interruptions
(commands like "stop", "wait", or meaningful speech).

The filter is used by agent_activity.py to prevent the agent from stopping
when users provide passive acknowledgements during agent speech.

Configuration:
    Environment Variables:
        BACKCHANNEL_IGNORE_WORDS: Comma-separated list of words to ignore
        BACKCHANNEL_INTERRUPT_WORDS: Comma-separated list of interrupt words
        BACKCHANNEL_DEBUG: Enable debug logging (true/false)

Usage:
    from livekit.agents.voice.backchannel_filter import should_ignore, classify
    
    # Check if transcript should be ignored when agent is speaking
    if should_ignore("yeah", agent_speaking=True):
        return  # Don't interrupt
    
    # Get classification
    result = classify("stop talking")  # Returns "interrupt"

Author: Aswani Sahoo
Assignment: LiveKit Intelligent Interruption Handling Challenge
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Set

logger = logging.getLogger("backchannel_filter")


@dataclass
class BackchannelConfig:
    """
    Configuration for backchannel detection.
    
    Supports loading from environment variables for deployment flexibility.
    
    Attributes:
        ignore_words: Words to ignore when agent is speaking (backchannels)
        interrupt_words: Words that always trigger interruption
        debug_mode: Enable verbose logging for debugging
    """
    
    ignore_words: Set[str] = field(default_factory=lambda: {
        # Affirmative backchannels
        "yeah", "yep", "yes", "yea", "ya", "yup",
        "ok", "okay", "k", "okey",
        "sure", "alright", "right", "all right",
        "got it", "i see", "i understand",
        "go on", "continue", "go ahead",
        "cool", "nice", "great", "good", "fine",
        # Acknowledgement sounds
        "hmm", "hm", "mm", "mhm", "mmhmm", "mhmm",
        "uh-huh", "uh huh", "uhuh", "aha", "a-ha",
        # Filler sounds
        "uh", "um", "er", "eh", "ah", "oh", "ooh",
        # Short confirmations
        "true", "correct", "exactly", "indeed",
    })
    
    interrupt_words: Set[str] = field(default_factory=lambda: {
        # Stop commands
        "stop", "wait", "hold", "pause", "enough", "quiet",
        # Negation (indicates disagreement)
        "no", "nope", "nah", "wrong", "incorrect",
        # Conjunctions that signal more meaningful content
        "but", "however", "actually", "although",
        # Attention words
        "hey", "listen", "excuse me", "sorry",
        # Questions (user wants to interject)
        "what", "why", "how", "when", "where", "who",
    })
    
    debug_mode: bool = False
    
    @classmethod
    def from_env(cls) -> "BackchannelConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        if env_ignore := os.getenv("BACKCHANNEL_IGNORE_WORDS"):
            config.ignore_words = {
                w.strip().lower() for w in env_ignore.split(",") if w.strip()
            }
        
        if env_interrupt := os.getenv("BACKCHANNEL_INTERRUPT_WORDS"):
            config.interrupt_words = {
                w.strip().lower() for w in env_interrupt.split(",") if w.strip()
            }
        
        config.debug_mode = os.getenv("BACKCHANNEL_DEBUG", "").lower() in ("true", "1", "yes")
        
        return config
    
    def add_ignore_word(self, word: str) -> None:
        """Add a word to the ignore (backchannel) list."""
        self.ignore_words.add(word.lower().strip())
    
    def add_interrupt_word(self, word: str) -> None:
        """Add a word to the interrupt list."""
        self.interrupt_words.add(word.lower().strip())


# Global config instance (lazy initialization)
_config: BackchannelConfig | None = None


def get_config() -> BackchannelConfig:
    """Get or create the global config from environment variables."""
    global _config
    if _config is None:
        _config = BackchannelConfig.from_env()
    return _config


def set_config(config: BackchannelConfig) -> None:
    """Set custom configuration."""
    global _config
    _config = config


def _tokenize(text: str) -> list[str]:
    """
    Fast tokenization with O(n) complexity.
    
    Returns lowercase words, preserving hyphens for words like "uh-huh".
    
    Args:
        text: Input text to tokenize
        
    Returns:
        List of lowercase word tokens
    """
    result = []
    current_word = []
    
    for char in text.lower():
        if char.isalpha() or char == '-':
            current_word.append(char)
        elif current_word:
            result.append(''.join(current_word))
            current_word = []
    
    if current_word:
        result.append(''.join(current_word))
    
    return result


def classify(text: str) -> Literal["ignore", "interrupt"]:
    """
    Classify transcript as backchannel (ignore) or real content (interrupt).
    
    Decision Logic:
        1. If ANY interrupt word is present -> "interrupt" (semantic interruption)
        2. If ALL words are ignore words -> "ignore" (pure backchannel)
        3. Otherwise -> "interrupt" (unknown content = treat as real input)
    
    Performance: O(n) tokenization + O(w) set lookups where w = word count
    
    Args:
        text: User transcript to classify
        
    Returns:
        "ignore" - Backchannel, should be ignored when agent speaking
        "interrupt" - Real content, should interrupt agent
    """
    config = get_config()
    start_time = time.perf_counter()
    
    words = _tokenize(text)
    
    if not words:
        return "ignore"
    
    # Priority 1: Check for interrupt words (semantic interruption)
    for word in words:
        if word in config.interrupt_words:
            if config.debug_mode:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"INTERRUPT '{text}' (word='{word}', {elapsed_ms:.2f}ms)")
            return "interrupt"
    
    # Priority 2: Check if ALL words are backchannel
    for word in words:
        if word not in config.ignore_words:
            if config.debug_mode:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"INTERRUPT '{text}' (unknown word='{word}', {elapsed_ms:.2f}ms)")
            return "interrupt"
    
    if config.debug_mode:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"IGNORE '{text}' (pure backchannel, {elapsed_ms:.2f}ms)")
    
    return "ignore"


def should_ignore(text: str, *, agent_speaking: bool) -> bool:
    """
    Main API: Determine if transcript should be ignored.
    
    This is the primary function used by agent_activity.py for
    intelligent interruption handling.
    
    Args:
        text: User transcript
        agent_speaking: True if agent is currently speaking/generating
        
    Returns:
        True if transcript should be ignored (backchannel while speaking)
        False if transcript should be processed
    """
    if not agent_speaking:
        return False  # Always process when agent is silent
    
    return classify(text) == "ignore"
