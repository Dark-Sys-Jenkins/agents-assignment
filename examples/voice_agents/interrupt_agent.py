import os
import re
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
from livekit.plugins import silero

# --------------------------------------------------
# Setup
# --------------------------------------------------

load_dotenv()
logger = logging.getLogger("interrupt-agent")

# Passive backchannel words (configurable)
IGNORE_WORDS = {
    "okay", "ok", "yeah", "hmm", "uh", "uhh", "uh-huh", "right", "aha"
}

# Explicit interruption commands
INTERRUPT_WORDS = {
    "stop", "wait", "no", "pause", "hold"
}


def classify(text: str) -> str:
    """
    Classify user input into:
    - IGNORE: passive acknowledgement
    - INTERRUPT: explicit command
    - VALID: normal speech
    """
    text = re.sub(r"[^\w\s]", "", text.lower().strip())
    tokens = set(text.split())

    # Semantic interruption always wins
    if tokens & INTERRUPT_WORDS:
        return "INTERRUPT"

    # Pure filler only
    if tokens and tokens.issubset(IGNORE_WORDS):
        return "IGNORE"

    return "VALID"


# --------------------------------------------------
# Agent
# --------------------------------------------------

class InterruptAwareAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "Your name is Kelly. You are a friendly voice assistant. "
                "Speak clearly and naturally. English only."
            )
        )
        self.speaking = False

    async def on_audio_start(self):
        self.speaking = True

    async def on_audio_end(self):
        self.speaking = False

    async def on_enter(self):
        self.speaking = True
        self.session.generate_reply()

    async def on_user_message(self, message: str):
        decision = classify(message)

        logger.info(
            f"user_message='{message}' decision={decision} speaking={self.speaking}"
        )

        # --------------------------------------------------
        # AGENT IS SPEAKING
        # --------------------------------------------------
        if self.speaking:

            # Passive acknowledgement → FALSE INTERRUPTION
            if decision == "IGNORE":
                # Let LiveKit resume audio automatically
                self.session.cancel_generation()
                return

            # Explicit command → HARD INTERRUPT
            if decision == "INTERRUPT":
                await self.session.stop_audio()
                self.session.cancel_generation()
                self.speaking = False
                return

            # Real speech → interrupt and respond
            await self.session.stop_audio()
            self.speaking = False
            await self.session.generate_reply()
            return

        # --------------------------------------------------
        # AGENT IS SILENT
        # --------------------------------------------------
        await self.session.generate_reply()


# --------------------------------------------------
# Server
# --------------------------------------------------

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2",
        vad=ctx.proc.userdata["vad"],

        # 🔑 REQUIRED FOR FALSE-INTERRUPTION HANDLING
        turn_detection=None,
        preemptive_generation=False,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    await session.start(
        agent=InterruptAwareAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
