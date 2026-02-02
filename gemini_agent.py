import logging
import os

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
)
from livekit.plugins import silero, google, deepgram, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("gemini-agent")

class GeminiAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Gemini. You are a helpful AI assistant powered by Google."
            "Interactions are via voice, so keep responses concise and conversational."
            "Avoid using special characters like asterisks or complex markdown."
            "You are friendly, professional, and here to help.",
        )

    async def on_enter(self):
        # Generate an initial greeting when the agent enters the session
        self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
    # Configure Gemini LLM using the Google plugin
    # This will automatically use the GOOGLE_API_KEY env var
    gemini_llm = google.LLM(model="gemini-2.0-flash-001")

    session = AgentSession(
        # STT powered by Deepgram as per your key
        stt=deepgram.STT(),
        llm=google.LLM(model="gemini-2.0-flash"),        # TTS powered by ElevenLabs
        tts=elevenlabs.TTS(),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

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
        agent=GeminiAgent(),
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(server)
