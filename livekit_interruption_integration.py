"""
LiveKit Event Loop Integration for Intelligent Interruption Handling

This module patches into LiveKit's VAD and STT event streams to implement
the intelligent interruption logic without modifying the core VAD.
"""

import logging
import asyncio
from typing import Optional, Callable
from livekit.agents import stt, vad as vad_module
from intelligent_interrupt_handler import IntelligentInterruptionHandler

logger = logging.getLogger(__name__)


class InterruptionFilteredSTTStream:
    """
    Wrapper around STT stream that filters interruptions based on agent state.
    This prevents the agent from stopping when hearing backchanneling.
    """
    
    def __init__(
        self, 
        original_stream,
        interrupt_handler: IntelligentInterruptionHandler,
        on_agent_speech_start: Optional[Callable] = None,
        on_agent_speech_end: Optional[Callable] = None
    ):
        self._original_stream = original_stream
        self.interrupt_handler = interrupt_handler
        self._on_agent_speech_start = on_agent_speech_start
        self._on_agent_speech_end = on_agent_speech_end
        self._buffer = []
        self._task: Optional[asyncio.Task] = None
        
    async def __aiter__(self):
        """Async iterator that filters STT events"""
        async for event in self._original_stream:
            # Check if this is a transcription event
            if isinstance(event, stt.SpeechEvent):
                should_process = await self._should_process_event(event)
                
                if should_process:
                    yield event
                else:
                    logger.info(f"Filtered out backchannel event: {event.alternatives[0].text if event.alternatives else 'N/A'}")
            else:
                # Pass through non-transcription events
                yield event
    
    async def _should_process_event(self, event: stt.SpeechEvent) -> bool:
        """
        Determine if an STT event should be processed or filtered out.
        """
        # Extract transcription text
        if not event.alternatives or len(event.alternatives) == 0:
            return True
        
        transcription = event.alternatives[0].text
        is_final = event.is_final
        confidence = event.alternatives[0].confidence if hasattr(event.alternatives[0], 'confidence') else 1.0
        
        # Use the interrupt handler to decide
        should_interrupt = await self.interrupt_handler.should_interrupt(
            transcription=transcription,
            is_final=is_final,
            confidence=confidence
        )
        
        return should_interrupt
    
    def aclose(self):
        """Close the stream"""
        if hasattr(self._original_stream, 'aclose'):
            return self._original_stream.aclose()


class VADInterruptionManager:
    """
    Manages VAD events and coordinates with the interruption handler.
    This sits between VAD and the agent's event processing.
    """
    
    def __init__(self, interrupt_handler: IntelligentInterruptionHandler):
        self.interrupt_handler = interrupt_handler
        self._vad_state = vad_module.VADEventType.END_OF_SPEECH
        
    def handle_vad_event(self, event: vad_module.VADEvent) -> bool:
        """
        Handle a VAD event and determine if it should trigger interruption logic.
        
        Returns:
            True if the event should be processed normally, False if it should be suppressed
        """
        self._vad_state = event.type
        
        # VAD START_OF_SPEECH alone shouldn't interrupt if agent is speaking
        # We'll let the STT determine the actual content
        if event.type == vad_module.VADEventType.START_OF_SPEECH:
            if self.interrupt_handler.is_agent_speaking():
                logger.debug("VAD detected start of speech while agent speaking - waiting for STT confirmation")
                # Don't suppress the VAD event, but the STT filter will handle it
                return True
        
        return True


def wrap_session_with_interruption_filter(session, interrupt_handler: IntelligentInterruptionHandler):
    """
    Wraps a LiveKit AgentSession with interruption filtering.
    This is the main integration point.
    """
    
    # Store original methods
    original_generate_reply = session.generate_reply
    
    async def wrapped_generate_reply(*args, **kwargs):
        """Track when agent is speaking"""
        interrupt_handler.set_agent_speaking_state(True)
        logger.info("🗣️ Agent started generating speech")
        
        try:
            result = await original_generate_reply(*args, **kwargs)
            return result
        finally:
            # Small delay to ensure TTS playback is considered
            await asyncio.sleep(0.1)
            interrupt_handler.set_agent_speaking_state(False)
            logger.info("🔇 Agent finished generating speech")
    
    # Replace the method
    session.generate_reply = wrapped_generate_reply
    
    logger.info("✅ Session wrapped with interruption filter")
    return session


# Monkey-patch helper for deeper integration
def patch_stt_stream_factory(session, interrupt_handler: IntelligentInterruptionHandler):
    """
    This function patches the STT stream creation to wrap it with our filter.
    Use this if you need deeper integration into the LiveKit framework.
    """
    
    if hasattr(session, '_stt'):
        original_stt = session._stt
        
        class FilteredSTT:
            def __init__(self, original):
                self._original = original
                
            def stream(self, *args, **kwargs):
                original_stream = self._original.stream(*args, **kwargs)
                return InterruptionFilteredSTTStream(
                    original_stream=original_stream,
                    interrupt_handler=interrupt_handler
                )
            
            def __getattr__(self, name):
                return getattr(self._original, name)
        
        session._stt = FilteredSTT(original_stt)
        logger.info("✅ STT stream patched with interruption filter")


# Example integration
async def create_interruption_aware_session(
    vad,
    stt,
    llm,
    tts,
    config: Optional[dict] = None
):
    """
    Factory function to create a fully integrated session with interruption handling.
    """
    from livekit.agents import AgentSession
    from intelligent_interrupt_handler import InterruptionConfig
    
    # Create interrupt handler
    interrupt_config = InterruptionConfig(**(config or {}))
    interrupt_handler = IntelligentInterruptionHandler(config=interrupt_config)
    
    # Create session
    session = AgentSession(
        vad=vad,
        stt=stt,
        llm=llm,
        tts=tts
    )
    
    # Wrap with interruption filtering
    wrap_session_with_interruption_filter(session, interrupt_handler)
    
    # Optionally patch STT stream for deeper integration
    patch_stt_stream_factory(session, interrupt_handler)
    
    return session, interrupt_handler