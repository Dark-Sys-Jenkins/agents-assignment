#!/usr/bin/env python3
"""
Demo Agent for Filler Word Interruption Detection

This agent demonstrates the interruption filter in action:
1. Agent speaking + "yeah/ok/hmm" → Agent continues (IGNORE)
2. Agent silent + "yeah" → Agent responds (PASS_THROUGH)
3. Agent speaking + "no stop" → Agent stops (INTERRUPT)
4. Agent speaking + "yeah okay but wait" → Agent stops (INTERRUPT on "but")
"""

import logging
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents import voice
from livekit.plugins import openai, silero


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_agent")


async def entrypoint(ctx: JobContext):
    logger.info("Connecting to room...")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to room. Waiting for participant...")
    
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    try:
        logger.info("Initializing dependencies...")
        vad_inst = silero.VAD.load()
        stt_inst = openai.STT()  # Using OpenAI Whisper instead of Deepgram

        llm_inst = openai.LLM(model="gpt-4o-mini")
        tts_inst = openai.TTS(voice="alloy")
        logger.info("Dependencies initialized.")

        session = voice.AgentSession(
            vad=vad_inst,
            stt=stt_inst,
            llm=llm_inst,
            tts=tts_inst,
        )
        logger.info("AgentSession created.")
    except Exception as e:
        logger.error(f"Failed to initialize agent dependencies: {e}", exc_info=True)
        raise
    
    agent = voice.Agent(
        instructions="""You are a helpful assistant demonstrating the filler word interruption filter.

When the user asks you to explain something, give a LONG detailed response (at least 3-4 sentences).
This allows them to test saying "yeah", "ok", "hmm" while you're speaking.

Be conversational and friendly!"""
    )
    
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent is ready!")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
