from dotenv import load_dotenv
load_dotenv()
import logging
import string

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentStateChangedEvent,
    JobContext,
    JobProcess,
    UserInputTranscribedEvent,
    UserStateChangedEvent,
    cli,
)
from livekit.plugins import google, silero, deepgram

# Configure logging
logger = logging.getLogger("interrupt-handler")
logger.setLevel(logging.INFO)

# --- CONFIGURATION ---
# Words to ignore when the agent is speaking (Backchanneling)
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "hm", "uh-huh", "right", 
    "cool", "nice", "got it", "i see", "sure", "yep", "yup"
}
INTERRUPT_WORDS = {
    "stop", "wait", "pause", "hold", "cancel", "silence", "quiet", "shut", "enough"
}

def is_backchannel(text: str) -> bool:
    """
    Determines if the text is purely backchanneling/filler words.
    Returns True if the text consists ONLY of words in the IGNORE_WORDS set.
    """
    clean_text = text.lower().translate(str.maketrans('', '', string.punctuation)).strip()
    if not clean_text:
        return False 
    words = set(clean_text.split())
    return words.issubset(IGNORE_WORDS)

def is_interrupt_command(text: str) -> bool:
    clean_text = text.lower().translate(str.maketrans('', '', string.punctuation)).strip()
    if not clean_text:
        return False
    words = set(clean_text.split())
    return len(words.intersection(INTERRUPT_WORDS)) > 0

class IntelligentInterruptionAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a voice assistant. Keep responses concise. "
                "If the user interrupts you with a meaningful request, stop speaking and listen. "
                "If the user says only backchannel words like 'yeah' or 'ok' while you speak, ignore them."
            )
        )

    async def on_enter(self) -> None:
        # Start with a deterministic demo script.
        greeting = (
            "Hello! I am running on Google Gemini. I am ready to read a long text. "
            "Try saying 'Yeah' while I speak, or 'Stop' to interrupt me."
        )
        await self.session.say(text=greeting, allow_interruptions=False).wait_for_playout()

        long_text = (
            "The history of artificial intelligence began in antiquity, with myths, stories "
            "and rumors of artificial beings endowed with intelligence or consciousness by master craftsmen. "
            "The seeds of modern AI were planted by classical philosophers who attempted to describe the "
            "process of human thinking as the mechanical manipulation of symbols. This work culminated in "
            "the invention of the programmable digital computer in the 1940s."
        )
        await self.session.say(text=long_text, allow_interruptions=True).wait_for_playout()


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Track whether the user started speaking while the agent was speaking.
    agent_is_speaking = False
    agent_was_speaking_at_turn_start = False

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=deepgram.TTS(),
        # Allow manual interruption via session.interrupt(), but effectively disable
        # automatic VAD-based interruptions by requiring a very long interruption.
        allow_interruptions=True,
        min_interruption_duration=60.0,
        min_interruption_words=50,
        min_endpointing_delay=0.5,
    )

    @session.on("agent_state_changed")
    def _agent_state_changed(ev: AgentStateChangedEvent):
        nonlocal agent_is_speaking
        agent_is_speaking = ev.new_state == "speaking"

    @session.on("user_state_changed")
    def _user_state_changed(ev: UserStateChangedEvent):
        nonlocal agent_was_speaking_at_turn_start
        if ev.new_state == "speaking":
            agent_was_speaking_at_turn_start = agent_is_speaking
            logger.info(
                "User started speaking. Agent speaking: %s", agent_was_speaking_at_turn_start
            )

    @session.on("user_input_transcribed")
    def _user_input_transcribed(ev: UserInputTranscribedEvent):
        if not ev.is_final:
            return

        text = (ev.transcript or "").strip()
        if not text:
            return

        if not agent_was_speaking_at_turn_start:
            return

        if is_backchannel(text):
            logger.info("Ignoring backchannel during agent speech: '%s'", text)
            session.clear_user_turn()
            return

        if is_interrupt_command(text):
            logger.info("Active interruption detected: '%s' -> interrupting.", text)
            session.interrupt(force=True)
            return

        logger.info("Ignoring non-interrupt speech during agent speech: '%s'", text)
        session.clear_user_turn()

    await session.start(agent=IntelligentInterruptionAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)