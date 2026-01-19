"""
LiveKit Intelligent Interruption Handler - NO EXTERNAL APIs
Uses only local models and LiveKit's built-in functionality

Author: Parth
"""

import asyncio
import logging
from typing import Set, Optional
from dataclasses import dataclass

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    tokenize,
)
from livekit.plugins import silero

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class InterruptionConfig:
    """Configuration for interruption detection"""
    
    # Passive acknowledgements to ignore while speaking
    PASSIVE_WORDS: Set[str] = None
    
    # Words that trigger immediate interruption
    INTERRUPT_WORDS: Set[str] = None
    
    def __post_init__(self):
        if self.PASSIVE_WORDS is None:
            self.PASSIVE_WORDS = {
                'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right',
                'aha', 'mhm', 'yep', 'yup', 'mm-hmm', 'uhuh',
                'yes', 'sure', 'gotcha', 'alright', 'cool'
            }
        
        if self.INTERRUPT_WORDS is None:
            self.INTERRUPT_WORDS = {
                'wait', 'stop', 'no', 'hold', 'pause', 'but',
                'however', 'actually', 'interrupt'
            }


class IntelligentInterruptionAgent:
    """
    Voice agent with intelligent interruption handling
    No external APIs - uses only local STT and TTS
    """
    
    def __init__(self, ctx: JobContext, config: Optional[InterruptionConfig] = None):
        self.ctx = ctx
        self.config = config or InterruptionConfig()
        
        # State tracking
        self.is_agent_speaking = False
        self.current_speech_task: Optional[asyncio.Task] = None
        
        # Components (local only)
        self.vad = silero.VAD.load()  # Local VAD
        self.room = None
        self.participant = None
        
    async def start(self):
        """Initialize and start the agent"""
        logger.info("🚀 Starting Intelligent Interruption Agent (No External APIs)")
        
        # Connect to room
        await self.ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        self.room = self.ctx.room
        
        # Set up event handlers
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("participant_connected", self._on_participant_connected)
        
        logger.info("✅ Agent started and ready")
        
        # Greet user
        await self._speak("Hello! I'm an intelligent voice assistant. I can continue speaking even when you say 'yeah' or 'ok', but I'll stop if you say 'wait' or 'stop'. What would you like to talk about?")
    
    def _on_participant_connected(self, participant):
        """Handle new participant"""
        logger.info(f"👤 Participant connected: {participant.identity}")
        self.participant = participant
    
    def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle subscribed audio track"""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎤 Audio track subscribed from {participant.identity}")
            asyncio.create_task(self._process_audio_track(track, participant))
    
    async def _process_audio_track(self, track: rtc.AudioTrack, participant: rtc.RemoteParticipant):
        """Process incoming audio with VAD and simple STT"""
        
        audio_stream = rtc.AudioStream(track)
        
        async for event in self.vad.stream():
            if event.type == silero.VADEventType.START_OF_SPEECH:
                logger.info("🎙️ User started speaking")
                
            elif event.type == silero.VADEventType.END_OF_SPEECH:
                logger.info("🎙️ User stopped speaking")
                
                # Get the audio frames
                frames = event.frames
                
                # Simple transcription using pattern matching
                # In production, you'd use local Whisper or similar
                transcription = await self._simple_transcribe(frames)
                
                if transcription:
                    await self._handle_user_input(transcription)
    
    async def _simple_transcribe(self, frames) -> str:
        """
        Simple local transcription placeholder
        
        In real implementation, integrate:
        - Whisper.cpp (local)
        - Vosk (local)
        - Or any other local STT
        
        For demo purposes, we'll simulate with predefined patterns
        """
        # This is a placeholder - in real implementation, use local Whisper
        # Example: whisper.transcribe(frames)
        
        # For testing, return empty (you'll type responses)
        return ""
    
    async def _handle_user_input(self, text: str):
        """
        Intelligently handle user input based on agent state
        
        Core Logic:
        1. Agent speaking + passive word only -> IGNORE
        2. Agent speaking + interrupt word -> STOP & PROCESS
        3. Agent silent -> PROCESS all input
        """
        
        if not text.strip():
            return
        
        text_lower = text.lower().strip()
        logger.info(f"📝 Transcription: '{text}' | Agent speaking: {self.is_agent_speaking}")
        
        # Split into words
        words = set(text_lower.split())
        
        if self.is_agent_speaking:
            # Check for interrupt words
            has_interrupt = bool(words & self.config.INTERRUPT_WORDS)
            
            if has_interrupt:
                logger.info(f"⛔ INTERRUPT detected: '{text}' - Stopping agent")
                await self._stop_speaking()
                await self._process_input(text)
                return
            
            # Check if only passive words
            non_empty_words = [w for w in words if w]
            is_all_passive = all(
                word in self.config.PASSIVE_WORDS 
                for word in non_empty_words
            )
            
            if is_all_passive:
                logger.info(f"⏭️ IGNORED: '{text}' - Passive acknowledgement while speaking")
                return
            
            # Mixed input - has non-passive content
            logger.info(f"⛔ INTERRUPT (mixed): '{text}' - Stopping agent")
            await self._stop_speaking()
            await self._process_input(text)
        else:
            # Agent is silent - process everything
            logger.info(f"✅ PROCESSING: '{text}' - Agent is silent")
            await self._process_input(text)
    
    async def _process_input(self, text: str):
        """Process user input and generate response"""
        
        # Simple response logic without external LLM
        response = self._generate_local_response(text)
        await self._speak(response)
    
    def _generate_local_response(self, text: str) -> str:
        """
        Generate response locally without external LLM
        
        Simple rule-based responses for demo
        In production, use local LLM like:
        - llama.cpp
        - GPT4All
        - ONNX models
        """
        
        text_lower = text.lower()
        
        # Simple pattern matching
        if any(word in text_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! How can I help you today?"
        
        elif any(word in text_lower for word in ['weather', 'temperature']):
            return "I'd be happy to tell you about the weather. It's a beautiful day with clear skies and comfortable temperatures around 72 degrees Fahrenheit."
        
        elif any(word in text_lower for word in ['ai', 'artificial intelligence']):
            return "Artificial intelligence is fascinating! It refers to computer systems that can perform tasks that typically require human intelligence, such as visual perception, speech recognition, decision-making, and language translation. AI has made tremendous progress in recent years."
        
        elif any(word in text_lower for word in ['space', 'universe', 'stars']):
            return "Space exploration is truly amazing. The universe is vast beyond comprehension, containing billions of galaxies, each with billions of stars. Our own galaxy, the Milky Way, is just one of these countless galaxies."
        
        elif any(word in text_lower for word in ['ocean', 'sea', 'water']):
            return "The ocean covers about 71% of Earth's surface and contains 97% of Earth's water. Oceans are home to incredibly diverse ecosystems and play a crucial role in regulating our planet's climate and weather patterns."
        
        elif any(word in text_lower for word in ['tell', 'explain', 'about']):
            return "I'd be happy to explain! Let me give you a detailed overview. This topic has many interesting aspects to explore, and I can break it down into several key points to help you understand it better."
        
        else:
            return "That's an interesting question! Let me think about that. Based on what you've asked, I can provide you with some information and perspectives on this topic."
    
    async def _speak(self, text: str):
        """
        Speak text using local TTS
        
        Uses simple audio synthesis without external APIs
        """
        
        logger.info(f"🔊 Agent speaking: '{text[:50]}...'")
        self.is_agent_speaking = True
        
        # Create audio source
        # In production, use local TTS like:
        # - piper-tts (local neural TTS)
        # - espeak (simple TTS)
        # - festival (local TTS)
        
        try:
            # Simulate speaking with delay (replace with actual TTS)
            words = text.split()
            duration = len(words) * 0.5  # Rough estimate
            
            # Create task for speaking
            self.current_speech_task = asyncio.create_task(
                self._simulate_speech(text, duration)
            )
            
            await self.current_speech_task
            
        except asyncio.CancelledError:
            logger.info("🛑 Speech cancelled (interrupted)")
        finally:
            self.is_agent_speaking = False
            self.current_speech_task = None
            logger.info("🔇 Agent finished speaking")
    
    async def _simulate_speech(self, text: str, duration: float):
        """
        Simulate speech for demo
        In production, replace with actual local TTS audio output
        """
        logger.info(f"Speaking: {text}")
        await asyncio.sleep(duration)
    
    async def _stop_speaking(self):
        """Stop current speech immediately"""
        if self.current_speech_task and not self.current_speech_task.done():
            logger.info("🛑 Stopping current speech")
            self.current_speech_task.cancel()
            try:
                await self.current_speech_task
            except asyncio.CancelledError:
                pass
        self.is_agent_speaking = False


async def entrypoint(ctx: JobContext):
    """Main entry point for the agent"""
    
    config = InterruptionConfig()
    agent = IntelligentInterruptionAgent(ctx, config)
    
    await agent.start()
    
    # Keep running
    await asyncio.sleep(3600)  # Run for 1 hour


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
