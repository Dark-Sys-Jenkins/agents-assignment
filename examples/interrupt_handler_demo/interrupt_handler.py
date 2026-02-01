from dataclasses import dataclass
from typing import Set, List
from enum import Enum
import asyncio
from collections import deque


class AgentState(Enum):
    SPEAKING = "speaking"
    SILENT = "silent"
    PROCESSING = "processing"


class InterruptType(Enum):
    IGNORE = "ignore"
    INTERRUPT = "interrupt"
    RESPOND = "respond"


@dataclass
class InterruptConfig:
    """Configuration for interrupt handling"""
    ignore_words: Set[str] = None
    command_words: Set[str] = None
    buffer_timeout: float = 0.3  # seconds to buffer before deciding
    
    def __post_init__(self):
        if self.ignore_words is None:
            self.ignore_words = {'yeah', 'ok', 'hmm', 'right', 'uh-huh', 
                                 'aha', 'mmm', 'yes', 'yep', 'okay'}
        if self.command_words is None:
            self.command_words = {'wait', 'stop', 'no', 'halt', 'cancel'}


class InterruptHandler:
    """
    Main logic layer for context-aware interruption handling.
    Distinguishes between passive acknowledgements and active interruptions.
    """
    
    def __init__(self, config: InterruptConfig = None):
        self.config = config or InterruptConfig()
        self.agent_state = AgentState.SILENT
        self.transcription_buffer = deque(maxlen=10)
        self.pending_interrupt = None
        self.lock = asyncio.Lock()
        
    def set_agent_state(self, state: AgentState):
        """Update agent's current speaking state"""
        self.agent_state = state
        
    def _contains_command(self, text: str) -> bool:
        """Check if transcription contains any command words"""
        text_lower = text.lower()
        return any(cmd in text_lower for cmd in self.config.command_words)
    
    def _is_only_ignore_words(self, text: str) -> bool:
        """Check if transcription contains only ignore words"""
        words = text.lower().split()
        if not words:
            return False
            
        # Check if all words are in ignore list
        return all(word in self.config.ignore_words for word in words)
    
    async def process_transcription(self, text: str) -> InterruptType:
        """
        Process incoming transcription and determine interrupt type.
        This should be called when STT produces text.
        """
        async with self.lock:
            # Store in buffer for contextual analysis
            self.transcription_buffer.append(text)
            
            # Check if this is a mixed input
            has_commands = self._contains_command(text)
            all_ignore_words = self._is_only_ignore_words(text)
            
            # Logic matrix implementation
            if self.agent_state == AgentState.SPEAKING:
                if has_commands:
                    # Contains command words - INTERRUPT
                    return InterruptType.INTERRUPT
                elif all_ignore_words:
                    # Only ignore words while speaking - IGNORE
                    return InterruptType.IGNORE
                else:
                    # Other speech while agent is speaking - INTERRUPT
                    return InterruptType.INTERRUPT
                    
            elif self.agent_state == AgentState.SILENT:
                # Agent is silent, always RESPOND to user input
                return InterruptType.RESPOND
                
            else:
                # Default case
                return InterruptType.RESPOND