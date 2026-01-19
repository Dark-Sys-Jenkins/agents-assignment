import logging
import asyncio
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
from livekit.agents.llm import ChatContext, ChatMessage, StopResponse
from livekit.agents.voice import UserInputTranscribedEvent
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()
logger = logging.getLogger("basic-agent")

# -------------------------
# Backchannel logic
# -------------------------

SOFT_WORDS = {
    "yeah", "yep", "yes", "yup", "ok", "okay", "right",
    "uh-huh", "hmm", "sure", "got it", "mhm",
    "ah", "oh", "i see",
}

def normalize(text: str) -> str:
    return (
        text.lower()
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
        .strip()
    )

def should_interrupt(text: str) -> bool:
    clean = normalize(text)
    if not clean:
        return False
    words = clean.split()
    # Interrupt if ANY word is NOT a soft word
    return any(word not in SOFT_WORDS for word in words)


# -------------------------
# Agent
# -------------------------

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You are a helpful voice assistant. "
                "Speak clearly and naturally. Keep responses concise."
            ),
        )
        self._was_speaking_during_input = False

    def set_context(self, was_speaking: bool):
        self._was_speaking_during_input = was_speaking

    async def on_user_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        user_text = (new_message.text_content or "").strip()

        # Ignore backchannels ONLY if agent was speaking
        if self._speaking_during_input and not should_interrupt(user_text):
            logger.info(f"IGNORING BACKCHANNEL: '{user_text}'")
            self._speaking_during_input = False
            raise StopResponse()

        # Otherwise accept normally
        self._speaking_during_input = False
        logger.info(f"ACCEPTED INPUT: '{user_text}'")


# -------------------------
# Server
# -------------------------

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        # REQUIRED MODELS (DO NOT REMOVE)
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",

        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),

        # REQUIRED FOR CHAT VISIBILITY
        preemptive_generation=True,

        # CRITICAL FOR CHALLENGE
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
    )

    agent = MyAgent()

    @session.on("user_input_transcribed")
    def on_transcribed(ev: UserInputTranscribedEvent):
        if not ev.is_final:
            return

        is_speaking = session.current_speech is not None
        agent.set_context(is_speaking)

        if is_speaking and should_interrupt(ev.transcript):
            logger.info(f"HARD INTERRUPT: '{ev.transcript}'")
            asyncio.ensure_future(session.interrupt(force=True))

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    cli.run_app(server)
