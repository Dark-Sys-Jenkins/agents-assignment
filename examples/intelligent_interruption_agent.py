"""
Example Voice Agent with Intelligent Interruption Handling

This example demonstrates how to use the IntelligentInterruptionHandler
to create a voice agent that can distinguish between backchanneling
(passive acknowledgements like "yeah", "ok") and active interruptions
(commands like "wait", "stop").

The agent will:
- Continue speaking when user says "yeah", "ok", "hmm" etc.
- Stop immediately when user says "wait", "stop", "no" etc.
- Respond to all input when agent is silent
"""

import asyncio
import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import IntelligentInterruptionHandler, InterruptionConfig
from livekit.plugins import deepgram, openai, silero

# Import custom configuration (optional)
try:
    from interruption_config import IGNORE_WORDS, INTERRUPT_WORDS, CASE_SENSITIVE
    use_custom_config = True
except ImportError:
    use_custom_config = False

logger = logging.getLogger("intelligent-agent")
logger.setLevel(logging.INFO)

load_dotenv()


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the voice agent."""
    
    logger.info("Starting intelligent voice agent with interruption handling")
    
    # Connect to the room
    await ctx.connect()
    
    # Configure the intelligent interruption handler
    if use_custom_config:
        # Use custom configuration from interruption_config.py
        interruption_config = InterruptionConfig(
            ignore_words=IGNORE_WORDS,
            interrupt_words=INTERRUPT_WORDS,
            case_sensitive=CASE_SENSITIVE
        )
        handler = IntelligentInterruptionHandler(config=interruption_config)
        logger.info(f"Using custom config: {len(IGNORE_WORDS)} ignore words, {len(INTERRUPT_WORDS)} interrupt words")
    else:
        # Use default configuration
        handler = IntelligentInterruptionHandler()
        logger.info("Using default interruption handler configuration")
    
    # Create the agent with specific instructions
    agent = Agent(
        instructions="""You are a helpful voice assistant with intelligent interruption handling.
        
You will explain things in detail, and users can acknowledge they're listening by saying
things like "yeah", "ok", or "hmm" without interrupting you.

However, if they say "wait", "stop", or other interrupt commands, you will stop immediately.

Try to speak in longer sentences to demonstrate the interruption handling. For example,
when asked about history, give a detailed 30-second explanation that the user might
acknowledge with "yeah" or "ok" while you're speaking.""",
    )
    
    # Create the session with the interruption handler
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
        interruption_handler=handler,  # <- This enables intelligent interruption handling
        allow_interruptions=True,  # Must be True for interruptions to work
        min_interruption_words=1,  # Allow single-word interruptions
    )
    
    # Event handlers for debugging and monitoring
    @session.on("user_input_transcribed")
    def on_user_input(event):
        """Log user input as it's transcribed."""
        if event.is_final:
            logger.info(f"User said (final): {event.transcript}")
        else:
            logger.debug(f"User said (interim): {event.transcript}")
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        """Log agent state changes."""
        logger.info(f"Agent state: {event.state}")
    
    @session.on("agent_false_interruption")
    def on_false_interruption(event):
        """Log false interruptions (when detected)."""
        if event.resumed:
            logger.info("False interruption detected - resumed speaking")
        else:
            logger.info("False interruption detected - stopped speaking")
    
    @session.on("speech_created")
    def on_speech_created(event):
        """Log when agent starts speaking."""
        logger.info(f"Agent speech created (source: {event.source})")
    
    # Start the session
    session.start(ctx.room)
    
    # Say a greeting
    await session.say(
        "Hello! I'm an intelligent voice assistant. I can tell when you're just "
        "acknowledging that you're listening, versus when you actually want to interrupt me. "
        "Try saying 'tell me about the history of computers' and then say 'yeah' or 'ok' "
        "while I'm talking. I'll keep going! But if you say 'wait' or 'stop', I'll "
        "stop immediately.",
        allow_interruptions=True
    )
    
    # Wait for the session to end
    await session.wait_for_close()
    
    logger.info("Session ended")


if __name__ == "__main__":
    # Run the agent with CLI
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
