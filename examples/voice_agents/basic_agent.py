import logging
import re
import asyncio
from enum import Enum

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

# -------------------------------------------------
# Setup
# -------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("basic-agent")

load_dotenv()

# -------------------------------------------------
# Semantic preprocessing / intent classification
# -------------------------------------------------

IGNORE_WORDS = {
    "yeah",
    "yes",
    "ok",
    "okay",
    "hmm",
    "uh",
    "uh-huh",
    "right",
    "aha",
}

INTERRUPT_WORDS = {
    "stop",
    "wait",
    "pause",
    "cancel",
    "hold on",
    "no",
}


class UserIntent(Enum):
    IGNORE = "ignore"
    INTERRUPT = "interrupt"
    NORMAL = "normal"


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def classify_input(transcript: str, agent_is_speaking: bool) -> UserIntent:
    if not transcript:
        return UserIntent.IGNORE

    words = set(_normalize(transcript).split())

    if agent_is_speaking:
        if words & INTERRUPT_WORDS:
            return UserIntent.INTERRUPT

        if words and words.issubset(IGNORE_WORDS):
            return UserIntent.IGNORE

        return UserIntent.INTERRUPT

    return UserIntent.NORMAL


# -------------------------------------------------
# Agent definition (model behavior unchanged)
# -------------------------------------------------

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and to the point. "
                "Do not use emojis, markdown, or special characters. "
                "You are friendly, curious, and speak English."
            )
        )

    async def on_enter(self):
        # Initial model invocation preserved
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        logger.info(f"Looking up weather for {location}")
        return "It is sunny with a temperature of 70 degrees."


# -------------------------------------------------
# Server setup
# -------------------------------------------------

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm

agent_is_speaking = False
agent_is_generating = False


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    global agent_is_speaking, agent_is_generating

    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # -------------------------------------------------
    # Track speaking + generation state
    # -------------------------------------------------

    @session.on("agent_speech_started")
    def _on_agent_speech_started():
        global agent_is_speaking
        agent_is_speaking = True
        logger.info("Agent speech started")

    @session.on("agent_speech_finished")
    def _on_agent_speech_finished():
        global agent_is_speaking
        agent_is_speaking = False
        logger.info("Agent speech finished")

    @session.on("llm_generation_started")
    def _on_generation_started():
        global agent_is_generating
        agent_is_generating = True
        logger.info("LLM generation started")

    @session.on("llm_generation_finished")
    def _on_generation_finished():
        global agent_is_generating
        agent_is_generating = False
        logger.info("LLM generation finished")

    # -------------------------------------------------
    # Semantic preprocessing gate
    # -------------------------------------------------

    @session.on("user_transcript_final")
    def _on_user_transcript(transcript: str):
        intent = classify_input(transcript, agent_is_speaking)

        logger.info(
            f"User='{transcript}' | intent={intent.value} | "
            f"speaking={agent_is_speaking} | generating={agent_is_generating}"
        )

        # Explicit interrupt
        if intent == UserIntent.INTERRUPT:
            logger.info("Interrupt intent → stopping agent")
            asyncio.create_task(session.interrupt())
            return

        # 🔴 Critical fix: suppress generation on backchannels
        if intent == UserIntent.IGNORE:
            logger.info("Backchannel detected → suppressing generation")
            return

        # NORMAL input → allow LiveKit to proceed naturally

    # -------------------------------------------------
    # Metrics (unchanged)
    # -------------------------------------------------

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # -------------------------------------------------
    # Start agent
    # -------------------------------------------------

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    logger.info("RUNNING BASIC AGENT WITH GENERATION-SAFE BACKCHANNEL HANDLING")
    cli.run_app(server)
