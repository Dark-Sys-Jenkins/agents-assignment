"""
Intelligent Interruption Handler for LiveKit Agents
Distinguishes between passive backchanneling and active interruptions
"""

import logging
from typing import Set, Optional
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class InterruptionConfig:
    """Configuration for interruption handling"""
    # Words to ignore when agent is speaking
    ignore_words: Set[str] = None
    # Words that always cause interruption
    interrupt_words: Set[str] = None
    # Minimum confidence threshold for STT
    confidence_threshold: float = 0.7
    
    def __post_init__(self):
        if self.ignore_words is None:
            self.ignore_words = {
                'yeah', 'ok', 'okay', 'hmm', 'mhmm', 'uh-huh', 
                'right', 'sure', 'got it', 'i see', 'alright'
            }
        if self.interrupt_words is None:
            self.interrupt_words = {
                'wait', 'stop', 'no', 'hold on', 'pause', 'hang on'
            }


class IntelligentInterruptionHandler:
    """
    Handles interruptions intelligently by distinguishing between
    backchanneling (passive acknowledgment) and active interruptions.
    """
    
    def __init__(self, config: Optional[InterruptionConfig] = None):
        self.config = config or InterruptionConfig()
        self._agent_is_speaking = False
        self._pending_transcriptions = []
        self._lock = asyncio.Lock()
        
    def set_agent_speaking_state(self, is_speaking: bool):
        """Update the agent's speaking state"""
        self._agent_is_speaking = is_speaking
        logger.debug(f"Agent speaking state changed to: {is_speaking}")
    
    def is_agent_speaking(self) -> bool:
        """Check if agent is currently speaking"""
        return self._agent_is_speaking
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        return text.lower().strip().rstrip('.,!?')
    
    def _contains_interrupt_word(self, text: str) -> bool:
        """Check if text contains any interrupt words"""
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        # Check for exact matches of interrupt words
        for word in words:
            if word in self.config.interrupt_words:
                return True
        
        # Check for phrases
        for interrupt_phrase in self.config.interrupt_words:
            if ' ' in interrupt_phrase and interrupt_phrase in normalized:
                return True
                
        return False
    
    def _is_only_backchannel(self, text: str) -> bool:
        """
        Check if the text is purely backchanneling.
        Returns True only if ALL words are in the ignore list.
        """
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        if not words:
            return False
        
        # Check if it's exactly a backchannel phrase
        if normalized in self.config.ignore_words:
            return True
        
        # Check if all words are backchannel words
        return all(word in self.config.ignore_words for word in words)
    
    async def should_interrupt(
        self, 
        transcription: str, 
        is_final: bool = True,
        confidence: float = 1.0
    ) -> bool:
        """
        Determine if the user input should interrupt the agent.
        
        Args:
            transcription: The transcribed user speech
            is_final: Whether this is a final transcription
            confidence: Confidence score of the transcription
            
        Returns:
            True if the agent should be interrupted, False otherwise
        """
        async with self._lock:
            # Only process final transcriptions with sufficient confidence
            if not is_final or confidence < self.config.confidence_threshold:
                logger.debug(f"Skipping non-final or low-confidence transcription: {transcription}")
                return False
            
            # If agent is NOT speaking, all inputs are valid
            if not self._agent_is_speaking:
                logger.info(f"Agent is silent, processing input: '{transcription}'")
                return True
            
            # Agent IS speaking - apply intelligent filtering
            
            # Check if text contains interrupt words (even mixed with backchannels)
            if self._contains_interrupt_word(transcription):
                logger.info(f"Interrupt word detected while agent speaking: '{transcription}'")
                return True
            
            # Check if it's purely backchanneling
            if self._is_only_backchannel(transcription):
                logger.info(f"Backchannel detected while agent speaking, IGNORING: '{transcription}'")
                return False
            
            # Any other speech while agent is speaking is an interruption
            logger.info(f"Active speech detected while agent speaking: '{transcription}'")
            return True
    
    def update_config(self, 
                     ignore_words: Optional[Set[str]] = None,
                     interrupt_words: Optional[Set[str]] = None):
        """Update the configuration dynamically"""
        if ignore_words is not None:
            self.config.ignore_words = ignore_words
        if interrupt_words is not None:
            self.config.interrupt_words = interrupt_words
        logger.info(f"Configuration updated - Ignore: {self.config.ignore_words}, Interrupt: {self.config.interrupt_words}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_handler():
        handler = IntelligentInterruptionHandler()
        
        print("Test 1: Agent speaking, user says 'yeah'")
        handler.set_agent_speaking_state(True)
        result = await handler.should_interrupt("yeah", is_final=True)
        print(f"Should interrupt: {result} (Expected: False)\n")
        
        print("Test 2: Agent speaking, user says 'wait'")
        handler.set_agent_speaking_state(True)
        result = await handler.should_interrupt("wait", is_final=True)
        print(f"Should interrupt: {result} (Expected: True)\n")
        
        print("Test 3: Agent silent, user says 'yeah'")
        handler.set_agent_speaking_state(False)
        result = await handler.should_interrupt("yeah", is_final=True)
        print(f"Should interrupt: {result} (Expected: True)\n")
        
        print("Test 4: Agent speaking, user says 'yeah but wait'")
        handler.set_agent_speaking_state(True)
        result = await handler.should_interrupt("yeah but wait", is_final=True)
        print(f"Should interrupt: {result} (Expected: True)\n")
        
        print("Test 5: Agent speaking, user says 'okay right'")
        handler.set_agent_speaking_state(True)
        result = await handler.should_interrupt("okay right", is_final=True)
        print(f"Should interrupt: {result} (Expected: False)\n")
    
    asyncio.run(test_handler())