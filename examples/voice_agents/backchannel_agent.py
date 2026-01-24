"""
Backchannel-Filtered Voice Agent Demo

This agent demonstrates intelligent interruption handling for the LiveKit
Intelligent Interruption Handling Challenge.

Behavior:
    - Agent IGNORES backchannels (yeah, ok, hmm) while speaking
    - Agent INTERRUPTS for commands (stop, wait, no) while speaking
    - Agent PROCESSES all input when silent

Usage:
    python backchannel_agent.py console   # Local testing with microphone
    python backchannel_agent.py dev       # Connect to LiveKit room

Author: Aswani Sahoo
Assignment: LiveKit Intelligent Interruption Handling Challenge
"""

from __future__ import annotations

import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice.events import (
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)
from livekit.plugins import deepgram, groq, silero, cartesia

from livekit.agents.voice.backchannel_filter import (
    BackchannelConfig,
    set_config,
    get_config,
)

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("backchannel_agent")

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def setup_filter():
    """
    Configure the backchannel filter.
    
    Enables debug mode to log classification decisions.
    Custom words can be added here if needed.
    """
    config = get_config()
    config.debug_mode = True
    set_config(config)
    
    logger.info(
        f"Backchannel filter configured: "
        f"ignore={len(config.ignore_words)} words, "
        f"interrupt={len(config.interrupt_words)} words"
    )


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the backchannel-filtered agent."""
    
    setup_filter()
    
    await ctx.connect()
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
    )
    
    @session.on("agent_state_changed")
    def on_agent_state(event: AgentStateChangedEvent):
        logger.info(f"Agent state: {event.old_state} -> {event.new_state}")
    
    @session.on("user_input_transcribed")
    def on_transcript(event: UserInputTranscribedEvent):
        if event.is_final:
            logger.info(f"User: '{event.transcript}'")
    
    agent = Agent(
        instructions="""You are a helpful assistant demonstrating intelligent interruption handling.

When the user asks a question, provide a detailed multi-sentence response.
This allows the user to test backchannel handling while you speak.

Behavior to demonstrate:
- If user says "yeah", "ok", or "hmm" while you speak, continue without pause
- If user says "stop", "wait", or "no" while you speak, stop immediately
- If user says backchannels when you are silent, respond to them normally

Start by greeting the user and asking them to test the interruption handling
by asking you a question and then saying "yeah" while you answer."""
    )
    
    await session.start(agent=agent, room=ctx.room)
    
    logger.info("Backchannel-filtered agent started")
    logger.info("Test: Say 'yeah' while agent speaks - agent should continue")
    logger.info("Test: Say 'stop' while agent speaks - agent should stop")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
