import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.plugins import silero, deepgram, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

load_dotenv(override=True)

# Configure simple logging to avoid terminal display issues on Windows
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("basic-agent")


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    # Set VAD activation threshold to 0.5 to filter out background noise
    proc.userdata["vad"] = silero.VAD.load(activation_threshold=0.5)


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    logger.info(f"Entrypoint called for room: {ctx.room.name}")
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    try:
        # Get VAD from userdata, or load it if not available
        vad = ctx.proc.userdata.get("vad")
        if vad is None:
            logger.warning("VAD not found in userdata, loading new instance")
            vad = silero.VAD.load(activation_threshold=0.5)
        
        session = AgentSession(
            # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
            # Deepgram requires DEEPGRAM_API_KEY environment variable
            stt=deepgram.STT(model="nova-3"),
            # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
            # Google Gemini requires GOOGLE_API_KEY environment variable
            llm=google.LLM(model="gemini-2.5-flash"),
            # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
            # Deepgram requires DEEPGRAM_API_KEY environment variable
            # Available voices: aura-2-andromeda-en, aura-2-arcas-en, aura-2-athena-en, aura-2-hera-en, aura-2-orpheus-en, aura-2-apollo-en, aura-2-zeus-en
            tts=deepgram.TTS(model="aura-2-andromeda-en"),
            # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
            # See more at https://docs.livekit.io/agents/build/turns
            turn_detection=MultilingualModel(),
            vad=vad,
            # allow the LLM to generate a response while waiting for the end of turn
            # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
            preemptive_generation=False,  # to not to bottleneck free tier api
            # Noise/filler word filtering: require at least 0.6s of speech and 2 words to trigger interruption
            # This filters out short noises and filler words like "yeah", "ok", "um"
            min_interruption_duration=0.6,
            min_interruption_words=2,
            # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
            # when it's detected, you may resume the agent's speech
            resume_false_interruption=True,
            false_interruption_timeout=1.0,
        )
    except Exception as e:
        logger.error(f"Failed to initialize AgentSession: {e}", exc_info=True)
        # Assuming we want to crash/return if initialization fails
        return

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

    try:
        logger.info(f"Starting agent session in room: {ctx.room.name}")
        await session.start(
            agent=MyAgent(),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                # Note: For advanced noise cancellation, uncomment and use Krisp BVC:
                # audio_input=room_io.AudioInputOptions(
                #     noise_cancellation=noise_cancellation.BVC(),
                # ),
                audio_output=room_io.AudioOutputOptions(),
            ),
        )
        logger.info(f"Agent session ended in room: {ctx.room.name}")
    except Exception as e:
        logger.error(f"Failed to start or run agent session: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)
