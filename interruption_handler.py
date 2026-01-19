"""
Intelligent Interruption Handler for LiveKit Agents

This module provides context-aware interruption handling that distinguishes between:
- Passive acknowledgment (backchanneling): "yeah", "ok", "hmm" while agent is speaking
- Active interruption: "wait", "stop", "no" - always triggers interruption
- Normal input: other user speech

The handler maintains state about whether the agent is currently speaking and applies
filtering logic accordingly.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Set

logger = logging.getLogger(__name__)


class InterruptionType(Enum):
    """Types of user interruptions"""
    IGNORE = "ignore"  # Backchannel word while agent is speaking
    RESPOND = "respond"  # Valid input to process
    INTERRUPT = "interrupt"  # Stop/wait command - immediate action


@dataclass
class InterruptionConfig:
    """Configuration for interruption handling"""
    
    # Words that are considered backchanneling (passive acknowledgment)
    # Only ignored when agent is actively speaking
    backchannel_words: Set[str] = field(
        default_factory=lambda: {
            "yeah",
            "yes",
            "ok",
            "okay",
            "hmm",
            "hm",
            "uh-huh",
            "uh",
            "ah",
            "mm",
            "mhm",
            "right",
            "aha",
            "yep",
        }
    )
    
    # Words/phrases that are considered active interruption commands
    # These ALWAYS trigger an interrupt, regardless of agent state
    interrupt_commands: Set[str] = field(
        default_factory=lambda: {
            "wait",
            "stop",
            "no",
            "hold",
            "hold on",
            "halt",
            "hold up",
        }
    )
    
    # Enable/disable the interruption handler
    enabled: bool = True
    
    # Case-insensitive matching
    case_insensitive: bool = True
    
    def normalize(self, text: str) -> str:
        """Normalize text for comparison"""
        if self.case_insensitive:
            return text.lower().strip()
        return text.strip()


@dataclass
class InterruptionState:
    """Tracks the current interruption state"""
    
    # Whether the agent is currently speaking (generating or playing audio)
    agent_is_speaking: bool = False
    
    # Whether the agent is generating text/audio
    agent_is_generating: bool = False
    
    # Whether audio is being played back
    audio_is_playing: bool = False
    
    def update_speaking_state(self, generating: bool = False, playing: bool = False) -> None:
        """Update the agent's speaking state"""
        self.agent_is_generating = generating
        self.audio_is_playing = playing
        self.agent_is_speaking = generating or playing
    
    def agent_active(self) -> bool:
        """Check if agent is actively speaking"""
        return self.agent_is_speaking


class InterruptionHandler:
    """
    Handles intelligent interruption logic for AI agents
    
    Distinguishes between passive acknowledgment and active interruption based on
    whether the agent is currently speaking or silent.
    """
    
    def __init__(self, config: Optional[InterruptionConfig] = None):
        """
        Initialize the interruption handler
        
        Args:
            config: InterruptionConfig instance. If None, uses default configuration.
        """
        self.config = config or InterruptionConfig()
        self.state = InterruptionState()
        self._callbacks: List[Callable] = []
        
        logger.info(
            f"InterruptionHandler initialized with backchannel_words: {self.config.backchannel_words}, "
            f"interrupt_commands: {self.config.interrupt_commands}"
        )
    
    def register_interrupt_callback(self, callback: Callable) -> None:
        """Register a callback to be called on interrupt"""
        self._callbacks.append(callback)
        logger.debug(f"Registered interrupt callback: {callback.__name__}")
    
    def set_agent_speaking(self, is_speaking: bool) -> None:
        """
        Set whether the agent is currently speaking
        
        Args:
            is_speaking: True if agent is generating or playing audio
        """
        old_state = self.state.agent_is_speaking
        self.state.update_speaking_state(playing=is_speaking)
        
        if old_state != is_speaking:
            logger.info(f"Agent speaking state changed: {old_state} -> {is_speaking}")
    
    def set_agent_generating(self, is_generating: bool) -> None:
        """
        Set whether the agent is currently generating text/audio
        
        Args:
            is_generating: True if agent is actively generating content
        """
        old_state = self.state.agent_is_generating
        self.state.agent_is_generating = is_generating
        self.state.update_speaking_state(generating=is_generating, playing=self.state.audio_is_playing)
        
        if old_state != is_generating:
            logger.info(f"Agent generating state changed: {old_state} -> {is_generating}")
    
    def set_audio_playing(self, is_playing: bool) -> None:
        """
        Set whether audio is currently being played
        
        Args:
            is_playing: True if audio playback is in progress
        """
        old_state = self.state.audio_is_playing
        self.state.audio_is_playing = is_playing
        self.state.update_speaking_state(generating=self.state.agent_is_generating, playing=is_playing)
        
        if old_state != is_playing:
            logger.info(f"Audio playing state changed: {old_state} -> {is_playing}")
    
    def _is_backchannel_word(self, text: str) -> bool:
        """Check if text is a backchannel word"""
        normalized = self.config.normalize(text)
        is_backchannel = normalized in self.config.backchannel_words
        
        if is_backchannel:
            logger.debug(f"Identified backchannel word: '{text}'")
        
        return is_backchannel
    
    def _is_interrupt_command(self, text: str) -> bool:
        """Check if text is an interrupt command"""
        normalized = self.config.normalize(text)
        
        # Check direct match
        is_interrupt = normalized in self.config.interrupt_commands
        
        # If not found, check if it's contained in the text (for multi-word commands)
        if not is_interrupt:
            for command in self.config.interrupt_commands:
                if command in normalized:
                    is_interrupt = True
                    break
        
        if is_interrupt:
            logger.debug(f"Identified interrupt command: '{text}'")
        
        return is_interrupt
    
    def process_user_input(self, transcript: str) -> InterruptionType:
        """
        Process user input and determine the interruption type
        
        Logic Matrix:
        ┌──────────────────────┬─────────────────┬──────────────────┐
        │ User Input           │ Agent State     │ Desired Behavior │
        ├──────────────────────┼─────────────────┼──────────────────┤
        │ Backchannel (yeah)   │ Agent Speaking  │ IGNORE           │
        │ Backchannel (yeah)   │ Agent Silent    │ RESPOND          │
        │ Interrupt (wait)     │ Agent Speaking  │ INTERRUPT        │
        │ Interrupt (wait)     │ Agent Silent    │ INTERRUPT        │
        │ Normal speech        │ Any             │ RESPOND          │
        └──────────────────────┴─────────────────┴──────────────────┘
        
        Args:
            transcript: The user's speech transcript
        
        Returns:
            InterruptionType indicating how to handle the input
        """
        if not self.config.enabled:
            logger.debug("Interruption handler disabled, returning RESPOND")
            return InterruptionType.RESPOND
        
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided")
            return InterruptionType.RESPOND
        
        logger.info(
            f"Processing input: '{transcript}' | Agent speaking: {self.state.agent_is_speaking}"
        )
        
        # First, check for interrupt commands - these always interrupt
        if self._is_interrupt_command(transcript):
            logger.info(f"Interrupt command detected: '{transcript}'")
            return InterruptionType.INTERRUPT
        
        # Check if it's a backchannel word
        if self._is_backchannel_word(transcript):
            # If agent is speaking, ignore it (passive acknowledgment)
            if self.state.agent_is_speaking:
                logger.info(f"Backchannel word while agent speaking, ignoring: '{transcript}'")
                return InterruptionType.IGNORE
            else:
                # If agent is silent, treat it as valid input
                logger.info(f"Backchannel word while agent silent, responding: '{transcript}'")
                return InterruptionType.RESPOND
        
        # Normal speech - always respond
        logger.info(f"Normal speech detected, responding: '{transcript}'")
        return InterruptionType.RESPOND
    
    def handle_interruption(self, transcript: str) -> bool:
        """
        Handle user interruption and execute appropriate callbacks
        
        Args:
            transcript: The user's speech transcript
        
        Returns:
            True if the input should interrupt the agent, False otherwise
        """
        interruption_type = self.process_user_input(transcript)
        
        if interruption_type == InterruptionType.INTERRUPT:
            logger.warning(f"INTERRUPT triggered for: '{transcript}'")
            for callback in self._callbacks:
                try:
                    callback(transcript)
                except Exception as e:
                    logger.error(f"Error executing interrupt callback: {e}")
            return True
        
        if interruption_type == InterruptionType.IGNORE:
            logger.debug(f"IGNORE: '{transcript}'")
            return False
        
        # RESPOND
        logger.debug(f"RESPOND: '{transcript}'")
        return False
    
    def get_state(self) -> InterruptionState:
        """Get the current interruption state"""
        return self.state
    
    def reset(self) -> None:
        """Reset the handler to initial state"""
        self.state = InterruptionState()
        logger.info("Interruption handler reset to initial state")
