"""
Context-Aware Voice Agent Package

This package provides a voice agent with intelligent backchannel handling
that prevents false interruptions from acknowledgement words like "yeah",
"ok", and "hmm" while the agent is speaking.
"""

from .config import InterruptionFilterConfig, BACKCHANNEL_WORDS, INTERRUPTION_WORDS
from .interruption_filter import InterruptionFilter, FilterDecision, FilterResult

__all__ = [
    "InterruptionFilterConfig",
    "InterruptionFilter",
    "FilterDecision",
    "FilterResult",
    "BACKCHANNEL_WORDS",
    "INTERRUPTION_WORDS",
]
