"""
Configuration module for interruption handling.

Defines default word sets and provides environment variable support
for customizing backchannel and interrupt words.
"""

import os
from typing import Set

# Default soft ignore words - backchanneling patterns
# These are passive acknowledgments that should NOT interrupt agent speech
DEFAULT_SOFT_IGNORE: Set[str] = {
    "yeah",
    "ok",
    "okay",
    "hmm",
    "uh-huh",
    "right",
    "aha",
    "mhm",
    "sure",
    "gotcha",
    "yep",
    "yup",
    "mhmm",
    "uh huh",
    "mm-hmm",
    "alright",
    "cool",
    "nice",
    "yes",
    "oh",  # Added for backchannel acknowledgment
}

# Default hard interrupt words - active interruption commands
# These should ALWAYS trigger immediate agent interruption
DEFAULT_HARD_INTERRUPT: Set[str] = {
    "stop",
    "wait",
    "pause",
    "no",
    "hold",
    "hold on",
    "wait a second",
    "wait a minute",
    "but wait",
    "hang on",
    "actually",
    "but",
    "however",
    "excuse me",
}


def load_config() -> tuple[Set[str], Set[str]]:
    """
    Load configuration from environment variables.

    Environment Variables:
        LIVEKIT_SOFT_IGNORE_WORDS: Comma-separated list of words to ignore
        LIVEKIT_HARD_INTERRUPT_WORDS: Comma-separated list of interrupt words

    Returns:
        tuple: (soft_ignore_words, hard_interrupt_words)
    """
    soft_ignore = DEFAULT_SOFT_IGNORE.copy()
    hard_interrupt = DEFAULT_HARD_INTERRUPT.copy()

    # Override with environment variables if present
    if env_soft := os.getenv("LIVEKIT_SOFT_IGNORE_WORDS"):
        soft_ignore = {w.strip().lower() for w in env_soft.split(",") if w.strip()}

    if env_hard := os.getenv("LIVEKIT_HARD_INTERRUPT_WORDS"):
        hard_interrupt = {
            w.strip().lower() for w in env_hard.split(",") if w.strip()
        }

    return soft_ignore, hard_interrupt
