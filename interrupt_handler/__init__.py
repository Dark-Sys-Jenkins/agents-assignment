"""
Intelligent Interruption Handler for LiveKit Agents.

This module provides context-aware interruption handling that distinguishes
between passive acknowledgment (backchanneling) and active interruptions.

Usage:
    from interrupt_handler import InterruptionHandler, InterruptionConfig
    
    # Create handler with default config
    handler = InterruptionHandler()
    
    # Or with custom config
    config = InterruptionConfig(debug=True)
    handler = InterruptionHandler(config)
    
    # Use in your agent
    should_stop = handler.should_interrupt(
        transcript="yeah",
        is_final=True
    )
"""

from .config import InterruptionConfig, default_config
from .handler import InterruptionHandler
from .utils import (
    normalize_and_tokenize,
    classify_utterance,
    contains_any_word,
    contains_only_words,
    detect_phrase_match,
    format_transcript_for_display,
)

__version__ = '1.0.0'
__author__ = 'Your Name'

__all__ = [
    'InterruptionConfig',
    'InterruptionHandler',
    'default_config',
    'normalize_and_tokenize',
    'classify_utterance',
    'contains_any_word',
    'contains_only_words',
    'detect_phrase_match',
    'format_transcript_for_display',
]
