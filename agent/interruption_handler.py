"""
Intelligent Interruption Handler - Core logic for context-aware interruption decisions
"""
import asyncio
import uuid
from typing import Optional
from config.interruption_config import InterruptionConfig
from agent.state_manager import AgentStateManager


class IntelligentInterruptionHandler:
    """
    Handles intelligent interruption decisions based on context.
    
    This is the core component that implements the logic matrix:
    - Backchannel + Speaking = Ignore
    - Command + Speaking = Interrupt
    - Any input + Silent = Process
    """
    
    def __init__(
        self, 
        state_manager: AgentStateManager, 
        config: Optional[InterruptionConfig] = None
    ):
        """
        Initialize the handler.
        
        Args:
            state_manager: Agent state manager instance
            config: Configuration object (uses default if not provided)
        """
        self.state_manager = state_manager
        self.config = config or InterruptionConfig()
        self.stt_grace_tasks = {}
        self.event_callbacks = {}
        
        print(f"[HANDLER] 🚀 Initialized with {len(self.config.BACKCHANNEL_WORDS)} backchannel words")
        print(f"[HANDLER] 🚀 Monitoring {len(self.config.COMMAND_WORDS)} command words")
    
    async def on_user_speech_detected(self, callback=None) -> str:
        """
        Called when VAD detects user started speaking.
        This happens BEFORE we have transcription.
        
        Args:
            callback: Optional callback to run when interruption is resolved
        
        Returns:
            event_id: Unique identifier for this interruption event
        """
        event_id = str(uuid.uuid4())
        
        # Register the interruption
        await self.state_manager.register_potential_interruption(event_id)
        
        # Store callback if provided
        if callback:
            self.event_callbacks[event_id] = callback
        
        # Start grace period timer for STT
        task = asyncio.create_task(
            self._wait_for_stt_with_timeout(event_id)
        )
        self.stt_grace_tasks[event_id] = task
        
        print(f"[HANDLER] 🎧 User speech detected, waiting for transcription... (event: {event_id[:8]})")
        
        return event_id
    
    async def on_user_speech_transcribed(self, event_id: str, text: str) -> bool:
        """
        Called when STT provides transcription for user speech.
        This is where the intelligent decision happens.
        
        Args:
            event_id: The interruption event identifier
            text: Transcribed text from STT
        
        Returns:
            should_interrupt: True if agent should stop speaking, False to ignore
        """
        # Update the state manager with the text
        await self.state_manager.update_interruption_text(event_id, text)
        
        # Get current agent state
        is_agent_speaking = self.state_manager.is_speaking
        
        # Make the intelligent decision
        should_interrupt = self.config.should_interrupt(text, is_agent_speaking)
        
        # Log the decision with context
        if is_agent_speaking:
            if should_interrupt:
                print(f"[HANDLER] ⛔ INTERRUPT: '{text}' (agent was speaking)")
            else:
                print(f"[HANDLER] ✅ IGNORE: '{text}' (backchannel, agent still speaking)")
        else:
            print(f"[HANDLER] 💬 PROCESS: '{text}' (agent was silent)")
        
        # Resolve the interruption in state manager
        await self.state_manager.resolve_interruption(event_id, should_interrupt)
        
        # Cancel grace period task if still running
        if event_id in self.stt_grace_tasks:
            task = self.stt_grace_tasks[event_id]
            if not task.done():
                task.cancel()
            del self.stt_grace_tasks[event_id]
        
        # Execute callback if provided
        if event_id in self.event_callbacks:
            callback = self.event_callbacks[event_id]
            await callback(should_interrupt, text)
            del self.event_callbacks[event_id]
        
        return should_interrupt
    
    async def _wait_for_stt_with_timeout(self, event_id: str):
        """
        Wait for STT transcription with timeout.
        If STT takes too long, make best-effort decision.
        
        Args:
            event_id: The interruption event identifier
        """
        try:
            # Wait for STT to complete
            await asyncio.sleep(self.config.STT_GRACE_PERIOD)
            
            # If we reach here, STT took too long (timeout)
            print(f"[HANDLER] ⏰ STT timeout for event {event_id[:8]}")
            
            # Check if we still have this event pending
            if event_id in self.state_manager.pending_interruptions:
                event = self.state_manager.pending_interruptions[event_id]
                
                if not event.stt_completed:
                    # No transcription yet - make fallback decision
                    # If agent is speaking, assume backchannel and ignore
                    # If agent is silent, process as valid input
                    should_interrupt = not self.state_manager.is_speaking
                    
                    print(f"[HANDLER] 🤷 No transcription, defaulting to interrupt={should_interrupt}")
                    
                    await self.state_manager.resolve_interruption(event_id, should_interrupt)
                    
                    # Execute callback if provided
                    if event_id in self.event_callbacks:
                        callback = self.event_callbacks[event_id]
                        await callback(should_interrupt, "")
                        del self.event_callbacks[event_id]
        
        except asyncio.CancelledError:
            # Normal case - STT completed before timeout
            print(f"[HANDLER] ✓ STT completed before timeout for {event_id[:8]}")
            pass
        
        except Exception as e:
            print(f"[HANDLER] ❌ Error in grace period handler: {e}")
    
    async def force_interrupt(self, reason: str = "manual"):
        """
        Force an interruption (emergency stop).
        
        Args:
            reason: Reason for the forced interruption
        """
        print(f"[HANDLER] 🚨 Force interrupting agent (reason: {reason})")
        await self.state_manager.force_stop_speaking()
    
    def get_decision_explanation(self, text: str, is_agent_speaking: bool) -> dict:
        """
        Get a detailed explanation of why a decision was made.
        Useful for debugging and understanding the logic.
        
        Args:
            text: User input text
            is_agent_speaking: Whether agent was speaking
        
        Returns:
            Dictionary with decision details
        """
        decision = self.config.should_interrupt(text, is_agent_speaking)
        
        explanation = {
            "text": text,
            "is_agent_speaking": is_agent_speaking,
            "decision": "INTERRUPT" if decision else "IGNORE",
            "reasons": []
        }
        
        if not is_agent_speaking:
            explanation["reasons"].append("Agent was silent - always process input")
        elif self.config.contains_command(text):
            explanation["reasons"].append(f"Contains command word(s)")
        elif self.config.is_backchannel_only(text):
            explanation["reasons"].append("Pure backchannel - ignore during speech")
        else:
            word_count = len(text.strip().split())
            if word_count >= self.config.MIN_WORD_COUNT_FOR_INTENT:
                explanation["reasons"].append(f"Multiple words ({word_count}) - likely has intent")
            else:
                explanation["reasons"].append("Non-backchannel single word - likely intent")
        
        return explanation
    
    async def cleanup(self):
        """
        Clean up resources and cancel pending tasks.
        Call this when shutting down the handler.
        """
        print(f"[HANDLER] 🧹 Cleaning up {len(self.stt_grace_tasks)} pending tasks")
        
        for event_id, task in list(self.stt_grace_tasks.items()):
            if not task.done():
                task.cancel()
        
        self.stt_grace_tasks.clear()
        self.event_callbacks.clear()
        
        await self.state_manager.cleanup_stale_interruptions()
