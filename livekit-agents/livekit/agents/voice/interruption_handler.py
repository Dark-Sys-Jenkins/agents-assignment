"""
Intelligent Interruption Handler for LiveKit Voice Agents

This module provides context-aware interruption handling that distinguishes between:
- Backchanneling (passive acknowledgements like "yeah", "ok", "hmm")
- Active interruptions (commands like "wait", "stop", "no")

The handler makes decisions based on whether the agent is currently speaking or silent.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class InterruptionConfig:
    """
    Configuration for the intelligent interruption handler.
    
    Attributes:
        ignore_words: List of words to ignore when agent is speaking (backchanneling)
        interrupt_words: List of words that always trigger interruption
        case_sensitive: Whether word matching should be case-sensitive
    """
    ignore_words: List[str] = field(default_factory=lambda: [
        # Common acknowledgements
        "yeah", "ok", "okay", "hmm", "mhm", "uh-huh", "mm-hmm", "right",
        "aha", "sure", "yep", "yup", "gotcha", "alright",
        # Thinking sounds
        "mmm", "uh", "um", "er", "ah",
        # Affirmative responses
        "yes", "nice", "cool", "great", "good",
    ])
    
    interrupt_words: List[str] = field(default_factory=lambda: [
        # Stop commands
        "wait", "stop", "no", "hold on", "hold up", "hang on",
        # Cancel commands
        "pause", "cancel", "never mind", "nevermind",
        # Correction commands
        "actually", "but", "however", "though",
    ])
    
    case_sensitive: bool = False


@dataclass
class InterruptionDecision:
    """
    Result of an interruption decision.
    
    Attributes:
        should_interrupt: Whether the agent should be interrupted
        reason: Human-readable explanation of the decision
        matched_ignore_words: List of ignore words found in the input
        matched_interrupt_words: List of interrupt words found in the input
        is_pure_backchanneling: Whether input contains only ignore words
    """
    should_interrupt: bool
    reason: str
    matched_ignore_words: List[str] = field(default_factory=list)
    matched_interrupt_words: List[str] = field(default_factory=list)
    is_pure_backchanneling: bool = False
    
    @property
    def matched_words(self) -> List[str]:
        """
        Combined list of all matched words (for backwards compatibility).
        Returns ignore words + interrupt words.
        """
        return self.matched_ignore_words + self.matched_interrupt_words


class IntelligentInterruptionHandler:
    """
    Intelligent interruption handler that analyzes user input and agent state
    to determine whether to interrupt the agent's speech.
    
    Decision Logic:
    - If agent is NOT speaking: Always process input (return should_interrupt=True)
    - If agent IS speaking:
        - If input contains interrupt words → INTERRUPT
        - If input contains ONLY ignore words → IGNORE (continue speaking)
        - Otherwise → INTERRUPT (mixed content or normal speech)
    """
    
    def __init__(
        self,
        config: Optional[InterruptionConfig] = None,
        enabled: bool = True,
    ):
        """
        Initialize the interruption handler.
        
        Args:
            config: Configuration object with word lists
            enabled: Whether the handler is enabled (can be toggled at runtime)
        """
        self.config = config or InterruptionConfig()
        self.enabled = enabled
        
        # Pre-compile regex patterns for performance
        self._compile_patterns()
        
        # Convert to sets for O(1) lookup
        self._ignore_set = self._normalize_words(self.config.ignore_words)
        self._interrupt_set = self._normalize_words(self.config.interrupt_words)
        
        logger.info(
            f"Interruption handler initialized: "
            f"{len(self._ignore_set)} ignore words, "
            f"{len(self._interrupt_set)} interrupt words, "
            f"enabled={enabled}"
        )
    
    def _normalize_words(self, words: List[str]) -> Set[str]:
        """Convert word list to normalized set."""
        if self.config.case_sensitive:
            return set(words)
        return set(w.lower() for w in words)
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficient text processing."""
        # Pattern to extract words (handles hyphenated words and apostrophes)
        self._word_pattern = re.compile(r'\b[\w\'-]+\b')
    
    def _extract_words(self, text: str) -> List[str]:
        """
        Extract individual words from text, normalizing for comparison.
        Handles hyphenated words (uh-huh) and contractions (it's).
        
        Args:
            text: Input text to process
            
        Returns:
            List of normalized words
        """
        if not text:
            return []
        
        # Extract words using regex (includes hyphenated words)
        words = self._word_pattern.findall(text)
        
        # Normalize case if needed
        if not self.config.case_sensitive:
            words = [w.lower() for w in words]
        
        return words
    
    def _extract_phrases(self, text: str, phrase_list: List[str]) -> List[str]:
        """
        Extract multi-word phrases from text.
        
        Args:
            text: Input text
            phrase_list: List of phrases to look for
            
        Returns:
            List of matched phrases
        """
        if not text:
            return []
        
        text_normalized = text if self.config.case_sensitive else text.lower()
        matched = []
        
        for phrase in phrase_list:
            phrase_normalized = phrase if self.config.case_sensitive else phrase.lower()
            if phrase_normalized in text_normalized:
                matched.append(phrase)
        
        return matched
    
    def should_interrupt(
        self,
        user_transcript: str,
        agent_speaking: bool,
    ) -> InterruptionDecision:
        """
        Determine whether the agent should be interrupted based on user input
        and current agent state.
        
        Args:
            user_transcript: The transcribed text from the user
            agent_speaking: Whether the agent is currently speaking
            
        Returns:
            InterruptionDecision with the decision and reasoning
        """
        # If handler is disabled, always interrupt (default behavior)
        if not self.enabled:
            return InterruptionDecision(
                should_interrupt=True,
                reason="Handler disabled - default behavior"
            )
        
        # Handle empty or whitespace-only input
        if not user_transcript or not user_transcript.strip():
            return InterruptionDecision(
                should_interrupt=False,
                reason="Empty input - ignored"
            )
        
        # If agent is NOT speaking, always process the input
        # (user is responding to agent's question or starting conversation)
        if not agent_speaking:
            return InterruptionDecision(
                should_interrupt=True,
                reason="Agent not speaking - process user input"
            )
        
        # Agent IS speaking - analyze the transcript
        
        # Check for multi-word interrupt phrases first
        interrupt_phrases = self._extract_phrases(user_transcript, self.config.interrupt_words)
        
        # Extract individual words
        words = self._extract_words(user_transcript)
        
        if not words:
            return InterruptionDecision(
                should_interrupt=False,
                reason="No words detected"
            )
        
        # Find matched ignore and interrupt words
        matched_ignore = [w for w in words if w in self._ignore_set]
        matched_interrupt = [w for w in words if w in self._interrupt_set]
        
        # Add phrase matches to interrupt list
        if interrupt_phrases:
            matched_interrupt.extend(interrupt_phrases)
        
        # Decision logic:
        # 1. If contains any interrupt words/phrases → INTERRUPT
        if matched_interrupt:
            return InterruptionDecision(
                should_interrupt=True,
                reason=f"Contains interrupt command: {', '.join(matched_interrupt)}",
                matched_ignore_words=matched_ignore,
                matched_interrupt_words=matched_interrupt,
                is_pure_backchanneling=False
            )
        
        # 2. If ALL words are ignore words → IGNORE (pure backchanneling)
        if len(matched_ignore) == len(words):
            return InterruptionDecision(
                should_interrupt=False,
                reason=f"Pure backchanneling: {', '.join(matched_ignore)}",
                matched_ignore_words=matched_ignore,
                matched_interrupt_words=[],
                is_pure_backchanneling=True
            )
        
        # 3. Mixed content or words not in either list → INTERRUPT
        #    (user is trying to say something substantive)
        return InterruptionDecision(
            should_interrupt=True,
            reason=f"Mixed/substantive content (not pure backchanneling)",
            matched_ignore_words=matched_ignore,
            matched_interrupt_words=[],
            is_pure_backchanneling=False
        )
    
    def add_ignore_words(self, words: List[str]):
        """
        Add words to the ignore list at runtime.
        
        Args:
            words: List of words to add
        """
        self.config.ignore_words.extend(words)
        self._ignore_set = self._normalize_words(self.config.ignore_words)
        logger.info(f"Added {len(words)} ignore words: {words}")
    
    def add_interrupt_words(self, words: List[str]):
        """
        Add words to the interrupt list at runtime.
        
        Args:
            words: List of words to add
        """
        self.config.interrupt_words.extend(words)
        self._interrupt_set = self._normalize_words(self.config.interrupt_words)
        logger.info(f"Added {len(words)} interrupt words: {words}")
    
    def update_config(self, config: InterruptionConfig):
        """
        Update the entire configuration.
        
        Args:
            config: New configuration object
        """
        self.config = config
        self._compile_patterns()
        self._ignore_set = self._normalize_words(self.config.ignore_words)
        self._interrupt_set = self._normalize_words(self.config.interrupt_words)
        logger.info("Configuration updated")


# Backwards compatibility - export all classes at module level
__all__ = [
    "IntelligentInterruptionHandler",
    "InterruptionConfig", 
    "InterruptionDecision",
]
