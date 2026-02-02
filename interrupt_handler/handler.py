"""
Core interruption handling logic.
Manages agent state and decides when to interrupt.
"""

import logging
import time
from typing import Optional
from .config import InterruptionConfig, default_config
from .utils import classify_utterance, format_transcript_for_display


logger = logging.getLogger(__name__)


class InterruptionHandler:
    """
    Intelligent interruption handler for LiveKit agents.
    
    Implements the logic matrix:
    - Agent speaking + filler only → IGNORE
    - Agent speaking + interrupt word → INTERRUPT
    - Agent speaking + other content → INTERRUPT
    - Agent silent + any input → ALLOW (normal processing)
    """
    
    def __init__(self, config: Optional[InterruptionConfig] = None):
        """
        Initialize the handler.
        
        Args:
            config: InterruptionConfig instance. Uses default if None.
        """
        self.config = config or default_config
        
        # State tracking
        self._agent_is_speaking = False
        self._current_speech_handle = None
        
        # Statistics (for debugging/monitoring)
        self.stats = {
            'total_transcripts': 0,
            'ignored_fillers': 0,
            'processed_interrupts': 0,
            'processed_normal': 0,
            'empty_inputs': 0,
        }
        
        # Setup logging
        if self.config.debug:
            logger.setLevel(logging.DEBUG)
            if not logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(
                    '[%(asctime)s] [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S'
                ))
                logger.addHandler(handler)
        
        logger.info(f"InterruptionHandler initialized with {self.config}")
    
    def on_agent_speech_started(self, speech_handle=None):
        """
        Called when agent starts speaking.
        
        Args:
            speech_handle: Optional speech handle from LiveKit
        """
        self._agent_is_speaking = True
        self._current_speech_handle = speech_handle
        
        if self.config.debug:
            logger.debug("[SPEAKING] Agent started speaking")
    
    def on_agent_speech_ended(self):
        """Called when agent stops speaking."""
        self._agent_is_speaking = False
        self._current_speech_handle = None
        
        if self.config.debug:
            logger.debug("[SILENT] Agent stopped speaking")
    
    def is_agent_speaking(self) -> bool:
        """
        Check if agent is currently speaking.
        
        Returns:
            True if agent is speaking
        """
        return self._agent_is_speaking
    
    def should_interrupt(self, transcript: str, is_final: bool = True) -> bool:
        """
        Determine if the agent should be interrupted based on transcript.
        
        This is the CORE LOGIC of the system.
        
        Args:
            transcript: User's speech transcript
            is_final: Whether this is a final transcript (not partial)
            
        Returns:
            True if agent should be interrupted, False to ignore
        """
        start_time = time.perf_counter()  # For latency measurement
        
        self.stats['total_transcripts'] += 1
        
        # Only process final transcripts unless configured otherwise
        if not is_final and not self.config.use_partial_transcripts:
            if self.config.debug:
                logger.debug(f"[SKIP] Partial transcript: {format_transcript_for_display(transcript)}")
            return False
        
        # Handle empty or whitespace-only input
        if not transcript or not transcript.strip():
            if self.config.debug:
                logger.debug("[SKIP] Empty transcript, ignoring")
            self.stats['empty_inputs'] += 1
            return False
        
        # Classify the utterance
        classification = classify_utterance(
            transcript,
            self.config.filler_words,
            self.config.interrupt_words
        )
        
        # Check agent state
        agent_speaking = self.is_agent_speaking()
        
        # Log classification
        if self.config.debug:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"📝 Transcript: {format_transcript_for_display(transcript)} | "
                f"Classification: {classification} | "
                f"Agent speaking: {agent_speaking} | "
                f"Latency: {elapsed_ms:.2f}ms"
            )
        
        # ============================================================
        # DECISION LOGIC MATRIX (CORE ALGORITHM)
        # ============================================================
        
        # CASE 1: Agent is NOT speaking (silent/listening)
        # → Allow ALL input to be processed normally
        if not agent_speaking:
            if self.config.debug:
                logger.debug(
                    f"✅ Agent silent - processing input normally "
                    f"(classification: {classification})"
                )
            self.stats['processed_normal'] += 1
            return True  # "Interrupt" (but agent isn't speaking, so it's normal input)
        
        # CASE 2: Agent IS speaking
        # Now we need to filter based on content
        
        if classification == 'EMPTY':
            # Empty input - ignore
            if self.config.debug:
                logger.debug("[SKIP] Empty utterance while agent speaking - ignoring")
            self.stats['empty_inputs'] += 1
            return False
        
        elif classification == 'FILLER':
            # Pure filler words - IGNORE completely
            if self.config.debug:
                logger.debug(
                    f"[IGNORE] Filler words while agent speaking: {format_transcript_for_display(transcript)}"
                )
            self.stats['ignored_fillers'] += 1
            return False  # Do NOT interrupt
        
        elif classification == 'INTERRUPT':
            # Contains interrupt/command words - STOP immediately
            if self.config.debug:
                logger.debug(
                    f"[INTERRUPT] Command detected while agent speaking: {format_transcript_for_display(transcript)}"
                )
            self.stats['processed_interrupts'] += 1
            return True  # Interrupt now
        
        elif classification in ['MIXED', 'UNKNOWN']:
            # Mixed content or unknown words
            # User wants to say something substantial - interrupt
            if self.config.debug:
                logger.debug(
                    f"[INTERRUPT] Non-filler content while agent speaking: {format_transcript_for_display(transcript)}"
                )
            self.stats['processed_interrupts'] += 1
            return True  # Interrupt
        
        # Fallback (should never reach here)
        if self.config.debug:
            logger.warning(
                f"[WARN] Unexpected classification: {classification} for {format_transcript_for_display(transcript)}"
            )
        return True  # Default to interrupting for safety
    
    def get_stats(self) -> dict:
        """Get handler statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            'total_transcripts': 0,
            'ignored_fillers': 0,
            'processed_interrupts': 0,
            'processed_normal': 0,
            'empty_inputs': 0,
        }
        if self.config.debug:
            logger.info("📊 Statistics reset")
    
    def print_stats(self):
        """Print current statistics."""
        print("\n" + "="*60)
        print("INTERRUPTION HANDLER STATISTICS")
        print("="*60)
        for key, value in self.stats.items():
            print(f"{key:.<30} {value:>10}")
        print("="*60 + "\n")
