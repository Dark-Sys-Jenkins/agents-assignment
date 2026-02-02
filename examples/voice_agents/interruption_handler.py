"""
Intelligent interruption handler for LiveKit voice agents.
Distinguishes between backchanneling and active interruptions.
"""

import logging
from enum import Enum
from typing import Optional
from interruption_config import InterruptionConfig, DEFAULT_CONFIG

logger = logging.getLogger("interruption-handler")


class AgentState(Enum):
    """Agent speaking state."""
    SPEAKING = "speaking"
    SILENT = "silent"


class InterruptionHandler:
    """
    Manages intelligent interruption logic for voice agents.
    
    Core functionality:
    - Ignores backchanneling (yeah, ok, hmm) when agent is speaking
    - Processes same words as valid input when agent is silent
    - Detects semantic interruptions (mixed sentences with interrupt words)
    - Maintains state awareness for context-dependent behavior
    """
    
    def __init__(self, config: InterruptionConfig = DEFAULT_CONFIG):
        self.config = config
        self._agent_state = AgentState.SILENT
        
        logger.info(
            f"InterruptionHandler initialized - "
            f"Backchannel words: {len(config.backchanneling_words)}, "
            f"Interrupt words: {len(config.interrupt_words)}, "
            f"Enabled: {config.enabled}"
        )
    
    def set_agent_speaking(self, is_speaking: bool) -> None:
        """Update agent speaking state."""
        new_state = AgentState.SPEAKING if is_speaking else AgentState.SILENT
        if new_state != self._agent_state:
            logger.debug(f"Agent state: {self._agent_state.value} -> {new_state.value}")
            self._agent_state = new_state
    
    def is_agent_speaking(self) -> bool:
        """Check if agent is currently speaking."""
        return self._agent_state == AgentState.SPEAKING
    
    def should_allow_interruption(self, transcription: str) -> bool:
        """
        Determine if user input should be allowed to interrupt the agent.
        
        Args:
            transcription: User's speech as text
            
        Returns:
            True if interruption should be allowed, False if it should be ignored
        """
        if not self.config.enabled:
            # If handler is disabled, allow all interruptions (default behavior)
            return True
        
        if not transcription or not transcription.strip():
            return False
        
        text = transcription.lower().strip()
        words = [w for w in text.split() if w]
        
        if not words:
            return False
        
        agent_speaking = self.is_agent_speaking()
        
        # Log the decision process
        logger.info(
            f"Evaluating: '{text}' | Agent state: {self._agent_state.value}"
        )
        
        # CASE 1: Agent is SILENT - all input is valid
        if not agent_speaking:
            logger.info(f"✓ Agent silent - allowing input: '{text}'")
            return True
        
        # CASE 2: Agent is SPEAKING - apply intelligent filtering
        
        # Priority 1: Check for explicit interrupt words
        interrupt_words_found = [w for w in words if w in self.config.interrupt_words]
        if interrupt_words_found:
            logger.info(
                f"✓ Interrupt word(s) detected: {interrupt_words_found} - "
                f"allowing interruption"
            )
            return True
        
        # Priority 2: Check if it's pure backchanneling
        backchannel_words = [w for w in words if w in self.config.backchanneling_words]
        other_words = [w for w in words if w not in self.config.backchanneling_words]
        
        is_pure_backchannel = len(backchannel_words) == len(words)
        
        if is_pure_backchannel:
            logger.info(f"✗ Pure backchannel: '{text}' - IGNORING (agent continues)")
            return False
        
        # Priority 3: Mixed input (backchannel + content)
        if other_words:
            logger.info(
                f"✓ Content words detected: {other_words} - allowing interruption"
            )
            return True
        
        # Default: allow interruption
        logger.info(f"✓ Default allow for: '{text}'")
        return True
    
    def analyze_input(self, text: str) -> dict:
        """
        Analyze user input for debugging purposes.
        
        Returns:
            Dictionary with detailed analysis
        """
        words = [w.lower() for w in text.split() if w]
        
        backchannel = [w for w in words if w in self.config.backchanneling_words]
        interrupt = [w for w in words if w in self.config.interrupt_words]
        other = [
            w for w in words 
            if w not in self.config.backchanneling_words 
            and w not in self.config.interrupt_words
        ]
        
        return {
            'original': text,
            'agent_state': self._agent_state.value,
            'word_count': len(words),
            'backchannel_words': backchannel,
            'interrupt_words': interrupt,
            'other_words': other,
            'is_pure_backchannel': len(backchannel) == len(words) and len(words) > 0,
            'decision': 'ALLOW' if self.should_allow_interruption(text) else 'IGNORE'
        }