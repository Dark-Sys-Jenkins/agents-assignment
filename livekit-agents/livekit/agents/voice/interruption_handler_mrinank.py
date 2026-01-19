"""
Context-aware Interruption Handler for LiveKit Agents.

This module implements intelligent filtering for backchannel utterances (filler words like
"yeah", "ok", "hmm") to distinguish between:
- Passive acknowledgements: User says "yeah" while agent is SILENT -> respond
- Active interruptions: User says "yeah" while agent is SPEAKING -> ignore

The handler is context-aware and only filters when the agent is actively generating or
playing audio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class InterruptionHandlerConfig:
    """Configuration for the interruption handler."""
    
    # Filler words that act as "soft inputs" - only ignored when agent is speaking
    ignore_list: list[str] = field(
        default_factory=lambda: ["yeah", "ok", "okay", "hmm", "right", "uh-huh", "huh", "uh"]
    )
    
    # Enable/disable the interruption handler
    enabled: bool = True
    
    # Minimum number of words to consider as interruption
    # (if text has more words than ignore list, it's always an interrupt)
    min_interrupt_words: int = 1
    
    # Log details for debugging
    verbose_logging: bool = False


class InterruptionHandler:
    """
    Handles context-aware interruption logic for the agent.
    
    This handler distinguishes between:
    1. Passive acknowledgements (user says "yeah" while agent is silent)
    2. Active interruptions (user says "yeah" while agent is speaking)
    3. Semantic interruptions (user says "yeah wait a second" - contains command words)
    """
    
    def __init__(self, config: InterruptionHandlerConfig | None = None):
        """Initialize the interruption handler."""
        self._config = config or InterruptionHandlerConfig()
        self._normalize_ignore_list()
    
    def _normalize_ignore_list(self) -> None:
        """Normalize ignore list to lowercase for case-insensitive matching."""
        self._ignore_list_lower = {word.lower().strip() for word in self._config.ignore_list}
        if self._config.verbose_logging:
            logger.info(f"Initialized ignore list: {self._ignore_list_lower}")
    
    def should_ignore_interrupt(
        self, 
        transcript: str, 
        agent_is_speaking: bool,
        current_agent_state: str | None = None
    ) -> bool:
        """
        Determine if an interrupt should be ignored based on context.
        
        Args:
            transcript: The user's transcribed text
            agent_is_speaking: Whether the agent is currently speaking/generating audio
            current_agent_state: The agent's current state (e.g., "speaking", "listening")
        
        Returns:
            True if the interrupt should be ignored, False if it should trigger
        """
        if not self._config.enabled or not transcript:
            return False
        
        # Extract words from transcript
        words = self._extract_words(transcript)
        
        if self._config.verbose_logging:
            logger.info(
                f"Interrupt check: transcript='{transcript}', agent_speaking={agent_is_speaking}, "
                f"words={words}, agent_state={current_agent_state}"
            )
        
        # Rule 1: If the transcript contains non-filler words, it's always an interrupt
        has_non_filler_words = self._has_non_filler_words(words)
        
        if has_non_filler_words:
            if self._config.verbose_logging:
                logger.info(f"Contains non-filler words: {words} -> INTERRUPT")
            return False  # Always interrupt if non-filler words present
        
        # Rule 2: If only filler words, only ignore if agent is actively speaking
        if not words:  # Empty transcript after word extraction
            return False  # Empty text should not cause ignore
        
        # All words are in ignore list
        if agent_is_speaking:
            if self._config.verbose_logging:
                logger.info(f"Agent is speaking and all words are filler -> IGNORE")
            return True  # Ignore backchannel while agent is speaking
        else:
            if self._config.verbose_logging:
                logger.info(f"Agent is NOT speaking but all words are filler -> RESPOND (passive ack)")
            return False  # Don't ignore - agent should respond to passive affirmation
    
    def _extract_words(self, text: str) -> list[str]:
        """Extract and normalize words from text."""
        # Simple word extraction - split by whitespace and punctuation
        import re
        # Split on whitespace and common punctuation
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _has_non_filler_words(self, words: list[str]) -> bool:
        """Check if the word list contains any non-filler words."""
        for word in words:
            if word not in self._ignore_list_lower:
                return True
        return False
    
    def get_interrupt_reason(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> str:
        """Get a human-readable reason for the interrupt decision."""
        words = self._extract_words(transcript)
        
        if not words:
            return "empty_transcript"
        
        if self._has_non_filler_words(words):
            return "contains_semantic_content"
        
        if agent_is_speaking:
            return "passive_acknowledgement_ignored_agent_speaking"
        else:
            return "passive_acknowledgement_agent_silent"
    
    def update_ignore_list(self, new_ignore_list: list[str]) -> None:
        """Update the ignore list at runtime."""
        self._config.ignore_list = new_ignore_list
        self._normalize_ignore_list()
        logger.info(f"Updated ignore list to: {self._ignore_list_lower}")


# Global instance for easy access
_default_handler: InterruptionHandler | None = None


def get_default_handler() -> InterruptionHandler:
    """Get or create the default interruption handler instance."""
    global _default_handler
    if _default_handler is None:
        _default_handler = InterruptionHandler()
    return _default_handler


def set_default_handler(handler: InterruptionHandler) -> None:
    """Set the default interruption handler instance."""
    global _default_handler
    _default_handler = handler
