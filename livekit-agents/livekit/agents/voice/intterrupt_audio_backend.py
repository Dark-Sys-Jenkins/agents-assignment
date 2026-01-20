"""
Backchannel-aware interruption handler for LiveKit agents.

This module implements intelligent conversation flow management by distinguishing
between passive backchanneling (acknowledgments like "yeah", "hmm") and active
interruptions (commands like "stop", "wait") based on agent speaking state.

Key Features:
- State-aware filtering (speaking vs. silent)
- Configurable backchannel word lists
- Semantic analysis for mixed inputs
- Phrase-level pattern matching
- Performance optimized for real-time processing
"""

import re
from typing import Set, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class InterruptionReason(Enum):
    """Enumeration of possible interruption decision reasons."""
    NO_DETECTABLE_WORDS = "no_detectable_words"
    MEANINGFUL_SPEECH = "meaningful_speech_detected"
    BACKCHANNEL_WHILE_SPEAKING = "backchannel_during_agent_speech"
    BACKCHANNEL_WHILE_IDLE = "backchannel_while_agent_idle"
    EXPLICIT_COMMAND = "explicit_command_detected"
    MIXED_CONTENT = "mixed_backchannel_and_command"


@dataclass
class InterruptionSettings:
    """Configuration for interruption handling behavior.
    
    Attributes:
        backchannel_words: Single-word acknowledgments to ignore while speaking
        backchannel_phrases: Multi-word phrases to ignore while speaking
        explicit_commands: Words/phrases that always trigger interruption
        enabled: Master switch for interruption filtering
        case_sensitive: Whether to perform case-sensitive matching
        partial_word_match: Allow matching word parts (e.g., "okay" matches "ok")
        debug: Enable verbose logging
    """
    
    backchannel_words: List[str] = field(default_factory=lambda: [
        # Single syllable acknowledgments
        "yeah", "yep", "yup", "yes", "ya", "ye",
        "ok", "okay", "k",
        "hmm", "hm", "mhm", "mm", "mmm",
        "uh", "um", "ah", "oh",
        "uh-huh", "mm-hmm", "uh-ha",
        
        # Affirmations
        "right", "correct", "true", "sure", "exactly",
        "totally", "absolutely", "definitely",
        "indeed", "certainly", "agreed",
        
        # Listening cues
        "i see", "got it", "gotcha", "cool", "nice",
        "interesting", "wow", "really",
        
        # Continuations
        "and", "so", "then", "well",
    ])
    
    backchannel_phrases: List[str] = field(default_factory=lambda: [
        "i see", "got it", "makes sense", "fair enough",
        "oh okay", "oh yeah", "ah okay", "uh huh",
        "mm hmm", "oh really", "i understand", "that's right",
        "for sure", "of course", "no doubt", "you bet",
    ])
    
    explicit_commands: List[str] = field(default_factory=lambda: [
        # Stop commands
        "stop", "wait", "hold", "pause", "hang on", "hold on",
        "hold up", "wait a minute", "wait a second", "one second",
        
        # Negations
        "no", "nope", "nah", "never", "not", "don't",
        
        # Corrections/Interruptions
        "actually", "but", "however", "although", "except",
        "listen", "hey", "excuse me", "sorry",
        
        # Questions (typically require response)
        "what", "when", "where", "who", "why", "how",
        "can you", "could you", "will you", "would you",
        "is it", "are you", "do you",
        
        # Topic changes
        "anyway", "by the way", "speaking of", "question",
        "let me", "i want", "i need", "i think",
    ])
    
    enabled: bool = True
    case_sensitive: bool = False
    partial_word_match: bool = False
    debug: bool = False


class InterruptionHandler:
    """
    Intelligent interruption filter with state-aware backchannel detection.
    
    This handler determines whether user speech should interrupt the agent
    based on semantic content and current agent state (speaking/silent).
    
    Logic:
    - Agent speaking + backchannel only → IGNORE (continue speaking)
    - Agent speaking + command/meaningful → INTERRUPT (stop and listen)
    - Agent silent + any input → RESPOND (normal processing)
    """
    
    def __init__(self, settings: Optional[InterruptionSettings] = None):
        """Initialize the interruption handler.
        
        Args:
            settings: Configuration object. If None, uses defaults.
        """
        self.settings = settings or InterruptionSettings()
        self._prepare_lookup_structures()
    
    def _prepare_lookup_structures(self) -> None:
        """Build optimized lookup structures for O(1) word matching."""
        # Normalize all words for fast lookup
        norm = self._normalize
        
        # Single word backchannels
        self._backchannel_set: Set[str] = {
            norm(word) for word in self.settings.backchannel_words
        }
        
        # Multi-word phrases (kept as list for phrase matching)
        self._backchannel_phrases: List[str] = [
            norm(phrase) for phrase in self.settings.backchannel_phrases
        ]
        
        # Commands and meaningful words
        self._command_set: Set[str] = {
            norm(word) for word in self.settings.explicit_commands
        }
        
        # Compile regex for efficient tokenization
        # Captures words with optional hyphens (e.g., "uh-huh", "mm-hmm")
        self._word_pattern = re.compile(r'\b[\w-]+\b')
        
        if self.settings.debug:
            print(f"Loaded {len(self._backchannel_set)} backchannel words")
            print(f"Loaded {len(self._backchannel_phrases)} backchannel phrases")
            print(f"Loaded {len(self._command_set)} command words")
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text (lowercase, stripped)
        """
        text = text.strip().lower()
        # remove trailing punctuation like ".", "!", "?", "...", ","
        text = re.sub(r"[^\w\s]+$", "", text)
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Extract word tokens from text.
        
        Uses compiled regex for efficient extraction. Handles:
        - Punctuation removal
        - Hyphenated words (e.g., "uh-huh", "mm-hmm")
        - Case normalization
        - Whitespace handling
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of normalized word tokens
        """
        normalized = self._normalize(text)
        tokens = self._word_pattern.findall(normalized)
        # Remove trailing punctuation from each token
        return [token.rstrip('.,!?;:') for token in tokens]
    
    def _is_phrase_match(self, text: str) -> bool:
        """Check if entire text matches a known backchannel phrase.
        
        Args:
            text: Normalized text to check
            
        Returns:
            True if text exactly matches a backchannel phrase
        """
        normalized = self._normalize(text)
        return normalized in self._backchannel_phrases
    
    def _contains_command(self, words: List[str]) -> Tuple[bool, Optional[str]]:
        """Check if word list contains any explicit command.
        
        Args:
            words: List of normalized word tokens
            
        Returns:
            Tuple of (has_command, first_command_found)
        """
        for word in words:
            if word in self._command_set:
                return True, word
            
            # Check multi-word commands
            # Reconstruct for phrase matching
            text = " ".join(words)
            for cmd in self.settings.explicit_commands:
                if self._normalize(cmd) in text:
                    return True, cmd
        
        return False, None
    
    def _is_pure_backchannel(self, words: List[str], original_text: str) -> bool:
        """Determine if input consists only of backchannel cues.
        
        Args:
            words: Tokenized words
            original_text: Original text for phrase matching
            
        Returns:
            True if all content is backchannel acknowledgment
        """
        # Check if entire phrase is a known backchannel
        if self._is_phrase_match(original_text):
            return True
        
        # Check if all individual words are backchannels
        if not words:
            return False
            
        for word in words:
            # Remove any trailing punctuation for comparison
            clean_word = word.rstrip('.,!?;:')
            if clean_word and clean_word not in self._backchannel_set:
                return False
        
        return True
    
    def should_ignore_interrupt(
        self, 
        text: str, 
        is_speaking: bool
    ) -> bool:
        """Primary decision function: should this input be ignored?
        
        This is the main API called by agent_activity.py to determine
        whether detected user speech should interrupt the agent.
        
        Decision Logic:
        1. Handler disabled → Never ignore (False)
        2. Empty/no words → Don't ignore (False)
        3. Contains command → Never ignore (False)
        4. Pure backchannel + agent speaking → Ignore (True)
        5. Pure backchannel + agent silent → Don't ignore (False)
        6. Default → Don't ignore (False)
        
        Args:
            text: User's transcribed speech
            is_speaking: Whether agent is currently speaking/playing audio
            
        Returns:
            True if input should be ignored (agent continues)
            False if input should interrupt agent
        """
        # Handler disabled - pass through all interrupts
        if not self.settings.enabled:
            return False
        # debug step
        # print(f"if not self.settings.enabled: {self.settings.enabled}")
        
        # Empty input - don't ignore
        if not text or not text.strip():
            return False
        # debug step
        # print(f"if not text or not text.strip(): {text}") 
        
        # Tokenize input
        words = self._tokenize(text)
        
        # No detectable words - don't ignore
        if not words:
            return False
        # debug step
        # print(f"if not words: {words}")
        
        # Check for explicit commands first (highest priority)
        has_command, command = self._contains_command(words)
        if has_command:
            if self.settings.debug:
                print(f"Command detected: '{command}' → INTERRUPT")
            return False
        # debug step
        # print(f"if has_command: {has_command}, command: {command}")
        
        # Check if pure backchannel
        is_backchannel = self._is_pure_backchannel(words, text)
        
        # State-based decision
        if is_backchannel and is_speaking:
            # Backchannel while speaking → IGNORE
            if self.settings.debug:
                print(f"Backchannel while speaking: '{text}' → IGNORE")
            return True
        # print(f"if is_backchannel and is_speaking: {is_backchannel}, {is_speaking}")
        
        
        # All other cases → Don't ignore
        if self.settings.debug:
            reason = "backchannel while silent" if is_backchannel else "meaningful content"
            print(f"{reason}: '{text}' → RESPOND")
        # print(f"All other cases → Don't ignore")
        
        return False
    
    def explain_decision(
        self, 
        text: str, 
        is_speaking: bool
    ) -> Tuple[bool, InterruptionReason, str]:
        """Detailed explanation of interruption decision for debugging/logging.
        
        Args:
            text: User's transcribed speech
            is_speaking: Whether agent is currently speaking
            
        Returns:
            Tuple of (should_ignore, reason_enum, human_readable_explanation)
        """
        if not text or not text.strip():
            return False, InterruptionReason.NO_DETECTABLE_WORDS, "No text to process"
        
        words = self._tokenize(text)
        
        if not words:
            return False, InterruptionReason.NO_DETECTABLE_WORDS, "No detectable words"
        
        # Check for commands
        has_command, command = self._contains_command(words)
        if has_command:
            explanation = f"Explicit command '{command}' detected"
            return False, InterruptionReason.EXPLICIT_COMMAND, explanation
        
        # Check backchannel
        is_backchannel = self._is_pure_backchannel(words, text)
        
        if is_backchannel:
            if is_speaking:
                return True, InterruptionReason.BACKCHANNEL_WHILE_SPEAKING, \
                       "Listener acknowledgment during agent speech - ignored"
            else:
                return False, InterruptionReason.BACKCHANNEL_WHILE_IDLE, \
                       "Acknowledgment while agent idle - processed normally"
        
        # Meaningful content
        explanation = f"Meaningful speech with {len(words)} words"
        return False, InterruptionReason.MEANINGFUL_SPEECH, explanation
    
    def update_settings(self, **kwargs) -> None:
        """Update settings at runtime and rebuild lookup structures.
        
        Args:
            **kwargs: Settings attributes to update
        """
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        self._prepare_lookup_structures()
    
    def get_stats(self) -> dict:
        """Get handler statistics for monitoring.
        
        Returns:
            Dictionary with handler statistics
        """
        return {
            "enabled": self.settings.enabled,
            "backchannel_words_count": len(self._backchannel_set),
            "backchannel_phrases_count": len(self._backchannel_phrases),
            "command_words_count": len(self._command_set),
            "case_sensitive": self.settings.case_sensitive,
        }