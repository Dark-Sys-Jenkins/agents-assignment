#!/usr/bin/env python3
"""
Demo Agent for Filler Word Interruption Detection

This agent demonstrates the interruption filter in action:
1. Agent speaking + "yeah/ok/hmm" → Agent continues (IGNORE)
2. Agent silent + "yeah" → Agent responds (PASS_THROUGH)
3. Agent speaking + "no stop" → Agent stops (INTERRUPT)
4. Agent speaking + "yeah okay but wait" → Agent stops (INTERRUPT on "but")
"""

import asyncio
import logging
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents import voice
from livekit.plugins import openai, silero, deepgram

# Load environment variables from .env file
load_dotenv()

# Enable debug logging to see filter decisions
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("demo_agent")


async def entrypoint(ctx: JobContext):
    logger.info("Agent starting, waiting for participant...")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Wait for a participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    # Create the agent session with our interruption filter enabled by default
    session = voice.AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),  # Using Deepgram for STT
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
        # filler_words is None by default, which enables the default filler word list
        # You can customize: filler_words=["yeah", "ok", "hmm", "right"]
    )
    
    # Create the agent with instructions for demo
    agent = voice.Agent(
        instructions="""You are a helpful assistant demonstrating the filler word interruption filter.

When the user asks you to explain something, give a LONG detailed response (at least 3-4 sentences).
This allows them to test saying "yeah", "ok", "hmm" while you're speaking.

If the user says something like "tell me about history" or "explain something long", 
give a detailed multi-sentence explanation so they can test the interruption handling.

Be conversational and friendly!"""
    )
    
    logger.info("Starting agent session...")
    
    # Start the session
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("Agent is ready! Test the interruption filter:")
    logger.info("1. Ask agent to explain something long")
    logger.info("2. Say 'yeah', 'ok', 'hmm' while it speaks → Should continue")
    logger.info("3. When agent is silent, say 'yeah' → Should respond")
    logger.info("4. Say 'stop' or 'wait' while speaking → Should interrupt")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
