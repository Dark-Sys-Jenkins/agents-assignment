"""
Interruption Filter for Voice Agents

Distinguishes between backchanneling ("yeah", "ok") and real interruptions ("wait", "stop").
When the agent is speaking, filler words are ignored. When silent, all input triggers a response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Filler words to ignore when agent is speaking
IGNORE_WORDS = [
    "yeah", "yes", "yep", "yup", "ok", "okay", "hmm", "mhm", "uh-huh",
    "mm-hmm", "right", "sure", "alright", "ah", "oh", "i see", "got it",
]

# Words that always trigger interruption
INTERRUPT_WORDS = [
    "wait", "stop", "no", "hold on", "pause", "actually", "but",
    "excuse me", "question", "help", "repeat", "cancel", "skip",
]


@dataclass
class InterruptionFilterConfig:
    """Config for the interruption filter."""
    ignore_words: list[str] = field(default_factory=lambda: IGNORE_WORDS.copy())
    interrupt_words: list[str] = field(default_factory=lambda: INTERRUPT_WORDS.copy())
    enabled: bool = True


class InterruptionFilter:
    """
    Filters user speech to decide if it should interrupt the agent.
    
    Example:
        filter = InterruptionFilter()
        
        # User says "yeah" while agent talks -> ignored
        filter.should_interrupt("yeah", agent_speaking=True)  # False
        
        # User says "wait" while agent talks -> interrupt
        filter.should_interrupt("wait", agent_speaking=True)  # True
        
        # User says anything while agent is silent -> respond
        filter.should_interrupt("yeah", agent_speaking=False)  # True
    """
    
    def __init__(self, config: InterruptionFilterConfig | None = None):
        self.config = config or InterruptionFilterConfig()
        self._ignore_pattern = self._make_pattern(self.config.ignore_words)
        self._interrupt_pattern = self._make_pattern(self.config.interrupt_words)
    
    def _make_pattern(self, words: list[str]) -> re.Pattern | None:
        if not words:
            return None
        escaped = [re.escape(w) for w in words]
        return re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)
    
    def _has_interrupt_word(self, text: str) -> bool:
        if not self._interrupt_pattern:
            return False
        return bool(self._interrupt_pattern.search(text))
    
    def _is_only_filler(self, text: str) -> bool:
        if not self._ignore_pattern:
            return False
        # Remove filler words and punctuation, check if anything remains
        remaining = self._ignore_pattern.sub('', text.lower())
        remaining = re.sub(r'[^\w\s]', '', remaining).strip()
        return len(remaining) == 0
    
    def should_interrupt(self, transcript: str, agent_speaking: bool = False) -> bool:
        """
        Check if transcript should interrupt the agent.
        
        Args:
            transcript: What the user said
            agent_speaking: True if agent is currently speaking
            
        Returns:
            True if agent should stop and respond, False if should continue
        """
        if not self.config.enabled:
            return True  # Filter disabled, always interrupt
        
        transcript = transcript.strip()
        if not transcript:
            return False
        
        # Interrupt words always trigger interruption
        if self._has_interrupt_word(transcript):
            return True
        
        # If agent is silent, respond to any input
        if not agent_speaking:
            return True
        
        # Agent is speaking - ignore if it's just filler words
        if self._is_only_filler(transcript):
            return False
        
        # Substantive input while speaking - interrupt
        return True
