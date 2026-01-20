import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from agent_speak import TextToSpeech
from interruption_logic import InterruptionLogic

from livekit.agents import JobContext, WorkerOptions, cli
from livekit import rtc
from livekit.agents.stt import SpeechEventType
from livekit.plugins import deepgram

# ─────────────────────────────────────────────────────────────
# Environment & Logging
# ─────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

LOG_FILE = Path(__file__).parent / "easy_logging_status.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("interrupt-agent")

# ─────────────────────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────────────────────

agent_speaking = False
current_speak_task = None
tts_engine = TextToSpeech()

# ─────────────────────────────────────────────────────────────
# TTS helper (ONLY speak_engine)
# ─────────────────────────────────────────────────────────────

def blocking_speak(text: str):
    tts_engine.speak_engine(text)

async def speak(text: str):
    global agent_speaking

    logger.info(f"Agent speaking: '{text}'")
    agent_speaking = True
    try:
        await asyncio.to_thread(blocking_speak, text)
    finally:
        agent_speaking = False
        logger.info("Agent finished speaking")

# ─────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    global current_speak_task, agent_speaking

    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    stt = deepgram.STT()

    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    audio_track = None
    while not audio_track:
        for pub in participant.track_publications.values():
            if pub.track and pub.kind == rtc.TrackKind.KIND_AUDIO:
                audio_track = pub.track
                break
        await asyncio.sleep(0.1)

    audio_stream = rtc.AudioStream(audio_track)
    stt_stream = stt.stream()

    async def push_audio():
        async for ev in audio_stream:
            stt_stream.push_frame(ev.frame)

    asyncio.create_task(push_audio())

    logger.info("Listening for speech events")

    async for event in stt_stream:

        if event.type == SpeechEventType.START_OF_SPEECH:
            if agent_speaking:
                logger.info("START_OF_SPEECH ignored (agent speaking)")
            else:
                logger.info("START_OF_SPEECH (agent silent)")
            continue

        if event.type == SpeechEventType.FINAL_TRANSCRIPT:
            user_text = event.alternatives[0].text.strip()
            logger.info(f"FINAL_TRANSCRIPT: '{user_text}'")

            # ── Agent speaking ──
            if agent_speaking:
                if InterruptionLogic.is_interrupt(user_text):
                    logger.info("🛑 INTERRUPT detected — stopping agent")

                    if current_speak_task:
                        current_speak_task.cancel()

                    current_speak_task = asyncio.create_task(
                        speak("Okay, stopping.")
                    )
                else:
                    logger.info("Backchannel ignored (agent continues)")
                continue

            # ── Agent silent ──
            if InterruptionLogic.is_interrupt(user_text):
                logger.info("Interrupt ignored (agent silent)")
                continue

            if InterruptionLogic.is_backchannel(user_text):
                logger.info("Backchannel accepted (agent silent)")
                await speak("Okay, starting now.")
                continue

            logger.info("Normal turn (agent silent)")
            await speak(f"You said {user_text}")

# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
