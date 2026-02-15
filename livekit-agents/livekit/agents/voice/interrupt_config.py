"""
Configuration for intelligent interruption handling.
Defines which words should be ignored (backchanneling) vs interrupt (commands).
"""

import os
from typing import Set

# Words to ignore when agent is speaking (backchanneling / passive acknowledgment)
DEFAULT_IGNORE_WORDS: Set[str] = {
    # Basic acknowledgments
    "yeah", "yep", "yup", "yes",
    
    # Agreement
    "ok", "okay", "alright", "right", "sure", "fine",
    
    # Positive feedback (ADDED)
    "good", "great", "nice", "cool", "awesome", "perfect",
    "excellent", "wonderful", "fantastic", "amazing",
    
    # Understanding
    "exactly", "absolutely", "definitely", "indeed", "totally",
    "correct", "true",
    
    # Listening signals
    "hmm", "mhmm", "mmhmm", "uh-huh", "ah", "oh", "aha",
    
    # Continuation
    "gotcha", "got it", "i see", "understood",
    "continue", "go on", "go ahead", "keep going",
}

# Words that always trigger interruption (commands)
DEFAULT_COMMAND_WORDS: Set[str] = {
    "wait",
    "stop",
    "no",
    "pause",
    "hold",
}

# Load from environment variables if provided
def get_ignore_words() -> Set[str]:
    """Get ignore words from environment or use defaults."""
    env_words = os.getenv("IGNORE_WORDS")
    if env_words:
        return {w.strip().lower() for w in env_words.split(",")}
    return DEFAULT_IGNORE_WORDS.copy()


def get_command_words() -> Set[str]:
    """Get command words from environment or use defaults."""
    env_words = os.getenv("COMMAND_WORDS")
    if env_words:
        return {w.strip().lower() for w in env_words.split(",")}
    return DEFAULT_COMMAND_WORDS.copy()


# Exported constants
IGNORE_WORDS = get_ignore_words()
COMMAND_WORDS = get_command_words()