"""
Configuration for intelligent interruption handling.
"""

from typing import FrozenSet
from dataclasses import dataclass


@dataclass
class InterruptionConfig:
    """Configuration for interruption handling logic."""
    
    # Words that should be ignored when agent is speaking (backchanneling)
    backchanneling_words: FrozenSet[str] = frozenset({
        'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 
        'aha', 'mhm', 'yep', 'sure', 'alright', 'got it',
        'i see', 'uh', 'um', 'mm', 'mmhmm', 'mhmm'
    })
    
    # Words that always trigger interruption
    interrupt_words: FrozenSet[str] = frozenset({
        'stop', 'wait', 'no', 'hold', 'pause', 'hang on',
        'hold on', 'interrupt', 'cancel', 'nevermind', 'never mind'
    })
    
    # Enable/disable the intelligent interruption handling
    enabled: bool = True


# Default configuration instance
DEFAULT_CONFIG = InterruptionConfig()