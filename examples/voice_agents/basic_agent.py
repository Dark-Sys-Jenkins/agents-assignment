import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import our custom interruption handling
from interruption_handler import InterruptionHandler
from interruption_config import DEFAULT_CONFIG

logger = logging.getLogger("basic-agent")

load_dotenv()


class MyAgent(Agent):
    def __init__(self, interruption_handler: InterruptionHandler) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
            "With that in mind keep your responses concise and to the point. "
            "Do not use emojis, asterisks, markdown, or other special characters in your responses. "
            "You are curious and friendly, and have a sense of humor. "
            "You will speak english to the user. "
            "When users say 'yeah', 'ok', or 'hmm' while you're speaking, it means they're listening - "
            "continue your explanation without stopping.",
        )
        self.interruption_handler = interruption_handler

    async def on_enter(self):
        # When the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Create interruption handler instance
    interruption_handler = InterruptionHandler(DEFAULT_CONFIG)
    
    session = AgentSession(
        # Speech-to-text (STT)
        stt="deepgram/nova-3",
        # Large Language Model (LLM)
        llm="openai/gpt-4o-mini",
        # Text-to-speech (TTS)
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Allow LLM to generate response while waiting for end of turn
        preemptive_generation=True,
        # DISABLE the built-in false interruption handling
        # We'll handle this with our custom logic
        resume_false_interruption=False,
        false_interruption_timeout=0.0,
    )

    # Track agent state based on TTS events
    @session.on("agent_speech_started")
    def _on_agent_speech_started():
        """Called when agent starts speaking (TTS begins)."""
        logger.info("🎤 Agent started speaking")
        interruption_handler.set_agent_speaking(True)

    @session.on("agent_speech_stopped")
    def _on_agent_speech_stopped():
        """Called when agent stops speaking (TTS ends)."""
        logger.info("🔇 Agent stopped speaking")
        interruption_handler.set_agent_speaking(False)

    # Intercept user speech for intelligent interruption handling
    @session.on("user_speech_committed")
    def _on_user_speech_committed(transcript: str):
        """
        Called when user speech is finalized (STT provides final transcription).
        This is where we decide if the interruption should be allowed.
        """
        logger.info(f"👤 User said: '{transcript}'")
        
        # Analyze the input
        analysis = interruption_handler.analyze_input(transcript)
        logger.info(f"📊 Analysis: {analysis}")
        
        # Check if interruption should be allowed
        should_allow = interruption_handler.should_allow_interruption(transcript)
        
        if not should_allow:
            # This is backchanneling while agent is speaking - IGNORE IT
            logger.warning(f"🚫 IGNORING backchannel: '{transcript}' (agent continues)")
            # Tell the session to resume the agent's speech if it was paused
            session.resume_agent_speech()
            return
        
        # This is a valid interruption or agent is silent - process normally
        logger.info(f"✅ PROCESSING input: '{transcript}'")
        # The default behavior will handle this

    # Log metrics as they are emitted
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(interruption_handler),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Uncomment to enable Krisp BVC noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)