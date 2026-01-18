"""
Demo agent for intelligent interruption handling.

Shows how the agent ignores filler words ("yeah", "ok") while speaking
but responds to them when silent, and stops on commands ("stop", "wait").

Usage:
    python intelligent_interruption_agent.py dev

Environment variables:
    SOFT_WORDS - comma-separated filler words to ignore
    HARD_INTERRUPT_WORDS - comma-separated interrupt commands
    INTERRUPTION_DEBUG - set to "true" for verbose logging
"""

import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("interruption-demo")
load_dotenv()


class StorytellerAgent(Agent):
    """Agent that tells stories - useful for testing backchanneling."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly storyteller named Alex.

When asked, tell detailed stories (4-5 sentences minimum) about history or science.

Behavior notes:
- If user says "yeah", "ok", "hmm" while you speak, they're just listening - continue.
- If user says "stop", "wait", "no", stop immediately.
- When you're silent and user says "yeah", treat it as confirmation.

Keep responses conversational. No emojis or markdown.""",
        )

    async def on_enter(self):
        self.session.generate_reply(
            instructions="Greet the user and offer to tell an interesting story."
        )

    @function_tool
    async def tell_history_story(self, context: RunContext):
        """Tell a detailed history story when the user asks for one."""
        logger.info("Telling history story")
        return (
            "The Library of Alexandria was one of the largest libraries of the ancient world. "
            "Founded in the 3rd century BCE by Ptolemy I, it held between 400,000 and 700,000 scrolls. "
            "Scholars from everywhere came to study there. The library's decline was gradual, "
            "caused by fires, budget cuts, and political instability over several centuries."
        )

    @function_tool
    async def tell_science_story(self, context: RunContext):
        """Tell a detailed science story when the user asks for one."""
        logger.info("Telling science story")
        return (
            "In the 1950s, scientists knew DNA carried genetic information but not its shape. "
            "Rosalind Franklin captured Photo 51, an X-ray image showing DNA's helical structure. "
            "Watson and Crick used this to build their famous double helix model in 1953. "
            "This discovery revolutionized biology and medicine."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
        allow_interruptions=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=StorytellerAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    cli.run_app(server)
