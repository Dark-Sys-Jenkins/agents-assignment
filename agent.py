import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Make sure you have the livekit and deepgram libraries installed
from livekit.agents import JobContext, WorkerOptions, cli
from livekit import rtc
from livekit.agents.stt import SpeechEventType
from livekit.plugins import deepgram

from interruption_logic import InterruptionLogic

load_dotenv(Path(__file__).parent / ".env")init

# Basic logging setup
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

# Global variables to track state
agent_speaking = False
current_speak_task = None

async def speak(room: rtc.Room, text: str, duration: float = 3.0):
    global agent_speaking
    
    logger.info(f"🔊 Agent STARTED speaking: '{text}'")
    agent_speaking = True

    # We create a dummy audio track so the UI shows the agent is 'active'
    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("agent-voice", source)
    publication = await room.local_participant.publish_track(track)

    try:
        # Simulate talking time (since we have no TTS API key)
        await asyncio.sleep(duration)
        logger.info(f"✅ Agent FINISHED speaking: '{text}'")
        
    except asyncio.CancelledError:
        logger.info(f"🛑 Agent speech CANCELLED: '{text}'")
        raise  # Important: allows the task to actually stop
        
    finally:
        # This runs whether finished normally OR cancelled
        await room.local_participant.unpublish_track(publication.sid)
        await track.stop()
        agent_speaking = False

async def entrypoint(ctx: JobContext):
    global current_speak_task

    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    stt = deepgram.STT(model="nova-2-general")

    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Connect to user audio
    audio_track = None
    while not audio_track:
        for pub in participant.track_publications.values():
            if pub.track and pub.kind == rtc.TrackKind.KIND_AUDIO:
                audio_track = pub.track
                break
        await asyncio.sleep(0.1)

    audio_stream = rtc.AudioStream(audio_track)
    stt_stream = stt.stream()

    # Send audio to Deepgram
    async def push_audio():
        async for ev in audio_stream:
            stt_stream.push_frame(ev.frame)
    asyncio.create_task(push_audio())

    logger.info("Listening...")

    async for event in stt_stream:
        # We only care about final transcripts for logic
        if event.type == SpeechEventType.FINAL_TRANSCRIPT:
            user_text = event.alternatives[0].text.strip()
            logger.info(f"👤 User said: '{user_text}'")

            if agent_speaking:
                # Check if we should interrupt
                if InterruptionLogic.is_interrupt(user_text):
                    logger.info("⚡ INTERRUPT DETECTED")

                    if current_speak_task:
                        current_speak_task.cancel()
                        # Wait a tiny bit to ensure the flag resets
                        await asyncio.sleep(0.05) 

                    # Agent acknowledges the stop
                    current_speak_task = asyncio.create_task(
                        speak(ctx.room, "Okay, stopping.", duration=1.0)
                    )
                else:
                    logger.info("Ignoring backchannel/noise.")

            else:
                # Agent is silent, so just reply normally
                logger.info("Normal reply trigger.")
                current_speak_task = asyncio.create_task(
                    speak(ctx.room, f"I heard you say {user_text}", duration=3.0)
                )

if __name__ == "__main__":
    # This starts the agent. Do not add code after this.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))