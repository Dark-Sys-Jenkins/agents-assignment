"""
Interruption Filter - Core filtering logic for context-aware speech handling.

This module implements the logic to distinguish between:
1. Passive acknowledgements (backchannels) - should be ignored when agent is speaking
2. Active interruptions - should always interrupt the agent
3. Valid input when agent is silent - should be processed normally
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set

try:
    from .config import InterruptionFilterConfig, DEFAULT_CONFIG
except ImportError:
    from config import InterruptionFilterConfig, DEFAULT_CONFIG

logger = logging.getLogger("interruption-filter")


class FilterDecision(Enum):
    """The decision made by the interruption filter."""
    IGNORE = "ignore"           # Backchannel while speaking - ignore
    INTERRUPT = "interrupt"     # Active interruption command - stop agent
    PROCESS = "process"         # Valid input when silent - normal processing


@dataclass
class FilterResult:
    """Result of the filtering decision."""
    decision: FilterDecision
    reason: str
    transcript: str
    agent_speaking: bool
    detected_backchannels: list[str]
    detected_interruptions: list[str]


class InterruptionFilter:
    """
    Context-aware filter that determines whether user speech should interrupt the agent.
    
    The filter implements the following logic matrix:
    
    | User Input        | Agent State | Desired Behavior                          |
    |-------------------|-------------|-------------------------------------------|
    | "Yeah/Ok/Hmm"     | Speaking    | IGNORE - Continue speaking seamlessly    |
    | "Wait/Stop/No"    | Speaking    | INTERRUPT - Stop and listen              |
    | "Yeah/Ok/Hmm"     | Silent      | PROCESS - Treat as valid input           |
    | "Start/Hello"     | Silent      | PROCESS - Normal conversation            |
    | "Yeah but wait"   | Speaking    | INTERRUPT - Contains command word        |
    """
    
    def __init__(self, config: Optional[InterruptionFilterConfig] = None):
        """
        Initialize the interruption filter.
        
        Args:
            config: Configuration for word lists and behavior. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        # Normalize word lists based on case sensitivity
        if self.config.case_sensitive:
            self._backchannel_words = self.config.backchannel_words
            self._interruption_words = self.config.interruption_words
        else:
            self._backchannel_words = {w.lower() for w in self.config.backchannel_words}
            self._interruption_words = {w.lower() for w in self.config.interruption_words}
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not self.config.case_sensitive:
            text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove punctuation for better matching
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def _extract_words(self, text: str) -> list[str]:
        """Extract individual words from text."""
        return self._normalize_text(text).split()
    
    def _find_backchannels(self, text: str) -> list[str]:
        """Find all backchannel words/phrases in the text."""
        normalized = self._normalize_text(text)
        words = normalized.split()
        found = []
        
        # Check single words
        for word in words:
            if word in self._backchannel_words:
                found.append(word)
        
        # Check multi-word phrases
        for phrase in self._backchannel_words:
            if ' ' in phrase and phrase in normalized:
                found.append(phrase)
        
        return found
    
    def _find_interruptions(self, text: str) -> list[str]:
        """Find all interruption words/phrases in the text."""
        normalized = self._normalize_text(text)
        words = normalized.split()
        found = []
        
        # Check single words
        for word in words:
            if word in self._interruption_words:
                found.append(word)
        
        # Check multi-word phrases
        for phrase in self._interruption_words:
            if ' ' in phrase and phrase in normalized:
                found.append(phrase)
        
        return found
    
    def _is_pure_backchannel(self, text: str) -> bool:
        """
        Check if the text consists ONLY of backchannel words.
        
        Returns True only if every word in the text is a backchannel word.
        """
        words = self._extract_words(text)
        if not words:
            return False
        
        # Check if all words are backchannel words
        for word in words:
            is_backchannel = word in self._backchannel_words
            # Also check if word is part of a multi-word backchannel phrase
            if not is_backchannel:
                for phrase in self._backchannel_words:
                    if ' ' in phrase:
                        phrase_words = phrase.split()
                        if word in phrase_words:
                            is_backchannel = True
                            break
            
            if not is_backchannel:
                return False
        
        return True
    
    def filter(self, transcript: str, agent_speaking: bool) -> FilterResult:
        """
        Determine whether the transcript should interrupt the agent.
        
        Args:
            transcript: The transcribed user speech.
            agent_speaking: Whether the agent is currently speaking.
        
        Returns:
            FilterResult with the decision and reasoning.
        """
        if not transcript or not transcript.strip():
            return FilterResult(
                decision=FilterDecision.IGNORE,
                reason="Empty transcript",
                transcript=transcript,
                agent_speaking=agent_speaking,
                detected_backchannels=[],
                detected_interruptions=[]
            )
        
        detected_backchannels = self._find_backchannels(transcript)
        detected_interruptions = self._find_interruptions(transcript)
        
        # === CASE 1: Agent is NOT speaking ===
        if not agent_speaking:
            result = FilterResult(
                decision=FilterDecision.PROCESS,
                reason="Agent is silent - process all input normally",
                transcript=transcript,
                agent_speaking=agent_speaking,
                detected_backchannels=detected_backchannels,
                detected_interruptions=detected_interruptions
            )
            self._log_decision(result)
            return result
        
        # === CASE 2: Agent IS speaking ===
        
        # Check for interruption words first (they take priority)
        if detected_interruptions and self.config.allow_mixed_input_interruption:
            result = FilterResult(
                decision=FilterDecision.INTERRUPT,
                reason=f"Interruption word(s) detected: {detected_interruptions}",
                transcript=transcript,
                agent_speaking=agent_speaking,
                detected_backchannels=detected_backchannels,
                detected_interruptions=detected_interruptions
            )
            self._log_decision(result)
            return result
        
        # Check if it's a pure backchannel (only backchannel words)
        if self._is_pure_backchannel(transcript):
            result = FilterResult(
                decision=FilterDecision.IGNORE,
                reason=f"Pure backchannel detected: {detected_backchannels}",
                transcript=transcript,
                agent_speaking=agent_speaking,
                detected_backchannels=detected_backchannels,
                detected_interruptions=detected_interruptions
            )
            self._log_decision(result)
            return result
        
        # If we get here, it's not a pure backchannel and has no interruption words
        # This could be substantive content - treat as interruption
        result = FilterResult(
            decision=FilterDecision.INTERRUPT,
            reason="Substantive content detected (not pure backchannel)",
            transcript=transcript,
            agent_speaking=agent_speaking,
            detected_backchannels=detected_backchannels,
            detected_interruptions=detected_interruptions
        )
        self._log_decision(result)
        return result
    
    def _log_decision(self, result: FilterResult) -> None:
        """Log the filtering decision for debugging."""
        if self.config.debug_logging:
            agent_state = "SPEAKING" if result.agent_speaking else "SILENT"
            logger.info(
                f"[Filter] Agent:{agent_state} | Decision:{result.decision.value.upper()} | "
                f"Reason: {result.reason} | Transcript: '{result.transcript}'"
            )
    
    def add_backchannel_word(self, word: str) -> None:
        """Add a word to the backchannel list."""
        normalized = word.lower() if not self.config.case_sensitive else word
        self._backchannel_words.add(normalized)
        self.config.backchannel_words.add(word)
    
    def remove_backchannel_word(self, word: str) -> None:
        """Remove a word from the backchannel list."""
        normalized = word.lower() if not self.config.case_sensitive else word
        self._backchannel_words.discard(normalized)
        self.config.backchannel_words.discard(word)
    
    def add_interruption_word(self, word: str) -> None:
        """Add a word to the interruption list."""
        normalized = word.lower() if not self.config.case_sensitive else word
        self._interruption_words.add(normalized)
        self.config.interruption_words.add(word)
    
    def remove_interruption_word(self, word: str) -> None:
        """Remove a word from the interruption list."""
        normalized = word.lower() if not self.config.case_sensitive else word
        self._interruption_words.discard(normalized)
        self.config.interruption_words.discard(word)
