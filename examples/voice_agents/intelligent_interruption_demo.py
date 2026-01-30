"""
Intelligent Interruption Handling Demo
======================================

This example demonstrates the intelligent interruption handling feature that
distinguishes between passive acknowledgements ("yeah", "ok", "hmm") and
intentional interruptions ("stop", "wait", "no").

Key behaviors:
1. When the agent is speaking and the user says "yeah/ok/hmm" -> Agent continues uninterrupted
2. When the agent is speaking and the user says "stop/wait/no" -> Agent stops immediately  
3. When the agent is silent and the user says "yeah" -> Agent responds normally

Usage:
    uv run examples/voice_agents/intelligent_interruption_demo.py console

Environment variables:
    LIVEKIT_URL - Your LiveKit server URL
    LIVEKIT_API_KEY - Your LiveKit API key
    LIVEKIT_API_SECRET - Your LiveKit API secret
    OPENAI_API_KEY - Your OpenAI API key (for LLM and TTS)
    
    # Optional: Customize ignored words (comma-separated)
    LIVEKIT_AGENT_IGNORED_WORDS - e.g., "yeah,ok,hmm,right,uh-huh"
"""

from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, openai, silero


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # Create an agent with a long explanation prompt to test interruption handling
    agent = Agent(
        instructions="""You are a helpful voice assistant demonstrating intelligent interruption handling.

When asked to explain something, give a LONG, detailed explanation (at least 30 seconds of speech).
This helps demonstrate that you can continue speaking even when the user says "yeah", "ok", or "hmm"
to acknowledge they're listening.

Example topics you can explain in detail:
- The history of the internet
- How airplanes fly
- The water cycle
- Photosynthesis
- How computers work

When the user says things like "stop", "wait", "hold on", or "no", you should stop immediately
and listen to what they have to say.

Start by greeting the user and offering to explain a topic in detail.""",
    )

    # Create the agent session with intelligent interruption handling
    # The ignored_words list can be customized here or via environment variable
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        # Customize the ignored words list if needed (uses defaults if not specified)
        # ignored_words=["yeah", "ok", "hmm", "right", "uh-huh", "mhm", "sure"],
    )

    # Log the current ignored words configuration
    print(f"\n🎤 Ignored words (backchannel): {list(session.options.ignored_words)}")
    print("   These words will NOT interrupt the agent while it's speaking.\n")

    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
