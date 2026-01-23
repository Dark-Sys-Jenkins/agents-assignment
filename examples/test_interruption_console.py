"""
Console mode test agent - runs locally without LiveKit server.

This demonstrates the interruption problem in terminal mode.

Run with: python test_interruption_console.py console

Test scenarios:
1. Let agent start speaking
2. Say "yeah" or "ok" → Agent should continue but currently stops
3. Say "stop" → Agent should stop (works correctly)
"""

import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import groq, deepgram, silero, openai, cartesia

logging.basicConfig(level=logging.INFO)
# Suppress noisy logs from plugins if needed
logging.getLogger("livekit.plugins").setLevel(logging.WARNING)
logger = logging.getLogger("console-test")


class TestAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful assistant. "
                "Keep your responses concise but informative. "
                "Do not use emojis or special characters."
            ),
        )

    async def on_enter(self):
        logger.info("=" * 60)
        logger.info("🧪 INTERRUPTION TEST - Console Mode")
        logger.info("=" * 60)
        logger.info("The agent will start explaining something.")
        logger.info("Try these tests:")
        logger.info("  1. Say 'yeah' while agent talks → Should continue (PROBLEM)")
        logger.info("  2. Say 'stop' while agent talks → Should stop (OK)")
        logger.info("  3. Say 'yeah' when silent → Should respond (OK)")
        logger.info("=" * 60)
        
        # Initial trigger
        await self.session.generate_reply(
            instructions=(
                "Greet the user and briefly explain what ARPANET was. "
                "Keep it to 2-3 sentences."
            )
        )


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    import os
    filter_words = os.getenv("INTERRUPTION_FILTER_WORDS", "").split(",")
    filter_words = [w.strip().lower() for w in filter_words if w.strip()]

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"), 
        tts=cartesia.TTS(),
        # Optimized settings for latency and intelligent interruption
        min_endpointing_delay=0.4,
        preemptive_generation=False,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )
    
    # Event logging
    @session.on("agent_state_changed")
    def _on_agent_state(ev):
        logger.info(f"🤖 Agent: {ev.old_state} → {ev.new_state}")
    
    @session.on("user_input_transcribed")
    def _on_user_input(ev):
        if ev.is_final:
            logger.info(f"📝 You said: '{ev.transcript}'")
    
    @session.on("agent_false_interruption")
    def _on_false_interruption(ev):
        logger.warning(f"⚠️  False interruption! Resumed: {ev.resumed}")
    
    await session.start(agent=TestAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
