"""
Conext layer for the agent to TTS

- Passive acknowledgements (filler words: "yeah", "ok", "hmm")
- Active interruptions (commands: "wait", "stop", "no")

The filter operates at the logical layer within the agent's event loop,
NOT modifying VAD. It validates transcripts before interruption decisions.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class InterruptionType(Enum):
    """Classification of user input."""
    IGNORE = "ignore"  # Passive acknowledgement - agent continues
    INTERRUPT = "interrupt"  # Active command - agent stops immediately
    RESPOND = "respond"  # Valid input when agent is silent
    UNKNOWN = "unknown"  # Unclassified input


@dataclass
class FilterDecision:
    """Result of interruption filtering decision."""
    decision_type: InterruptionType
    transcript: str
    reason: str
    is_agent_speaking: bool
    matched_word: Optional[str] = None
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return (
            f"FilterDecision(type={self.decision_type.value}, "
            f"transcript='{self.transcript}', reason='{self.reason}', "
            f"agent_speaking={self.is_agent_speaking}, "
            f"matched_word={self.matched_word})"
        )


class ContextAwareInterruptionFilter:
    """
    Intelligently filters user input to prevent false interruptions.
    
    Key Features:
    1. Configurable ignore list for filler words
    2. State-based filtering (only active when agent is speaking/playing)
    3. Semantic analysis for mixed inputs (e.g., "Yeah wait a second")
    4. No VAD modification - pure logic layer implementation
    """
    
    # Default filler words that indicate passive listening
    DEFAULT_IGNORE_LIST = {
        "yeah", "yep", "yes", "ok", "okay", "alright", "right",
        "hmm", "uh", "uhh", "uh", "uhhhh", "um", "umm", "uh-huh", "uh huh",
        "mm", "mmm", "mm-hmm", "mmhmm", "huh", "huh?",
        "i see", "i understand", "got it", "sure", "cool",
        "no", "nope", "nah",  # Can be passive in some contexts
    }
    
    # Strong interrupt commands that override ignore list
    STRONG_INTERRUPT_WORDS = {
        "stop", "wait", "hold on", "hold up", "hold it", "pause",
        "no wait", "not wait", "but wait", "actually wait",
        "no stop", "stop stop", "shut up", "be quiet",
    }
    
    # Semantic markers indicating interruption intent
    INTERRUPT_CONJUNCTIONS = {
        "but", "however", "actually", "wait", "hold",
        "i need", "i want", "i have", "let me",
    }
    
    def __init__(
        self,
        ignore_list: Optional[set[str]] = None,
        min_interruption_words: int = 1,
        enable_logging: bool = True,
    ):
        """
        Initialize the interruption filter.
        
        Args:
            ignore_list: Custom set of words to treat as passive acknowledgements.
                        If None, uses DEFAULT_IGNORE_LIST.
            min_interruption_words: Minimum number of words to trigger interruption
                                   for non-strong-interrupt cases.
            enable_logging: Whether to log filtering decisions for debugging.
        """
        self.ignore_list = ignore_list or self.DEFAULT_IGNORE_LIST.copy()
        self.min_interruption_words = min_interruption_words
        self.enable_logging = enable_logging
        self._decision_history: list[FilterDecision] = []
        
        logger.info(
            f"InterruptionFilter initialized with {len(self.ignore_list)} "
            f"ignore words and min_interruption_words={min_interruption_words}"
        )
    
    def evaluate(
        self,
        transcript: str,
        is_agent_speaking: bool,
        is_agent_playing_audio: bool = False,
    ) -> FilterDecision:
        """
        Evaluate a user transcript and determine if it should interrupt the agent.
        
        Args:
            transcript: The user's spoken text (from STT)
            is_agent_speaking: Whether agent is currently generating text/LLM
            is_agent_playing_audio: Whether agent is currently playing audio
            
        Returns:
            FilterDecision with the interruption classification and reasoning.
        """
        # Normalize transcript for analysis
        normalized = self._normalize_text(transcript)
        
        # Empty transcript - ignore it
        if not normalized:
            decision = FilterDecision(
                decision_type=InterruptionType.IGNORE,
                transcript=transcript,
                reason="Empty transcript",
                is_agent_speaking=is_agent_speaking,
            )
            self._log_decision(decision)
            return decision
        
        # Agent is not active - this is valid input (not an interruption)
        if not is_agent_speaking and not is_agent_playing_audio:
            decision = FilterDecision(
                decision_type=InterruptionType.RESPOND,
                transcript=transcript,
                reason="Agent not speaking/playing - valid user input",
                is_agent_speaking=False,
            )
            self._log_decision(decision)
            return decision
        
        # Agent is active - apply context-aware filtering
        matched_word = self._find_matching_word(normalized)
        
        # Check for strong interruption commands (override ignore list)
        strong_interrupt = self._check_strong_interrupt(normalized)
        if strong_interrupt:
            decision = FilterDecision(
                decision_type=InterruptionType.INTERRUPT,
                transcript=transcript,
                reason=f"Strong interrupt command detected: '{strong_interrupt}'",
                is_agent_speaking=True,
                matched_word=strong_interrupt,
                confidence=1.0,
            )
            self._log_decision(decision)
            return decision
        
        # Check for pure filler words (only ignore list matches)
        if matched_word and not self._has_semantic_content(normalized):
            decision = FilterDecision(
                decision_type=InterruptionType.IGNORE,
                transcript=transcript,
                reason=f"Passive acknowledgement detected: '{matched_word}'",
                is_agent_speaking=True,
                matched_word=matched_word,
                confidence=0.95,
            )
            self._log_decision(decision)
            return decision
        
        # Check for mixed semantic input (e.g., "Yeah but wait")
        semantic_decision = self._check_semantic_interruption(normalized)
        if semantic_decision:
            decision = FilterDecision(
                decision_type=semantic_decision,
                transcript=transcript,
                reason=self._explain_semantic_decision(normalized, semantic_decision),
                is_agent_speaking=True,
                matched_word=matched_word,
                confidence=0.85,
            )
            self._log_decision(decision)
            return decision
        
        # Default: actual interruption (real user input while agent speaking)
        decision = FilterDecision(
            decision_type=InterruptionType.INTERRUPT,
            transcript=transcript,
            reason="User provided substantial input while agent speaking",
            is_agent_speaking=True,
            confidence=0.9,
        )
        self._log_decision(decision)
        return decision
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent analysis."""
        # Convert to lowercase, remove extra spaces, strip punctuation
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        # Remove trailing punctuation for matching
        normalized = re.sub(r'[.!?;:,]+$', '', normalized)
        return normalized
    
    def _find_matching_word(self, normalized: str) -> Optional[str]:
        """Find if normalized text contains a word from ignore list."""
        words = set(normalized.split())
        
        # Direct word match
        for word in words:
            if word in self.ignore_list:
                return word
        
        # Check for filler word prefixes/variants (uh, uhh, uhhhh, etc.)
        for word in words:
            if word.startswith('uh') and word != 'unhappy':
                return word
            if word.startswith('umm'):
                return word
            if word.startswith('hmm'):
                return word
            if word.startswith('mm'):
                return word
        
        # Common contractions/variants
        if "uh huh" in normalized or "uh-huh" in normalized:
            return "uh-huh"
        if "mm hmm" in normalized or "mmhmm" in normalized:
            return "mmhmm"
            
        return None
    
    def _check_strong_interrupt(self, normalized: str) -> Optional[str]:
        """Check for strong interrupt commands."""
        for command in self.STRONG_INTERRUPT_WORDS:
            if command in normalized:
                return command
        return None
    
    def _has_semantic_content(self, normalized: str) -> bool:
        """Check if text has semantic meaning beyond filler words."""
        # Text is too short - likely just a filler word
        if len(normalized.split()) <= 1:
            return False
        
        # Remove ignore words and filler patterns, see if meaningful content remains
        words = normalized.split()
        meaningful_words = []
        
        for w in words:
            # Skip if in ignore list
            if w in self.ignore_list:
                continue
            # Skip filler variants (uh, uhh, umm, hmm, mm variations)
            if w.startswith(('uh', 'um', 'hmm', 'mm')) and len(w) <= 5:
                continue
            # Skip short tokens
            if len(w) <= 2:
                continue
            # Skip numbers
            if w.isdigit():
                continue
            meaningful_words.append(w)
        
        # If we have meaningful words remaining, there's semantic content
        return len(meaningful_words) > 0
    
    def _check_semantic_interruption(self, normalized: str) -> Optional[InterruptionType]:
        """
        Detect semantic interruption patterns like "Yeah but wait" or
        "Yeah I have a question".
        
        Returns:
            InterruptionType.INTERRUPT if interruption intent detected, None otherwise.
        """
        # Check for conjunction patterns that indicate interruption
        for conjunction in self.INTERRUPT_CONJUNCTIONS:
            if conjunction in normalized:
                # Likely an interruption with semantic content
                return InterruptionType.INTERRUPT
        
        return None
    
    def _explain_semantic_decision(self, normalized: str, decision: InterruptionType) -> str:
        """Generate explanation for semantic-based decision."""
        if decision == InterruptionType.INTERRUPT:
            # Find which conjunction triggered it
            for conjunction in self.INTERRUPT_CONJUNCTIONS:
                if conjunction in normalized:
                    return f"Semantic interruption detected: contains '{conjunction}'"
        
        return "Semantic analysis triggered interruption"
    
    def _log_decision(self, decision: FilterDecision) -> None:
        """Log filtering decision for debugging and testing."""
        self._decision_history.append(decision)
        
        if self.enable_logging:
            logger.info(
                f"[INTERRUPT_FILTER] {decision.decision_type.value.upper()}: "
                f"'{decision.transcript}' | Reason: {decision.reason} | "
                f"Agent Speaking: {decision.is_agent_speaking}"
            )
    
    def get_decision_history(self) -> list[FilterDecision]:
        """Retrieve all filtering decisions made so far."""
        return self._decision_history.copy()
    
    def clear_history(self) -> None:
        """Clear decision history."""
        self._decision_history.clear()
    
    def update_ignore_list(self, words: set[str]) -> None:
        """
        Update the ignore list dynamically.
        
        Args:
            words: New set of words to treat as passive acknowledgements.
        """
        self.ignore_list = words.copy()
        logger.info(f"Ignore list updated to {len(words)} words")
    
    def add_to_ignore_list(self, words: set[str] | list[str]) -> None:
        """Add words to the ignore list."""
        if isinstance(words, list):
            words = set(words)
        self.ignore_list.update(words)
        logger.info(f"Added {len(words)} words to ignore list")
    
    def remove_from_ignore_list(self, words: set[str] | list[str]) -> None:
        """Remove words from the ignore list."""
        if isinstance(words, list):
            words = set(words)
        self.ignore_list.difference_update(words)
        logger.info(f"Removed {len(words)} words from ignore list")
