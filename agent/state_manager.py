"""
Agent State Manager - Tracks agent speaking state and manages interruption events
"""
import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AgentState(Enum):
    """Possible states for the agent"""
    IDLE = "idle"
    SPEAKING = "speaking"
    LISTENING = "listening"
    PROCESSING = "processing"


@dataclass
class InterruptionEvent:
    """
    Represents a potential interruption event.
    Tracks the lifecycle from VAD detection to STT completion to final decision.
    """
    text: str
    timestamp: float
    vad_triggered: bool = False
    stt_completed: bool = False
    should_interrupt: Optional[bool] = None


class AgentStateManager:
    """
    Manages the agent's speaking state and tracks interruption events.
    Thread-safe using asyncio locks.
    """
    
    def __init__(self):
        self.state = AgentState.IDLE
        self.is_speaking = False
        self.speech_start_time: Optional[float] = None
        self.speech_end_time: Optional[float] = None
        self.last_interruption_time: Optional[float] = None
        self.pending_interruptions: Dict[str, InterruptionEvent] = {}
        self._lock = asyncio.Lock()
        self._speech_task: Optional[asyncio.Task] = None
    
    async def on_agent_speech_start(self):
        """
        Called when agent starts generating or playing audio.
        This is critical for the interruption logic to work correctly.
        """
        async with self._lock:
            self.is_speaking = True
            self.state = AgentState.SPEAKING
            self.speech_start_time = time.time()
            print(f"[STATE] 🗣️  Agent started speaking at {self.speech_start_time:.3f}")
    
    async def on_agent_speech_end(self):
        """
        Called when agent finishes speaking.
        Transitions agent back to IDLE state.
        """
        async with self._lock:
            self.is_speaking = False
            self.state = AgentState.IDLE
            self.speech_end_time = time.time()
            
            if self.speech_start_time:
                duration = self.speech_end_time - self.speech_start_time
                print(f"[STATE] 🔇 Agent stopped speaking (duration: {duration:.3f}s)")
            else:
                print(f"[STATE] 🔇 Agent stopped speaking")
    
    async def on_agent_listening(self):
        """Called when agent is actively listening for user input"""
        async with self._lock:
            if not self.is_speaking:
                self.state = AgentState.LISTENING
                print(f"[STATE] 👂 Agent listening")
    
    async def on_agent_processing(self):
        """Called when agent is processing user input (thinking)"""
        async with self._lock:
            if not self.is_speaking:
                self.state = AgentState.PROCESSING
                print(f"[STATE] 🤔 Agent processing")
    
    async def register_potential_interruption(self, event_id: str, text: str = ""):
        """
        Called when VAD detects user speech.
        Registers a new interruption event for tracking.
        
        Args:
            event_id: Unique identifier for this interruption
            text: Initial text (usually empty until STT completes)
        """
        async with self._lock:
            event = InterruptionEvent(
                text=text,
                timestamp=time.time(),
                vad_triggered=True
            )
            self.pending_interruptions[event_id] = event
            print(f"[STATE] 🎤 Registered potential interruption: {event_id}")
    
    async def update_interruption_text(self, event_id: str, text: str):
        """
        Called when STT provides transcription for an interruption event.
        
        Args:
            event_id: The interruption event to update
            text: Transcribed text from STT
        """
        async with self._lock:
            if event_id in self.pending_interruptions:
                self.pending_interruptions[event_id].text = text
                self.pending_interruptions[event_id].stt_completed = True
                print(f"[STATE] 📝 Updated interruption {event_id} with text: '{text}'")
            else:
                print(f"[STATE] ⚠️  Warning: Event {event_id} not found for text update")
    
    async def resolve_interruption(self, event_id: str, should_interrupt: bool) -> bool:
        """
        Make final decision on whether to interrupt.
        Cleans up the interruption event after resolution.
        
        Args:
            event_id: The interruption event to resolve
            should_interrupt: Final decision on whether to interrupt
            
        Returns:
            The should_interrupt value (for convenience)
        """
        async with self._lock:
            if event_id in self.pending_interruptions:
                event = self.pending_interruptions[event_id]
                event.should_interrupt = should_interrupt
                
                if should_interrupt:
                    self.last_interruption_time = time.time()
                    print(f"[STATE] ⛔ Resolved {event_id}: INTERRUPT (text: '{event.text}')")
                else:
                    print(f"[STATE] ✅ Resolved {event_id}: IGNORE (text: '{event.text}')")
                
                # Clean up the event
                del self.pending_interruptions[event_id]
                
                return should_interrupt
            else:
                print(f"[STATE] ⚠️  Warning: Event {event_id} not found for resolution")
                return False
    
    async def cleanup_stale_interruptions(self, max_age_seconds: float = 2.0):
        """
        Clean up interruption events that are too old.
        This prevents memory leaks from events that never completed.
        
        Args:
            max_age_seconds: Maximum age before an event is considered stale
        """
        async with self._lock:
            current_time = time.time()
            stale_events = [
                event_id for event_id, event in self.pending_interruptions.items()
                if current_time - event.timestamp > max_age_seconds
            ]
            
            for event_id in stale_events:
                print(f"[STATE] 🧹 Cleaning up stale event: {event_id}")
                del self.pending_interruptions[event_id]
    
    def get_state_info(self) -> Dict[str, Any]:
        """
        Get current state information for debugging and monitoring.
        
        Returns:
            Dictionary with current state details
        """
        info = {
            "state": self.state.value,
            "is_speaking": self.is_speaking,
            "pending_interruptions": len(self.pending_interruptions),
        }
        
        if self.speech_start_time:
            if self.is_speaking:
                info["speech_duration"] = time.time() - self.speech_start_time
            elif self.speech_end_time:
                info["last_speech_duration"] = self.speech_end_time - self.speech_start_time
        
        if self.last_interruption_time:
            info["time_since_last_interruption"] = time.time() - self.last_interruption_time
        
        return info
    
    async def force_stop_speaking(self):
        """
        Emergency stop for agent speech.
        Called when a valid interruption is detected.
        """
        async with self._lock:
            if self.is_speaking:
                print(f"[STATE] 🛑 Force stopping agent speech")
                self.is_speaking = False
                self.state = AgentState.LISTENING
                self.speech_end_time = time.time()
                
                # Cancel speech task if it exists
                if self._speech_task and not self._speech_task.done():
                    self._speech_task.cancel()
    
    def is_within_cooldown(self, cooldown_seconds: float) -> bool:
        """
        Check if we're within the cooldown period after last interruption.
        Prevents rapid-fire interruptions.
        
        Args:
            cooldown_seconds: Cooldown period in seconds
            
        Returns:
            True if within cooldown, False otherwise
        """
        if self.last_interruption_time is None:
            return False
        
        return (time.time() - self.last_interruption_time) < cooldown_seconds
