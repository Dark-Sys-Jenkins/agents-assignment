"""
Filler Detection Module

Context-aware filler word filtering for voice agents.
Distinguishes between soft acknowledgments and commands.
"""

from .filter import InterruptionFilter

__all__ = [
    "InterruptionFilter",
]
