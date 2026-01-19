#!/usr/bin/env python3
"""
Demo agent with Grok LLM + Google STT/TTS + Silero VAD
"""

import logging
import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import llm, tts, stt, vad
from livekit.plugins import groq, google, silero

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize plugins
logger.info("Initializing Grok LLM...")
grok_llm = groq.LLM(model="mixtral-8x7b-32768", api_key=os.getenv("GROK_API_KEY"))

logger.info("Initializing Google STT...")
google_stt = google.STT()

logger.info("Initializing Google TTS...")
google_tts = google.TTS()

logger.info("Initializing Silero VAD...")
silero_vad = silero.VAD.load()

# Create agent with all components
agent = agents.Agent(
    name="grok_agent",
    impl=agents.VoiceAssistantImpl(
        vad=silero_vad,
        stt=google_stt,
        llm=grok_llm,
        tts=google_tts,
    ),
)

# Define agent instructions
SYSTEM_PROMPT = """You are a helpful AI assistant powered by Grok. 
You are concise, helpful, and friendly. 
Keep responses short and natural for voice interaction."""

async def prewarm(proc: agents.JobContext):
    """Prewarm the agent on startup"""
    logger.info("Prewarming agent...")
    await proc.agent.say(
        "Hello! I'm powered by Grok. Ready to chat!",
        allow_interruptions=True,
    )

if __name__ == "__main__":
    logger.info("Starting Grok + Google + Silero demo agent...")
    agents.run_app(agent)
