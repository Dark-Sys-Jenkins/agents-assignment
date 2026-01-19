"""
Smart Interruption Module

Intelligent interruption handling for LiveKit voice agents.

This module provides SmartInterruptionHandler, which enables context-aware
interruption detection for voice conversations. It distinguishes between
passive acknowledgments (like "yeah", "uh-huh") and command interruptions
(like "stop", "wait") to create more natural voice interactions.

Key Components:
    - SmartInterruptionHandler: Main handler for processing interruptions
    - InterruptionConfig: Configuration for passive/command words and phrases
    - InterruptionDecision: Decision output with reasoning and confidence
    - TranscriptAnalysis: Detailed analysis of user speech patterns
"""

# Configuration exports
from .config import (
    InterruptionConfig,
    DEFAULT_PASSIVE_WORDS,
    DEFAULT_COMMAND_WORDS,
    DEFAULT_PASSIVE_PHRASES,
    DEFAULT_COMMAND_PHRASES,
)

# Handler exports
from .handler import (
    SmartInterruptionHandler,
    InterruptionDecision,
    InterruptionEvent,
    TranscriptAnalysis,
)

__all__ = [
    # Config
    "InterruptionConfig",
    "DEFAULT_PASSIVE_WORDS",
    "DEFAULT_COMMAND_WORDS",
    "DEFAULT_PASSIVE_PHRASES",
    "DEFAULT_COMMAND_PHRASES",
    # Handler
    "SmartInterruptionHandler",
    "InterruptionDecision",
    "InterruptionEvent",
    "TranscriptAnalysis",
]

__version__: str = "1.0.0"
