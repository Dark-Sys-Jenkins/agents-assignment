"""
Configuration for the Context-Aware Interruption Filter.

This module contains all configurable word lists and settings for the
backchannel detection system.
"""

from dataclasses import dataclass, field
from typing import Set

# ============================================================================
# BACKCHANNEL WORDS (Passive Acknowledgements)
# These words should be IGNORED when the agent is speaking
# ============================================================================
BACKCHANNEL_WORDS: Set[str] = {
    # Common acknowledgements
    "yeah",
    "yep",
    "yes",
    "yup",
    "ya",
    "yah",
    
    # Affirmations
    "ok",
    "okay",
    "k",
    "alright",
    "right",
    "sure",
    "fine",
    
    # Listening indicators
    "hmm",
    "hm",
    "mm",
    "mmm",
    "mhm",
    "mm-hmm",
    "mmhmm",
    "uh-huh",
    "uhuh",
    "uhhuh",
    "uh-huh",
    "uhuh",
    "uh huh",
    "ah",
    "aha",
    "ah-ha",
    
    # Understanding indicators
    "i see",
    "got it",
    "gotcha",
    "understood",
    
    # Continuers
    "go on",
    "continue",
    "and",
    "so",
    "then",
}

# ============================================================================
# INTERRUPTION WORDS (Active Commands)
# These words should ALWAYS trigger an interruption, even if mixed with backchannels
# ============================================================================
INTERRUPTION_WORDS: Set[str] = {
    # Stop commands
    "wait",
    "stop",
    "hold",
    "hold on",
    "pause",
    "one moment",
    "one second",
    "hang on",
    
    # Negations
    "no",
    "nope",
    "not",
    "don't",
    "dont",
    
    # Corrections
    "actually",
    "but",
    "however",
    "except",
    "instead",
    
    # Questions (user wants to interject)
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    
    # Attention getters
    "hey",
    "excuse me",
    "sorry",
    "pardon",
    
    # Clarification requests
    "repeat",
    "again",
    "slower",
    "louder",
}


@dataclass
class InterruptionFilterConfig:
    """Configuration for the interruption filter behavior."""
    
    # Word lists (can be customized)
    backchannel_words: Set[str] = field(default_factory=lambda: BACKCHANNEL_WORDS.copy())
    interruption_words: Set[str] = field(default_factory=lambda: INTERRUPTION_WORDS.copy())
    
    # Filtering behavior
    case_sensitive: bool = False
    """Whether word matching should be case-sensitive."""
    
    filter_when_speaking: bool = True
    """Whether to filter backchannels when agent is speaking."""
    
    allow_mixed_input_interruption: bool = True
    """Whether mixed inputs like 'yeah but wait' should interrupt."""
    
    # Logging
    debug_logging: bool = True
    """Whether to log filtering decisions for debugging."""


# Default configuration instance
DEFAULT_CONFIG = InterruptionFilterConfig()
