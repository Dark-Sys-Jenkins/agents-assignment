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

Features:
- Configurable fuzzy matching threshold (default 80%, range 0-100)
- Handles typos and misspellings ("yeahh", "okayy", "yea")
- STT transcription variations ("yah" vs "yeah")
- Common phonetic variations
- Robust error handling for fuzzy matching failures
- Case-insensitive matching
- Punctuation handling

Configuration:
    # Default threshold (80%)
    session = AgentSession(...)
    
    # Stricter matching (requires closer matches)
    session = AgentSession(fuzzy_match_threshold=90, ...)
    
    # More lenient matching (allows more variations)
    session = AgentSession(fuzzy_match_threshold=70, ...)

Usage:
    uv run examples/voice_agents/intelligent_interruption_demo.py console
    
    # Text mode (no microphone required)
    uv run examples/voice_agents/intelligent_interruption_demo.py console --text

Environment variables:
    LIVEKIT_URL - Your LiveKit server URL
    LIVEKIT_API_KEY - Your LiveKit API key
    LIVEKIT_API_SECRET - Your LiveKit API secret
    OPENAI_API_KEY - Your OpenAI API key (for LLM and TTS)
    
    # Optional: Customize ignored words (comma-separated)
    LIVEKIT_AGENT_IGNORED_WORDS - e.g., "yeah,ok,hmm,right,uh-huh"
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from examples directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

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
    # The fuzzy_match_threshold can be adjusted (default 80, range 0-100)
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        # Customize the ignored words list if needed (uses defaults if not specified)
        # ignored_words=["yeah", "ok", "hmm", "right", "uh-huh", "mhm", "sure"],
        # Customize fuzzy matching threshold (default 80)
        # fuzzy_match_threshold=90,  # Stricter: requires closer matches
        # fuzzy_match_threshold=70,  # More lenient: allows more variations
    )

    # Log the current configuration
    print(f"\n🎤 Ignored words (backchannel): {list(session.options.ignored_words)}")
    print(f"📊 Fuzzy match threshold: {session.options.fuzzy_match_threshold}%")
    print("   These words will NOT interrupt the agent while it's speaking.")
    print("\n💡 Try saying 'yeah' or 'ok' while the agent is talking - it will continue!")
    print("   But saying 'stop' or 'wait' will interrupt immediately.\n")

    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
