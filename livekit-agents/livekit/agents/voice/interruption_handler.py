"""
Intelligent interruption handler for LiveKit voice agents.

This module provides context-aware interruption handling that distinguishes
between passive acknowledgments (backchanneling) and active commands based on
whether the agent is currently speaking.
"""

import logging
import re
from typing import Set

logger = logging.getLogger(__name__)


class InterruptionHandler:
    """
    Handles intelligent interruption decisions based on agent speaking state.
    
    Logic:
    - If agent is NOT speaking: All input is valid (don't interrupt)
    - If agent IS speaking:
        - Check if transcript contains command words → Interrupt
        - Check if all words are ignorable → Don't interrupt  
        - Otherwise → Interrupt
    """
    
    def __init__(
        self,
        ignore_words: Set[str],
        command_words: Set[str],
    ):
        """
        Initialize the interruption handler.
        
        Args:
            ignore_words: Set of words to ignore when agent is speaking
            command_words: Set of words that always trigger interruption
        """
        # Normalize all words to lowercase
        normalized_ignore = {w.lower().strip() for w in ignore_words}
        self.ignore_phrases = {w for w in normalized_ignore if " " in w}
        self.ignore_words = {w for w in normalized_ignore if " " not in w}
        self.command_words = {w.lower().strip() for w in command_words}
        
        # Track agent state
        self._agent_is_speaking = False
        
        # Statistics for debugging
        self.stats = {
            "total_checks": 0,
            "interrupted": 0,
            "ignored": 0,
            "while_speaking": 0,
            "while_silent": 0,
        }
        
        logger.info(
            f"InterruptionHandler initialized: "
            f"{len(self.ignore_words)} ignore words, "
            f"{len(self.command_words)} command words"
        )

    def _normalize(self, transcript: str) -> str:
        return re.sub(r"\s+", " ", transcript.strip().lower())

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z]+(?:[-'][a-zA-Z]+)*", text)

    def _remove_ignore_phrases(self, text: str) -> str:
        if not self.ignore_phrases or not text:
            return text

        cleaned = text
        for phrase in sorted(self.ignore_phrases, key=len, reverse=True):
            pattern = r"\b" + re.escape(phrase) + r"\b"
            cleaned = re.sub(pattern, " ", cleaned)

        return re.sub(r"\s+", " ", cleaned).strip()

    def extract_words(self, transcript: str) -> list[str]:
        """Extract normalized tokens from transcript."""
        return self._tokenize(self._normalize(transcript))

    def is_pure_backchannel(self, transcript: str) -> bool:
        """Return True if transcript is composed only of ignorable words/phrases."""
        normalized = self._normalize(transcript)
        if not normalized:
            return False

        without_phrases = self._remove_ignore_phrases(normalized)
        if not without_phrases:
            return True

        words = self._tokenize(without_phrases)
        if not words:
            return True

        return all(word in self.ignore_words for word in words)
    
    @property
    def agent_is_speaking(self) -> bool:
        """Get current agent speaking state."""
        return self._agent_is_speaking
    
    def set_agent_speaking(self, is_speaking: bool) -> None:
        """
        Update agent speaking state.
        
        Args:
            is_speaking: True if agent is currently speaking
        """
        if self._agent_is_speaking != is_speaking:
            logger.debug(f"Agent speaking state: {is_speaking}")
            self._agent_is_speaking = is_speaking
    
    def should_interrupt(self, transcript: str) -> bool:
        """
        Determine if transcript should interrupt.
        
        NEW LOGIC: Ignore backchanneling words throughout conversation.
        Only interrupt for commands or real content (non-backchanneling).
        """
        self.stats["total_checks"] += 1
        
        # Normalize
        transcript_original = transcript
        transcript = self._normalize(transcript)
        
        if not transcript:
            return False
        
        # Extract words
        words = self._tokenize(transcript)
        
        if not words:
            return False
        
        logger.info(
            f"🧠 INTERRUPTION HANDLER: Processing '{transcript_original}' | "
            f"Agent speaking: {self._agent_is_speaking} | "
            f"Words: {words}"
        )
        
        # ===== RULE 1: Check for command words (ALWAYS interrupt) =====
        logger.info(f"🔍 Checking for command words in: {words}")
        for word in words:
            if word in self.command_words:
                self.stats["interrupted"] += 1
                logger.info(f"🚨 COMMAND DETECTED: '{word}' in '{transcript_original}' - INTERRUPTING")
                return True
        
        logger.info(f"✅ No command words found")
        
        # ===== RULE 2: Check for repeated words (emphasis) =====
        logger.info(f"🔍 Checking for repeated words in: {words}")
        # If same word appears 2+ times, it's emphasis, not backchanneling
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        logger.info(f"📊 Word counts: {word_counts}")
        
        # If any word repeated 2+ times, treat as real input (interrupt)
        for word, count in word_counts.items():
            if count >= 2 and word not in self.ignore_words:
                self.stats["interrupted"] += 1
                logger.info(
                    f"🔄 REPEATED WORD: '{word}' x{count} = emphasis in '{transcript_original}' - INTERRUPTING"
                )
                return True
        
        logger.info(f"✅ No repeated words found")
        
        # ===== RULE 3: Check if all words are backchanneling (ALWAYS ignore) =====
        logger.info(f"🔍 Checking if all words are backchanneling: {words}")
        all_backchanneling = self.is_pure_backchannel(transcript)
        logger.info(f"🤔 All backchanneling result: {all_backchanneling}")
        
        # Check each word individually for detailed logging
        word_status = []
        for word in words:
            is_ignored = word in self.ignore_words
            status = "ignored" if is_ignored else "valid"
            word_status.append(f"{word}({status})")
        
        logger.info(f"📝 Word status: {' '.join(word_status)}")
        
        if all_backchanneling:
            self.stats["ignored"] += 1
            logger.info(f"🔇 PURE BACKCHANNELING: '{transcript_original}' - IGNORING")
            return False
        
        # ===== RULE 4: Mixed content - check ratio =====
        logger.info(f"🔍 Checking mixed content ratio for: {words}")
        ignorable_count = sum(1 for word in words if word in self.ignore_words)
        ignorable_ratio = ignorable_count / len(words)
        
        logger.info(f"📊 Mixed content: {ignorable_count}/{len(words)} ignorable = {ignorable_ratio:.0%}")
        
        if ignorable_ratio >= 0.75:
            self.stats["ignored"] += 1
            logger.info(f"🔇 MOSTLY BACKCHANNELING: {ignorable_ratio:.0%} ignorable in '{transcript_original}' - IGNORING")
            return False
        
        # ===== RULE 5: Real content (interrupt) =====
        self.stats["interrupted"] += 1
        logger.info(f"🎯 REAL CONTENT: '{transcript_original}' - INTERRUPTING")
        return True
    
    def get_stats(self) -> dict:
        """Get handler statistics."""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total_checks": 0,
            "interrupted": 0,
            "ignored": 0,
            "while_speaking": 0,
            "while_silent": 0,
        }

