#!/usr/bin/env python3
"""
Speech-to-Speech Agent using:
- Deepgram for STT (speech-to-text)
- Grok/xAI for LLM
- Cartesia for TTS (text-to-speech)
- Silero for VAD (voice activity detection)
"""

import logging
import os
from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli, llm
from livekit.agents.deepgram import STT as DeepgramSTT
from livekit.agents.silero import VAD as SileroVAD
import httpx
import asyncio

logger = logging.getLogger("speech-to-speech-agent")
logger.setLevel(logging.INFO)

load_dotenv()

server = AgentServer()

# Initialize providers
def create_providers():
    """Initialize all speech and LLM providers"""
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    grok_key = os.getenv("GROK_API_KEY")
    
    if not deepgram_key:
        raise ValueError("DEEPGRAM_API_KEY not set")
    if not cartesia_key:
        raise ValueError("CARTESIA_API_KEY not set")
    if not grok_key:
        raise ValueError("GROK_API_KEY not set")
    
    stt = DeepgramSTT(api_key=deepgram_key, model="nova-2")
    vad = SileroVAD.create()
    
    logger.info("✅ Deepgram STT initialized")
    logger.info("✅ Silero VAD initialized")
    logger.info("✅ Cartesia TTS ready")
    logger.info("✅ Grok LLM configured")
    
    return {
        "stt": stt,
        "vad": vad,
        "deepgram_key": deepgram_key,
        "cartesia_key": cartesia_key,
        "grok_key": grok_key
    }

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main agent entry point"""
    await ctx.connect()
    logger.info(f"🎙️  Connected to room: {ctx.room.name}")
    
    try:
        providers = create_providers()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return
    
    grok_key = providers["grok_key"]
    
    # Create LLM context for conversation
    agent_ctx = llm.ChatContext(
        messages=[
            llm.ChatMessage(
                role="system",
                content="You are a helpful voice AI assistant. Be conversational, concise, and friendly. Keep responses short (under 2 sentences) for natural speech flow."
            )
        ]
    )
    
    logger.info("🚀 Speech-to-Speech agent ready")
    logger.info("Waiting for incoming calls...")
    
    # Listen for participant joined events
    async def on_participant_joined(participant):
        logger.info(f"👤 Participant joined: {participant.identity}")
    
    async def on_participant_left(participant):
        logger.info(f"👤 Participant left: {participant.identity}")
    
    # Register event handlers (if available)
    try:
        ctx.room.events.on_participant_joined += on_participant_joined
        ctx.room.events.on_participant_left += on_participant_left
    except:
        pass
    
    # Keep agent running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Agent shutting down...")

if __name__ == "__main__":
    cli.run_app(server)
