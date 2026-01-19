"""
Smart Interruption Handler

Core logic for context-aware interruption handling that distinguishes between
passive affirmations and command words based on agent speaking state.
"""

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Set

try:
    from .config import InterruptionConfig
except ImportError:
    from config import InterruptionConfig

logger = logging.getLogger(__name__)


class InterruptionDecision(Enum):
    """Decision on how to handle user input."""
    
    INTERRUPT = "interrupt"  # Stop agent and process input
    IGNORE = "ignore"  # Ignore input completely (passive word while speaking)
    PROCESS = "process"  # Process input normally (agent is silent)


@dataclass
class TranscriptAnalysis:
    """Analysis result of a transcript."""
    
    has_command_word: bool
    has_passive_only: bool
    detected_commands: Set[str]
    detected_passives: Set[str]
    word_count: int


@dataclass
class InterruptionEvent:
    """Event information for logging and debugging."""
    
    transcript: str
    decision: InterruptionDecision
    agent_speaking: bool
    analysis: TranscriptAnalysis
    timestamp: float


class SmartInterruptionHandler:
    """
    Intelligent interruption handler that uses context-aware logic.
    
    Key behaviors:
    - Ignores passive words (yeah, okay, etc.) while agent is speaking
    - Processes the same words when agent is silent
    - Always interrupts on command words (stop, wait, etc.)
    - Handles mixed input (e.g., "yeah but wait" triggers interrupt)
    """
    
    def __init__(self, config: InterruptionConfig | None = None):
        """
        Initialize the smart interruption handler.
        
        Args:
            config: Configuration for passive/command words. Uses defaults if None.
        """
        self.config = config or InterruptionConfig()
        self._agent_speaking = False
        
        # Statistics
        self._stats = {
            "total_decisions": 0,
            "interrupts": 0,
            "ignores": 0,
            "processes": 0,
            "while_speaking": 0,
            "while_silent": 0
        }
        
        logger.info(
            f"SmartInterruptionHandler initialized with "
            f"{len(self.config.passive_words)} passive words and "
            f"{len(self.config.command_words)} command words"
        )
    
    def on_agent_speaking_started(self) -> None:
        """Call this when the agent starts speaking."""
        self._agent_speaking = True
        logger.debug("Agent speaking started")
    
    def on_agent_speaking_stopped(self) -> None:
        """Call this when the agent stops speaking."""
        self._agent_speaking = False
        logger.debug("Agent speaking stopped")
    
    @property
    def is_agent_speaking(self) -> bool:
        """Check if agent is currently speaking."""
        return self._agent_speaking
    
    def analyze_transcript(self, transcript: str) -> TranscriptAnalysis:
        """
        Analyze a transcript to detect command words and passive words.
        
        Args:
            transcript: The user's speech transcript
            
        Returns:
            TranscriptAnalysis with detection results
        """
        if not transcript:
            return TranscriptAnalysis(
                has_command_word=False,
                has_passive_only=False,
                detected_commands=set(),
                detected_passives=set(),
                word_count=0
            )
        
        # Normalize transcript
        normalized = transcript.lower().strip()
        
        # Extract words (remove punctuation)
        words = re.findall(r'\b\w+(?:[-\']\w+)*\b', normalized)
        
        # Check for command phrases FIRST (highest priority)
        detected_commands: Set[str] = set()
        for phrase in self.config.command_phrases:
            if phrase in normalized:
                detected_commands.add(phrase)
        
        # Check for passive phrases
        detected_passives: Set[str] = set()
        for phrase in self.config.passive_phrases:
            if phrase in normalized:
                detected_passives.add(phrase)
        
        # Check individual words (if not already detected via phrases)
        for word in words:
            if word in self.config.command_words:
                detected_commands.add(word)
            elif word in self.config.passive_words:
                detected_passives.add(word)
        
        has_command = len(detected_commands) > 0
        has_passive_only = len(detected_passives) > 0 and len(detected_commands) == 0
        
        return TranscriptAnalysis(
            has_command_word=has_command,
            has_passive_only=has_passive_only,
            detected_commands=detected_commands,
            detected_passives=detected_passives,
            word_count=len(words)
        )
    
    def should_interrupt(self, transcript: str) -> InterruptionDecision:
        """
        Determine if the user input should interrupt the agent.
        
        Decision logic:
        1. If agent is NOT speaking: PROCESS (allow all input)
        2. If agent IS speaking:
           a. Contains command word: INTERRUPT
           b. Only contains passive words: IGNORE
           c. Mixed or other content: INTERRUPT
        
        Args:
            transcript: The user's speech transcript
            
        Returns:
            InterruptionDecision indicating how to handle the input
        """
        # Update statistics
        self._stats["total_decisions"] += 1
        if self._agent_speaking:
            self._stats["while_speaking"] += 1
        else:
            self._stats["while_silent"] += 1
        
        # Empty or whitespace-only transcript
        if not transcript or not transcript.strip():
            decision = InterruptionDecision.IGNORE
            self._stats["ignores"] += 1
            return decision
        
        # Analyze the transcript
        analysis = self.analyze_transcript(transcript)
        
        # Decision logic
        if not self._agent_speaking:
            # Agent is silent - process everything
            decision = InterruptionDecision.PROCESS
            self._stats["processes"] += 1
            logger.debug(
                f"Decision: PROCESS (agent silent) - '{transcript}'"
            )
        elif analysis.has_command_word:
            # Agent is speaking AND user said a command word - interrupt
            decision = InterruptionDecision.INTERRUPT
            self._stats["interrupts"] += 1
            logger.debug(
                f"Decision: INTERRUPT (command detected) - '{transcript}' "
                f"commands={analysis.detected_commands}"
            )
        elif analysis.has_passive_only:
            # Agent is speaking AND user only said passive words - ignore
            decision = InterruptionDecision.IGNORE
            self._stats["ignores"] += 1
            logger.debug(
                f"Decision: IGNORE (passive only while speaking) - '{transcript}' "
                f"passives={analysis.detected_passives}"
            )
        else:
            # Agent is speaking AND user said something else - interrupt
            # (This handles cases where user says something not in either list)
            decision = InterruptionDecision.INTERRUPT
            self._stats["interrupts"] += 1
            logger.debug(
                f"Decision: INTERRUPT (non-passive content) - '{transcript}'"
            )
        
        # Create event for logging
        event = InterruptionEvent(
            transcript=transcript,
            decision=decision,
            agent_speaking=self._agent_speaking,
            analysis=analysis,
            timestamp=time.time()
        )
        
        logger.info(
            f"Interruption decision: {decision.value} | "
            f"speaking={self._agent_speaking} | "
            f"transcript='{transcript[:50]}...'"
        )
        
        return decision
    
    def get_stats(self) -> dict:
        """Get statistics about interruption decisions."""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0
