import os
import re
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

logger = logging.getLogger("basic-agent")
load_dotenv()

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and natural. "
                "Do not use emojis, markdown, or special formatting. "
                "You are curious, friendly, and slightly humorous. "
                "Speak English only."
            )
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        logger.info(f"Looking up weather for {location}")
        return "It is sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm

class SmartInterruptionManager:
    def __init__(self, session, soft_words):
        self.session = session
        self.soft_words = set(w.strip().lower() for w in soft_words)

    def _is_agent_speaking(self) -> bool:
        return self.session.output.audio.is_playing()

    def _is_soft_only(self, text: str) -> bool:
        if not text:
            return True
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        if not tokens:
            return True
        return all(tok in self.soft_words for tok in tokens)

    def on_user_transcript(self, ev):
        text = (ev.text or "").strip()
        speaking = self._is_agent_speaking()

        logger.info(f"User transcript='{text}' | agent_speaking={speaking}")

        # If agent is silent → normal flow
        if not speaking:
            return

        # Agent is speaking
        if self._is_soft_only(text):
            logger.info("Soft input detected → continuing speech")
            return

        # HARD INTERRUPT
        logger.info("Hard interrupt detected → stopping agent speech")
        self.session.output.audio.clear_buffer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        allow_interruptions=True,   # MUST stay True
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=False,
    )

    soft_words = os.getenv(
        "SOFT_WORDS",
        "yeah,ok,okay,uh-huh,hmm,mhm,yep,yup,right,aha"
    ).split(",")

    logger.info(f"Soft words: {soft_words}")

    interrupt_manager = SmartInterruptionManager(session, soft_words)

    @session.on("user_transcript")
    def _on_user_transcript(ev):
        interrupt_manager.on_user_transcript(ev)

    # Metrics
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
