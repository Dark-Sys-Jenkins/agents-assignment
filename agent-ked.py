import logging
import re
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

# -----------------------------
# Filler / Interrupt word sets
# -----------------------------
FILLER_WORDS = {
    "yeah", "ok", "okay", "uh", "uhh", "hmm", "mm", "mmhmm", 
    "uhhuh", "right", "aha", "mhm", "yep", "yup", "sure", "gotcha",
    "alright", "mhmm", "uh huh"
}

INTERRUPT_WORDS = {
    "stop", "wait", "hold", "pause", "no", "but", "however"
}


def is_filler_only(text: str) -> bool:
    """Check if transcript contains only filler words"""
    words = re.findall(r"[a-z']+", text.lower())
    return bool(words) and all(w in FILLER_WORDS for w in words)


def contains_interrupt_word(text: str) -> bool:
    """Check if transcript contains any interrupt words"""
    words = re.findall(r"[a-z']+", text.lower())
    return any(w in INTERRUPT_WORDS for w in words)


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        
        # KEY SETTINGS for handling fillers without pauses
        # Require at least 2 words to interrupt (fillers are usually 1 word)
        min_interruption_words=2,
        
        # Set a timeout for false interruptions (e.g., fillers)
        # If no real speech is detected after this time, resume
        false_interruption_timeout=0.8,  # 800ms
        
        # Automatically resume after false interruption
        resume_false_interruption=True,
        
        # Minimum speech duration to trigger interruption (in seconds)
        min_interruption_duration=0.3,  # 300ms - very short utterances ignored
    )

    agent_speaking = False
    pending_fillers = set()  # Track potential filler interruptions

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        nonlocal agent_speaking
        agent_speaking = (ev.new_state == "speaking")
        logger.debug(f"Agent state changed to: {ev.new_state}")

    @session.on("agent_false_interruption")
    def on_false_interruption(ev):
        """
        This event fires when VAD detected speech but no actual transcription came through.
        This is EXACTLY what happens with very short fillers.
        """
        logger.info("✓ False interruption detected - agent will resume automatically")

    @session.on("user_input_transcribed")
    def on_user_transcribed(ev):
        """
        Handle transcribed user input with intelligent filtering.
        This is a secondary safety layer since min_interruption_words should
        already prevent most single-word fillers from interrupting.
        """
        
        # Only process final transcripts
        if not ev.is_final:
            return

        text = ev.transcript.strip()
        if not text:
            return

        logger.info(f"Transcript: '{text}' | Agent speaking: {agent_speaking}")

        # CASE 1: Agent is speaking and user said only filler words
        # With min_interruption_words=2, single-word fillers shouldn't reach here,
        # but we handle them anyway for multi-word fillers like "yeah okay"
        if agent_speaking and is_filler_only(text):
            logger.info(f"✓ SUPPRESSING filler: '{text}'")
            # Mark this as handled so it doesn't trigger a response
            session.clear_user_turn()
            return

        # CASE 2: Agent is speaking and user said interrupt word(s)
        if agent_speaking and contains_interrupt_word(text):
            logger.info(f"✓ INTERRUPTING due to command: '{text}'")
            # Force immediate interruption
            session.interrupt()
            return

        # CASE 3: Agent is speaking and user said substantive content
        if agent_speaking:
            logger.info(f"✓ Substantive input during speech: '{text}'")
            session.interrupt()
            return

        # CASE 4: Agent is silent - normal processing
        logger.info(f"✓ Processing input (agent silent): '{text}'")

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)