"""
Example: Intelligent Interruption Handling with Backchannel Filtering

This example demonstrates the backchannel filter feature that allows the agent to:
1. Continue speaking when user says backchannel words ("yeah", "ok", "hmm")
2. Stop immediately when user says interrupt commands ("stop", "wait", "no")
3. Handle mixed input ("yeah wait") as an interruption
4. Respond to backchannels when the agent is silent

Usage:
    uv run python examples/voice_agents/intelligent_interruption.py console
"""

import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.agents.voice import DEFAULT_BACKCHANNEL_WORDS, DEFAULT_INTERRUPT_WORDS
from livekit.plugins import silero

logger = logging.getLogger("intelligent-interruption")

# Load environment from .env.local
load_dotenv(".env.local")


class StorytellerAgent(Agent):
    """An agent that tells stories and demonstrates intelligent interruption handling."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a storyteller assistant. When asked to tell a story,
            provide an engaging, moderately long story (about 3-5 paragraphs).

            Important behavior:
            - If the user says "yeah", "ok", "hmm" while you're speaking, continue your story.
            - If the user says "stop", "wait", or "actually", stop and listen.
            - If the user is silent and says "yeah" or "ok", ask what they'd like to hear about.

            Keep your responses without emojis or markdown formatting since this is voice-only.
            """
        )

    async def on_enter(self) -> None:
        """Called when the agent joins the session."""
        self.session.generate_reply(
            instructions="Greet the user briefly and offer to tell them a story."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent."""
    # Create agent session with backchannel filtering enabled (default)
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        # Backchannel filtering is enabled by default; override lists via
        # LIVEKIT_BACKCHANNEL_WORDS / LIVEKIT_INTERRUPT_WORDS if needed
        # Optional: customize backchannel words (uses defaults if None)
        # backchannel_words=frozenset({"yeah", "yep", "ok", "okay", "hmm"}),
        # Optional: customize interrupt words (uses defaults if None)
        # interrupt_words=frozenset({"stop", "wait", "no", "pause"}),
        # Enable false interruption handling
        resume_false_interruption=True,
        false_interruption_timeout=1.5,
    )

    await session.start(
        agent=StorytellerAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    cli.run_app(server)
