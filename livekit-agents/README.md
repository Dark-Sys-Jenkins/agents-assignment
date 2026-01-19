# LiveKit Agents for Python

Realtime framework for production-grade multimodal and voice AI agents.

See [https://docs.livekit.io/agents/](https://docs.livekit.io/agents/) for quickstarts, documentation, and examples.

```python
import re
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.plugins import openai

load_dotenv()

# =========================
# CONFIGURATION
# =========================

# Words that mean "I am listening, continue"
FILLER_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "mm-hm", "right"
}

# Words that mean "stop / interrupt"
INTERRUPT_WORDS = {
    "stop", "wait", "no", "pause", "hold"
}

# Agent speaking state
agent_is_speaking = False


# =========================
# HELPERS
# =========================

def normalize(text: str) -> list[str]:
    """
    Normalize STT text:
    - lowercase
    - remove punctuation
    - split into words
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return text.split()


def should_interrupt(agent_speaking: bool, words: list[str]) -> bool:
    """
    Core decision logic.
    Returns True if the agent should stop speaking.
    """

    # If agent is silent, everything is valid input
    if not agent_speaking:
        return True

    if not words:
        return False

    has_interrupt = any(word in INTERRUPT_WORDS for word in words)
    is_filler_only = all(word in FILLER_WORDS for word in words)

    if has_interrupt:
        return True

    if is_filler_only:
        return False

    # Any meaningful speech while agent is speaking interrupts
    return True


# =========================
# ENTRYPOINT
# =========================

async def entrypoint(ctx: agents.JobContext):
    global agent_is_speaking

    await ctx.connect()

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="coral"
        )
    )

    # =========================
    # EVENT HANDLERS
    # =========================

    # Agent starts speaking (TTS playback begins)
    @session.on("agent_speech_start")
    async def on_agent_speech_start():
        global agent_is_speaking
        agent_is_speaking = True
        print("[STATE] Agent speaking")

    # Agent stops speaking (TTS playback ends)
    @session.on("agent_speech_end")
    async def on_agent_speech_end():
        global agent_is_speaking
        agent_is_speaking = False
        print("[STATE] Agent silent")

    # User transcription received (STT result)
    @session.on("user_transcription")
    async def on_user_transcription(event):
        words = normalize(event.text)
        decision = should_interrupt(agent_is_speaking, words)

        print(f"[STT] '{event.text}' → words={words} interrupt={decision}")

        if decision:
            await session.interrupt()
        else:
            # Filler-only speech while agent is talking → ignore
            pass

    # =========================
    # START SESSION
    # =========================

    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions="You are a helpful voice AI assistant."
        )
    )

    # Initial greeting
    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )

```
