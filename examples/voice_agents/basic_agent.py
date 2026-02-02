import logging
import os
import sys

# CRITICAL: Ensure workspace livekit-agents is prioritized BEFORE any imports
# This must happen before dotenv or any other imports that might trigger livekit imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_livekit_agents_path = os.path.join(_workspace_root, "livekit-agents")
# Remove from path if already there, then insert at position 0
if _livekit_agents_path in sys.path:
    sys.path.remove(_livekit_agents_path)
sys.path.insert(0, _livekit_agents_path)

# Add all plugin paths BEFORE any imports
_plugin_paths = [
    os.path.join(_workspace_root, "livekit-plugins", "livekit-plugins-groq"),
    os.path.join(_workspace_root, "livekit-plugins", "livekit-plugins-openai"),
    os.path.join(_workspace_root, "livekit-plugins", "livekit-plugins-silero"),
    os.path.join(_workspace_root, "livekit-plugins", "livekit-plugins-turn-detector"),
    os.path.join(_workspace_root, "livekit-plugins", "livekit-plugins-cartesia"),
]
for _plugin_path in _plugin_paths:
    if _plugin_path in sys.path:
        sys.path.remove(_plugin_path)
    sys.path.insert(0, _plugin_path)

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
from livekit.plugins import cartesia, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import Groq plugin
try:
    from livekit.plugins import groq
except ImportError:
    # Try direct import
    try:
        from livekit.plugins.groq import LLM, STT, TTS

        class GroqNamespace:
            LLM = LLM
            STT = STT
            TTS = TTS

        groq = GroqNamespace()
    except ImportError as e:
        raise ImportError(
            f"Groq plugin not found. Please install it:\n"
            f"  uv pip install -e livekit-plugins/livekit-plugins-groq\n"
            f"Or: pip install livekit-plugins-groq\n"
            f"Original error: {e}"
        ) from e

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()


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

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
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
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # Using Groq STT (whisper-large-v3-turbo) - fast and accurate
        stt=groq.STT(model="whisper-large-v3-turbo"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # Using Groq LLM (llama-3.3-70b-versatile) - fast inference with high quality
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # Using Cartesia TTS (Groq TTS playai-tts has been decommissioned)
        # Cartesia provides high-quality, fast TTS with natural voices
        tts=cartesia.TTS(),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
        # when it's detected, you may resume the agent's speech
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

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

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # uncomment to enable the Krisp BVC noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
