"""
Intelligent Interruption Handling Demo

This example demonstrates the intelligent interruption handling feature that
distinguishes between backchannel words (yeah, ok, hmm) and real interruptions
(stop, wait, no).

Key behaviors:
- When agent is SPEAKING and user says "yeah/ok/hmm" -> IGNORE (agent continues)
- When agent is SPEAKING and user says "stop/wait/no" -> INTERRUPT immediately
- When agent is SILENT and user says "yeah/ok/hmm" -> RESPOND normally
- Semantic awareness: "Yeah, but wait" triggers interrupt because it contains "wait"

Usage:
    python examples/voice_agents/intelligent_interrupt_demo.py console

Environment variables needed (in examples/.env):
    - LIVEKIT_URL
    - LIVEKIT_API_KEY  
    - LIVEKIT_API_SECRET
    - OPENAI_API_KEY
"""

import logging
import os
import sys
from pathlib import Path

# Allow running this demo directly from a source checkout (without pip installing
# the monorepo packages). We add the core and the specific plugin roots needed
# for this example to sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _rel in (
    "livekit-agents/livekit-agents",
    "livekit-plugins/livekit-plugins-openai",
    "livekit-plugins/livekit-plugins-silero",
):
    _p = _REPO_ROOT / _rel
    if _p.exists():
        sys.path.insert(0, str(_p))

for _rel in (
    "livekit-agents",
    "livekit-plugins/livekit-plugins-openai",
    "livekit-plugins/livekit-plugins-silero",
):
    _p = _REPO_ROOT / _rel
    if _p.exists():
        sys.path.insert(0, str(_p))

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.voice import DEFAULT_BACKCHANNEL_WORDS, DEFAULT_INTERRUPT_WORDS
from livekit.plugins import openai, silero

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("intelligent_interrupt_demo")

class StoryTellerAgent(Agent):
    """An agent that tells long stories - perfect for testing interruption handling."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions="""
        You are a helpful and responsive AI assistant.

        Your primary goal is to fulfill any request the user makes to the best of your ability.
        When the user asks you to do something - whether it's explaining a concept, 
        writing code, telling a story, analyzing data, or anything else - commit fully 
        to the task and provide comprehensive, detailed responses.

        IMPORTANT INTERACTION RULES:
        1. When performing a task (especially lengthy explanations, stories, or detailed responses):
        - Provide thorough, complete answers without rushing
        - Include relevant details, examples, and context
        - Take the time needed to properly address the request

        2. User Interruption Handling:
        - If the user interrupts with commands like "stop", "wait", "pause", or "hold on":
            * Immediately stop what you're saying
            * Acknowledge the interruption
            * Ask what they need or how you can help
        
        - If the user provides encouraging feedback like "yeah", "okay", "hmm", "uh-huh", or "right":
            * Treat these as signs they're listening and engaged
            * Continue with your current response WITHOUT pausing or stopping
            * Do NOT acknowledge these as interruptions

        3. Always be ready to:
        - Switch topics if the user changes direction
        - Provide clarification when asked
        - Adjust your approach based on user feedback

        Remember: Your role is to be maximally helpful while respecting the user's 
        communication style and interruption cues.
        """
    )

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    # Print the default word lists for reference
    logger.info("=== Intelligent Interruption Handler Demo ===")
    logger.info(f"Backchannel words (will be IGNORED when agent speaking):")
    logger.info(f"  {DEFAULT_BACKCHANNEL_WORDS}")
    logger.info(f"Interrupt words (will STOP agent immediately):")
    logger.info(f"  {DEFAULT_INTERRUPT_WORDS}")
    logger.info("=" * 50)
    
    llm_model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(),  # Uses Whisper - only needs OPENAI_API_KEY
        llm=openai.LLM(model=llm_model),
        tts=openai.TTS(voice="alloy"),
    )
    
    # Log state changes to observe the behavior
    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        logger.info(f"Agent state: {event.old_state} -> {event.new_state}")
    
    @session.on("user_state_changed") 
    def on_user_state_changed(event):
        logger.info(f"User state: {event.old_state} -> {event.new_state}")
    
    @session.on("user_input_transcribed")
    def on_user_input(event):
        logger.info(f"User said: '{event.transcript}' (final={event.is_final})")
    
    agent = StoryTellerAgent()
    await session.start(agent=agent, room=ctx.room)

    await session.generate_reply(
    instructions="Greet the user warmly and introduce yourself as their AI assistant. "
    "Ask how you can help them today. Briefly mention that while you're responding, "
    "they can say 'yeah' or 'ok' if they're following along, or 'stop' or 'wait' "
    "if they need you to pause."
)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
