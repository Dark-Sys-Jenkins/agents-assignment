import logging
from dotenv import load_dotenv
import asyncio

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

# Load environment variables
load_dotenv()

logger = logging.getLogger("basic-agent")

# 1. Configurable Ignore and Interrupt Lists [cite: 37]
IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "uh-huh", "right", "aha", "hmm"}
INTERRUPT_WORDS = {"stop", "wait", "no", "pause", "hold"}

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and to the point. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "You are curious, friendly, and have a sense of humor. "
                "Speak English to the user."
            ),
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather information."""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    # Track speaking state locally to this session 
    agent_is_speaking = False
    just_interrupted = False

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
        # Handling "false start" interruptions by allowing the stream to resume
        # if our logic layer determines it was a filler word [cite: 47]
        resume_false_interruption=False,
        false_interruption_timeout=1.2, 
    )

    # 2. State-Based Filtering: Track when agent is speaking 
    @session.on("agent_audio_start")
    def _on_agent_audio_start():
        nonlocal agent_is_speaking
        agent_is_speaking = True

    @session.on("agent_audio_end")
    def _on_agent_audio_end():
        nonlocal agent_is_speaking
        agent_is_speaking = False


    @session.on("user_transcript")
    def _on_user_transcript(transcript: str):
        nonlocal agent_is_speaking, just_interrupted

        text = transcript.lower().strip()
        words = text.split()
        if not words:
            return

        has_command = any(w in words for w in INTERRUPT_WORDS)
        is_only_filler = all(w in IGNORE_WORDS for w in words)

        # HARD COMMANDS
        if has_command:
            if agent_is_speaking:
                just_interrupted = True
                asyncio.create_task(session.interrupt())
            # If agent is already silent, do NOTHING
            return
        
        # If we just interrupted, do NOT auto-generate a reply
        if just_interrupted:
            just_interrupted = False
            return

        if agent_is_speaking:
            if is_only_filler:
                # Small debounce to let audio pipeline settle
                return
            else:
                asyncio.create_task(session.interrupt())
        else:
            session.generate_reply()


    # Metrics and Usage
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
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)