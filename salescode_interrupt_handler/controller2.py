"""
Intelligent Interruption Controller for LiveKit Agents - FINAL FIXED VERSION

This module implements a context-aware interruption handling system that distinguishes
between passive acknowledgements (backchanneling) and active interruptions based on
the agent's current state.
"""

import time
import re
import logging
from enum import Enum
from typing import Set

logger = logging.getLogger(__name__)


class Decision(Enum):
    """
    Interruption decision types.
    
    IGNORE: Backchannel/filler word while agent is speaking - ignore completely
    INTERRUPT: User command or real input while agent is speaking - stop agent
    NO_DECISION: Agent is silent, let framework handle normally
    """
    IGNORE = 0
    INTERRUPT = 1
    NO_DECISION = 2


# Grace period to handle state transition timing
GRACE_PERIOD_SECONDS = 0.5


class InterruptionController:
    """
    Context-aware controller that filters user input based on agent state.
    
    Logic Matrix:
    - Agent Speaking + Filler ("yeah") → IGNORE (continue speaking)
    - Agent Speaking + Command ("stop") → INTERRUPT (stop immediately)
    - Agent Speaking + Unknown words → INTERRUPT (real interruption)
    - Agent Silent + Any input → NO_DECISION (process normally)
    """
    
    def __init__(self):
        """Initialize the interruption controller with default word lists."""
        self.state = 'listening'
        self.last_speaking_time = 0
        
        # CRITICAL FIX: Include multi-word fillers as single entries
        # AND also include their component words separately
        self.IGNORE_WORDS: Set[str] = {
            # Basic affirmations
            "yeah", "yep", "yup", "yes",
            "ok", "okay", "k",
            
            # Verbal fillers
            "hmm", "mhm", "mm", "mmm","mhmm",
            "uh", "huh",  # Individual words
            "uh huh", "uh huh",  # Multi-word version
            "ah", "oh", "aha", "ooh",
            
            # Agreements
            "right", "alright", "all right",
            "sure", "fine",
            
            # Understanding indicators
            "got it", "gotcha", "i see",
            "makes sense",
            
            # Encouragement
            "cool", "nice", "great", "good",
            "interesting", "wow",
        }
        
        self.INTERRUPT_WORDS: Set[str] = {
            "stop", "pause", "hold", "wait",
            "no", "nope", "nah",
            "but", "actually", "however",
            "wait a minute", "hold on",
            "what", "huh", "pardon", "sorry",
            "excuse me", "come again",
        }
        
        logger.info(f"InterruptionController initialized with {len(self.IGNORE_WORDS)} "
                   f"ignore words and {len(self.INTERRUPT_WORDS)} interrupt words")

    def update_agent_state(self, state: str):
        """Track agent state changes for context-aware decisions."""
        old_state = self.state
        
        if old_state == 'speaking' and state != 'speaking':
            self.last_speaking_time = time.time()
            logger.debug(f"Agent stopped speaking at {self.last_speaking_time}")
        
        self.state = state
        logger.debug(f"Agent state: {old_state} → {state}")

    def _normalize(self, text: str) -> str:
        """
        Normalize transcript text for consistent matching.
        
        CRITICAL: Converts hyphens to spaces BEFORE other processing
        so "uh-huh" becomes "uh huh" for matching.
        """
        if not text:
            return ""
        
        text = text.lower()
        text = text.replace('-', ' ')  # uh-huh → uh huh
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text

    def _is_agent_effectively_speaking(self) -> bool:
        """
        Determine if agent should be considered "speaking" for decision purposes.
        
        CRITICAL FIX: Only apply grace period if last_speaking_time was actually set
        (i.e., agent has spoken at least once this session).
        """
        if self.state == 'speaking':
            return True
        
        # Only check grace period if agent has spoken before
        if self.last_speaking_time == 0:
            return False
        
        current_time = time.time()
        time_since_speaking = current_time - self.last_speaking_time
        in_grace_period = time_since_speaking < GRACE_PERIOD_SECONDS
        
        if in_grace_period:
            logger.debug(f"In grace period ({time_since_speaking:.2f}s since stopped)")
        
        return in_grace_period

    def decide(self, transcript: str, is_final: bool) -> Decision:
        """
        Make intelligent interruption decision based on transcript and agent state.
        
        CRITICAL FIXES:
        1. Check exact phrase match first (for multi-word fillers)
        2. Then check for interrupt words
        3. Then check if ALL words are known fillers
        4. If any unknown word, interrupt
        """
        normalized = self._normalize(transcript)
        
        if not normalized:
            logger.debug("[DECISION] Empty transcript → IGNORE")
            return Decision.IGNORE
        
        is_agent_speaking = self._is_agent_effectively_speaking()
        
        # PRIORITY 1: Check if exact phrase is a known filler
        # This handles multi-word fillers like "uh huh", "got it"
        if is_agent_speaking and normalized in self.IGNORE_WORDS:
            logger.info(f"[DECISION] Exact phrase match in fillers: '{transcript}' → IGNORE")
            return Decision.IGNORE
        
        # Split into words for word-level analysis
        words = normalized.split()
        
        # PRIORITY 2: Check for interrupt commands (regardless of agent state)
        interrupt_words_found = [w for w in words if w in self.INTERRUPT_WORDS]
        if interrupt_words_found:
            logger.info(f"[DECISION] Interrupt commands: {interrupt_words_found} → INTERRUPT")
            return Decision.INTERRUPT
        
        # PRIORITY 3: Agent is speaking - check for unknown words
        if is_agent_speaking:
            # Check if ANY word is unknown (not in our ignore list)
            unknown_words = [w for w in words if w not in self.IGNORE_WORDS]
            
            if unknown_words:
                # Contains non-filler words → real interruption
                logger.info(f"[DECISION] Unknown words while speaking: {unknown_words} → INTERRUPT")
                return Decision.INTERRUPT
            else:
                # All individual words are known fillers
                logger.info(f"[DECISION] All words are fillers: '{transcript}' → IGNORE")
                return Decision.IGNORE
        
        # PRIORITY 4: Agent is silent - let framework handle
        logger.debug(f"[DECISION] Agent silent: '{transcript}' → NO_DECISION")
        return Decision.NO_DECISION

    def add_ignore_word(self, word: str):
        """Add a custom word to the ignore list."""
        normalized = self._normalize(word)
        if normalized:
            self.IGNORE_WORDS.add(normalized)
            logger.info(f"Added '{normalized}' to ignore list")

    def add_interrupt_word(self, word: str):
        """Add a custom word to the interrupt list."""
        normalized = self._normalize(word)
        if normalized:
            self.INTERRUPT_WORDS.add(normalized)
            logger.info(f"Added '{normalized}' to interrupt list")

    def remove_ignore_word(self, word: str):
        """Remove a word from the ignore list."""
        normalized = self._normalize(word)
        if normalized in self.IGNORE_WORDS:
            self.IGNORE_WORDS.remove(normalized)
            logger.info(f"Removed '{normalized}' from ignore list")

    def remove_interrupt_word(self, word: str):
        """Remove a word from the interrupt list."""
        normalized = self._normalize(word)
        if normalized in self.INTERRUPT_WORDS:
            self.INTERRUPT_WORDS.remove(normalized)
            logger.info(f"Removed '{normalized}' from interrupt list")

    def get_stats(self) -> dict:
        """Get current controller statistics."""
        return {
            "current_state": self.state,
            "ignore_words_count": len(self.IGNORE_WORDS),
            "interrupt_words_count": len(self.INTERRUPT_WORDS),
            "grace_period_seconds": GRACE_PERIOD_SECONDS,
            "time_since_speaking": time.time() - self.last_speaking_time if self.last_speaking_time > 0 else None,
        }