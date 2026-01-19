# exmaples/smart_interruption_session.py
from __future__ import annotations

import asyncio
import logging
import time
import uuid
import os
from typing import Dict, Any, Optional

# NOTE: This imports internal classes. Ensure compatibility with LiveKit SDK version.
from livekit.agents.voice.agent_activity import AgentActivity
from livekit.agents.voice.agent_session import AgentSession
from livekit.agents.stt import SpeechEvent, SpeechEventType

logger = logging.getLogger("smart-agent-activity")
START_TIME = time.time()

def log_trace(msg: str):
    """Structured logging for verification proof"""
    elapsed = time.time() - START_TIME
    logger.info(f"[{elapsed:06.3f}] {msg}")


class SmartAgentActivity(AgentActivity):
    """
    Custom AgentActivity that buffers VAD events and validates with STT
    before executing interruptions.
    """
    
    def __init__(self, agent, session, handler):
        super().__init__(agent, session)
        self.handler = handler  # InterruptionClassifier instance
        
        # Buffering state
        self.pending_interruptions: Dict[str, Dict[str, Any]] = {}
        self.interruption_lock = asyncio.Lock()
        self.current_speech_start_time: Optional[float] = None
        
        # Configuration
        self.INTERRUPTION_TIMEOUT_MS = int(
            os.getenv('INTERRUPTION_TIMEOUT_MS', '400')
        )
        
        logger.info(f"SmartAgentActivity initialized with buffering (timeout: {self.INTERRUPTION_TIMEOUT_MS}ms)")
    
    # OVERRIDE: on_start_of_speech
    def on_start_of_speech(self, ev) -> None:
        """
        Called when VAD detects speech start. Update state but don't interrupt yet.
        """
        # Track when user started speaking (for correlation)
        self.current_speech_start_time = time.time()
        
        logger.info(f"[VAD] Speech start detected at {self.current_speech_start_time}")
        
        # Call parent to update user state (Sync)
        super().on_start_of_speech(ev)
    
    # OVERRIDE: on_vad_inference_done
    def on_vad_inference_done(self, ev) -> None:
        """
        CRITICAL: This is where interruption normally triggers.
        We intercept here and buffer the event.
        """
        # Check if agent is currently speaking
        agent_speaking = self._is_agent_speaking()
        
        if not agent_speaking:
            # Agent is silent - allow normal interruption behavior
            log_trace("VAD DETECTED")
            log_trace("RESPOND (agent silent)")
            super().on_vad_inference_done(ev)
            return
        
        # Agent IS speaking - buffer this potential interruption
        log_trace(f"VAD DETECTED")
        log_trace(f"AGENT STATE: speaking")
        
        # Offload async buffering to task
        asyncio.create_task(self._buffer_vad_event(ev))
        
        # DO NOT call super() - this prevents the default interruption
    
    async def _buffer_vad_event(self, ev) -> None:
        """Async helper to buffer VAD event safely"""
        interrupt_id = str(uuid.uuid4())
        
        async with self.interruption_lock:
            self.pending_interruptions[interrupt_id] = {
                'id': interrupt_id,
                'vad_event': ev,
                'timestamp': time.time(),
                'speech_start': self.current_speech_start_time,
                'resolved': False,
                'stt_text': None,
            }
        
        log_trace(f"BUFFER: interruption_id={interrupt_id}")
        
        # Start timeout timer
        asyncio.create_task(self._interruption_timeout(interrupt_id))

    # OVERRIDE: on_interim_transcript
    def on_interim_transcript(
        self, 
        ev: SpeechEvent, 
        *,
        speaking: bool | None = None
    ) -> None:
        """
        Interim STT results - use for early keyword detection.
        Matches signature: (self, ev: stt.SpeechEvent, *, speaking: bool | None) -> None
        """
        
        if not self.pending_interruptions:
            # No pending interruptions - normal behavior
            super().on_interim_transcript(ev, speaking=speaking)
            return
        
        # Handle async logic in task
        asyncio.create_task(self._process_interim_transcript(ev, speaking))
    
    async def _process_interim_transcript(self, ev, speaking) -> None:
        """Async helper for interim transcript processing"""
        if not self.pending_interruptions:
            return

        # Get the most recent pending interruption (assumes temporal ordering)
        interrupt_id = max(
            self.pending_interruptions.keys(),
            key=lambda k: self.pending_interruptions[k]['timestamp']
        )
        
        # ev IS the SpeechEvent
        text = ev.alternatives[0].text if ev.alternatives else ""
        
        logger.info(f"[STT-INTERIM] '{text}' for interrupt {interrupt_id[:8]}...")
        
        # Quick check for obvious interrupt keywords
        if self.handler.classifier.has_interrupt_keyword(text):
            logger.info(f"[EARLY-INTERRUPT] Keyword detected in interim: '{text}'")
            await self._execute_interruption(interrupt_id, text, interim=True)
        elif self.handler.classifier.is_pure_backchanneling(text):
            logger.debug(f"[INTERIM] Looks like backchanneling: '{text}' (waiting for final)")
        
        # Don't call super() - we're handling this manually
    
    # OVERRIDE: on_final_transcript
    def on_final_transcript(
        self, 
        ev: SpeechEvent, 
        *,
        speaking: bool | None = None
    ) -> None:
        """
        Final STT result - make the final decision here.
        Matches signature: (self, ev: stt.SpeechEvent, *, speaking: bool | None) -> None
        """
        text = ev.alternatives[0].text if ev.alternatives else ""
        
        if not self.pending_interruptions:
            # No pending interruptions - agent was silent
            log_trace(f"STT FINAL: \"{text}\"")
            super().on_final_transcript(ev, speaking=speaking)
            return
        
        # Handle async decision
        asyncio.create_task(self._process_final_transcript(ev, text))
        
    async def _process_final_transcript(self, ev, text) -> None:
        """Async helper for final transcript decision"""
        if not self.pending_interruptions:
            return

        # Find matching pending interruption (most recent)
        interrupt_id = max(
            self.pending_interruptions.keys(),
            key=lambda k: self.pending_interruptions[k]['timestamp']
        )
        
        logger.info(f"[STT-FINAL] '{text}' for interrupt {interrupt_id[:8]}...")
        
        # CRITICAL DECISION: Should we interrupt?
        should_interrupt = self.handler.classifier.should_interrupt(
            text,
            agent_speaking=True  # We know agent is speaking (we buffered it)
        )
        
        async with self.interruption_lock:
            if interrupt_id not in self.pending_interruptions:
                logger.warning(f"Interrupt {interrupt_id[:8]} already resolved")
                return
            
            pending = self.pending_interruptions[interrupt_id]
            pending['resolved'] = True
            pending['stt_text'] = text
        
        if should_interrupt:
            log_trace(f"STT FINAL: \"{text}\"")
            log_trace(f"CLASSIFIER: interrupt=True")
            log_trace("ACTION: EXECUTE INTERRUPTION")
            await self._execute_interruption(interrupt_id, text)
        else:
            log_trace(f"STT FINAL: \"{text}\"")
            log_trace(f"CLASSIFIER: backchannel=True")
            log_trace("ACTION: IGNORE (no interruption)")
            await self._discard_interruption(interrupt_id)
        
        # Don't call super() - we've handled this manually
    
    # HELPER: Execute Interruption
    async def _execute_interruption(
        self, 
        interrupt_id: str, 
        text: str,
        interim: bool = False
    ) -> None:
        """
        Actually execute the buffered interruption.
        """
        async with self.interruption_lock:
            if interrupt_id not in self.pending_interruptions:
                return
            
            pending = self.pending_interruptions.pop(interrupt_id)
        
        latency = (time.time() - pending['timestamp']) * 1000
        logger.info(
            f"[INTERRUPT-EXECUTE] Stopping agent (latency: {latency:.0f}ms, "
            f"interim: {interim}, text: '{text}')"
        )
        
        # Use the parent class's interruption mechanism
        # Based on research, this method is available in AgentActivity
        if hasattr(self, '_interrupt_by_audio_activity'):
            await self._interrupt_by_audio_activity()
        else:
            # Fallback if method name changed/not found (shouldn't happen based on research)
            logger.warning("_interrupt_by_audio_activity not found, trying manual interrupt")
            if self._current_speech:
                # SpeechHandle.interrupt is async and should be awaited
                if asyncio.iscoroutinefunction(self._current_speech.interrupt):
                     await self._current_speech.interrupt()
                else:
                     self._current_speech.interrupt()
        
        
        # Log metrics
        log_trace("TTS STOPPED")
    
    # HELPER: Discard Interruption
    async def _discard_interruption(self, interrupt_id: str) -> None:
        """
        Discard a buffered interruption (backchanneling).
        """
        async with self.interruption_lock:
            if interrupt_id not in self.pending_interruptions:
                return
            
            pending = self.pending_interruptions.pop(interrupt_id)
        
        latency = (time.time() - pending['timestamp']) * 1000
        logger.info(
            f"[INTERRUPT-DISCARD] Ignoring backchanneling "
            f"(latency: {latency:.0f}ms, text: '{pending.get('stt_text', 'N/A')}')"
        )
        
        log_trace("TTS CONTINUES (no gap)")
    
    # HELPER: Timeout
    async def _interruption_timeout(self, interrupt_id: str) -> None:
        """
        Fallback: if STT doesn't complete in time, execute interruption.
        """
        await asyncio.sleep(self.INTERRUPTION_TIMEOUT_MS / 1000)
        
        async with self.interruption_lock:
            if interrupt_id not in self.pending_interruptions:
                # Already resolved
                return
            
            pending = self.pending_interruptions[interrupt_id]
            
            if pending['resolved']:
                # Resolved by STT, just clean up
                self.pending_interruptions.pop(interrupt_id, None)
                return
            
            # Timeout - execute interruption as fallback
            logger.warning(
                f"[TIMEOUT] STT timeout for {interrupt_id[:8]} after "
                f"{self.INTERRUPTION_TIMEOUT_MS}ms - executing interruption as fallback"
            )
            
            pending['resolved'] = True
        
        await self._execute_interruption(interrupt_id, "[TIMEOUT]")
    
    # HELPER: Check if Agent is Speaking
    def _is_agent_speaking(self) -> bool:
        """
        Check if agent is currently speaking.
        """
        # Check if there's an active speech handle
        if hasattr(self, '_current_speech') and self._current_speech is not None:
            return True
        
        # Check activity state
        if hasattr(self, '_agent_state'):
            return self._agent_state == "speaking"
            
        return False


class SmartInterruptionSession(AgentSession):
    """
    Custom AgentSession that uses SmartAgentActivity for intelligent interruption handling.
    """
    
    def __init__(self, handler, *args, **kwargs):
        self.handler = handler  # Store handler for passing to activity
        super().__init__(*args, **kwargs)
        logger.info("SmartInterruptionSession initialized")
    
    async def _update_activity(self, agent, *args, **kwargs):
        """
        Override to inject SmartAgentActivity.
        
        STRATEGY: Call parent first to handle all the complex logic,
        then swap out the activity if it was just created.
        """
        # Store reference to check if new activity was created
        old_next_activity = self._next_activity
        
        # Call parent to do all the heavy lifting
        await super()._update_activity(agent, *args, **kwargs)
        
        # If parent created a new activity (not resuming), replace it with ours
        if self._next_activity is not old_next_activity:
            if isinstance(self._next_activity, AgentActivity) and not isinstance(self._next_activity, SmartAgentActivity):
                old_activity = self._next_activity
                self._next_activity = SmartAgentActivity(agent, self, self.handler)
                
                #  Clean up the old activity
                if hasattr(old_activity, 'aclose'):
                    await old_activity.aclose()
                
                logger.info("Replaced AgentActivity with SmartAgentActivity")