"""
Context-aware interruption filter for LiveKit Voice Agents.

Distinguishes between passive acknowledgements (yeah, ok, hmm) and active interruptions (stop, wait, no).
"""

from enum import Enum
from typing import Optional


class InterruptionType(Enum):
    """Types of user input."""
    PASSIVE = "passive"  # yeah, ok, hmm
    ACTIVE = "active"    # stop, wait, no
    COMMAND = "command"  # other
    UNKNOWN = "unknown"


class InterruptionFilter:
    """Intelligent filter for agent interruptions."""
    
    def __init__(self):
        # Words to ignore when agent is speaking
        self.passive_words = {
            'yeah', 'yep', 'yup', 'yes', 'ok', 'okay', 'hmm', 'huh',
            'uh-huh', 'uh huh', 'mm-hmm', 'mmhmm', 'mm', 'aha', 'ah',
            'ohh', 'oh', 'right', 'sure', 'got it', 'gotcha', 'mhm',
            'i see', 'i understand', 'understood', 'understood',
            'go on', 'continue', 'keep going', 'uh', 'uhh'
        }
        
        # Words that always trigger interruption
        self.interrupt_words = {
            'stop', 'wait', 'no', 'hold on', 'hold up', 'pause',
            'hang on', 'wait a second', 'wait a minute', 'slow down',
            'back up', 'hold it', 'cancel', 'never mind', 'actually'
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()
    
    def classify(self, transcript: str) -> InterruptionType:
        """Classify the type of interruption."""
        if not transcript or not transcript.strip():
            return InterruptionType.UNKNOWN
        
        normalized = self.normalize_text(transcript)
        words = normalized.split()
        
        # Check for interrupt words first (highest priority)
        for word in self.interrupt_words:
            if word in normalized:
                return InterruptionType.ACTIVE
        
        # Check if all words are passive
        if all(word in self.passive_words for word in words) and len(words) <= 3:
            return InterruptionType.PASSIVE
        
        return InterruptionType.COMMAND
    
    def should_interrupt_agent(
        self,
        transcript: str,
        agent_is_speaking: bool
    ) -> bool:
        """
        Determine if the agent should be interrupted.
        
        Args:
            transcript: User's spoken input
            agent_is_speaking: Whether agent is currently speaking
            
        Returns:
            True if agent should be interrupted, False otherwise
        """
        interruption_type = self.classify(transcript)
        
        # Active interruptions always work
        if interruption_type == InterruptionType.ACTIVE:
            return True
        
        # Passive words only ignored when agent is speaking
        if interruption_type == InterruptionType.PASSIVE and agent_is_speaking:
            return False
        
        # Everything else (commands, unknown) allows interrupt
        return True
