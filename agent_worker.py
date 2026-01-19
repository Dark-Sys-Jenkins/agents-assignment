import asyncio
import logging
import os
import ssl
import sys
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.plugins import silero
from unittest.mock import MagicMock

# Configure logging
logger = logging.getLogger("kelly-agent")
logger.setLevel(logging.INFO)

# Mock missing dependencies for Google Plugin (STT/TTS not used)
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.speech_v2"] = MagicMock()
sys.modules["google.cloud.speech_v2.types"] = MagicMock()
sys.modules["google.cloud.texttospeech"] = MagicMock()
sys.modules["google.cloud.texttospeech_v1"] = MagicMock()
sys.modules["google.cloud.texttospeech_v1.types"] = MagicMock()

import livekit.plugins.google as google
import livekit.plugins.deepgram as deepgram

# --- SSL BYPASS FOR CORPORATE PROXY ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# ---------------------------------------

load_dotenv()

# Create the AgentServer
server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm function to load VAD model once"""
    logger.info("Prewarming: Loading Silero VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Prewarm complete")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entrypoint for the LiveKit agent worker"""
    logger.info(f"Agent connecting to room: {ctx.room.name}")
    
    # Validate required environment variables
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not deepgram_key:
        logger.error("DEEPGRAM_API_KEY must be set in .env")
        return
    
    if not gemini_key:
        logger.error("GEMINI_API_KEY must be set in .env")
        return
    
    # Initialize plugins
    logger.info("Initializing Deepgram STT/TTS and Gemini LLM...")
    stt_plugin = deepgram.STT()
    tts_plugin = deepgram.TTS()
    llm_plugin = google.LLM(model="gemini-2.0-flash-001", api_key=gemini_key)
    
    # Create agent
    agent = Agent(
        instructions="You are a helpful voice assistant named Kelly. You are concise and friendly.",
    )
    
    # Create agent session
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin,
        preemptive_generation=False,
        resume_false_interruption=False,
    )
    
    # Start the session
    logger.info("Starting agent session...")
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("Agent session started successfully!")
    
    # Generate initial greeting
    logger.info("Generating initial greeting...")
    session.history.add_message(role="user", content="Please introduce yourself concisely.")
    session.generate_reply()
    
    logger.info("Agent is now active and listening!")


if __name__ == "__main__":
    # Validate environment variables before starting
    if not os.getenv("LIVEKIT_API_KEY"):
        logger.error("LIVEKIT_API_KEY must be set in .env")
        exit(1)
    
    if not os.getenv("LIVEKIT_API_SECRET"):
        logger.error("LIVEKIT_API_SECRET must be set in .env")
        exit(1)
    
    if not os.getenv("LIVEKIT_URL"):
        logger.error("LIVEKIT_URL must be set in .env")
        exit(1)
    
    if not os.getenv("DEEPGRAM_API_KEY"):
        logger.error("DEEPGRAM_API_KEY must be set in .env")
        exit(1)
    
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY must be set in .env")
        exit(1)
    
    logger.info("Starting LiveKit Agent Worker...")
    cli.run_app(server)
