import logging
import re

from dotenv import load_dotenv

from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.voice import AgentSession, Agent, RoomInputOptions

logger = logging.getLogger("interrupt-worker")
logger.setLevel(logging.INFO)

load_dotenv()

server = AgentServer()

# -----------------------------
# Filler / Interrupt word sets
# -----------------------------
FILLER_WORDS = {
    "yeah", "ok", "okay", "uh", "uhh", "hmm", "mm", "mmhmm", "uhhuh"
}

INTERRUPT_WORDS = {
    "stop", "wait", "hold", "pause", "no"
}


def is_filler_only(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    return bool(words) and all(w in FILLER_WORDS for w in words)


def contains_interrupt_word(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    return any(w in INTERRUPT_WORDS for w in words)


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info(f"Connected to room {ctx.room.name}")

    session = AgentSession()

    agent = Agent(
        instructions="You are a helpful voice assistant."
    )

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions()
    )

    agent_speaking = False

    # Track agent speaking state
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        nonlocal agent_speaking
        agent_speaking = (ev.new_state == "speaking")

    # Intercept user transcripts
    @session.on("user_input_transcribed")
    def on_user_transcribed(ev):
        # Only care about final transcripts
        if not ev.is_final:
            return

        text = ev.transcript.strip()
        if not text:
            return

        # If agent is speaking and user said only filler -> ignore
        if agent_speaking and is_filler_only(text):
            logger.info(f"Ignored filler while speaking: {text}")
            session.clear_user_turn()
            return

        # If interrupt word present -> stop agent speech
        if agent_speaking and contains_interrupt_word(text):
            logger.info(f"Interrupt detected: {text}")
            session.interrupt()
            return

        # Otherwise normal behavior
        logger.info(f"User said: {text}")


if __name__ == "__main__":
    cli.run_app(server)
