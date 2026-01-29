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

from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# -------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("assessment-agent")

# -------------------------------------------------------------------
# INTERRUPTION CONFIG
# -------------------------------------------------------------------

FILLER_WORDS = {
    "ok", "okay", "yeah", "yep", "uh-huh", "uh huh",
    "hmm", "mm", "mhmm", "right", "cool", "oh"
}

INTERRUPT_WORDS = {
    "stop", "wait", "hold on", "pause", "cancel"
}

# -------------------------------------------------------------------
# AGENT IMPLEMENTATION
# -------------------------------------------------------------------

class AssessmentAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "Your name is Kelly. "
                "You tell long, engaging stories when asked. "
                "Do not restart sentences after interruptions. "
                "If interrupted, continue from where you stopped. "
                "Ignore listener acknowledgements like yeah or hmm."
            )
        )

        # --- Speech state ---
        self.is_speaking = False
        self.full_response = ""
        self.spoken_offset = 0

    # ---------------------------------------------------------------

    async def on_enter(self):
        logger.info("Agent entered room")
        await self.session.generate_reply()

    # ---------------------------------------------------------------
    # SPEECH STREAM TRACKING (CRITICAL FIX)
    # ---------------------------------------------------------------

    async def on_agent_speech_started(self):
        self.is_speaking = True
        logger.info("Agent started speaking")

    async def on_agent_speech_chunk(self, chunk: str):
        """
        LiveKit streams TTS chunks here.
        We track exactly what was spoken.
        """
        self.full_response += chunk
        self.spoken_offset += len(chunk)

    async def on_agent_speech_ended(self):
        self.is_speaking = False
        logger.info("Agent finished speaking")

    # ---------------------------------------------------------------
    # USER INPUT HANDLING
    # ---------------------------------------------------------------

    async def on_user_transcript(self, transcript):
        if not transcript.final:
            return

        text = transcript.text.lower().strip(" .,!?")
        words = text.split()

        logger.info(f"User said: {text}")

        # -----------------------------------------------------------
        # 1️⃣ Ignore single-word fillers completely
        # -----------------------------------------------------------
        if len(words) == 1 and text in FILLER_WORDS:
            logger.info("Ignoring filler word")
            return

        # -----------------------------------------------------------
        # 2️⃣ True interruption → pause speech
        # -----------------------------------------------------------
        if any(w in text for w in INTERRUPT_WORDS) and self.is_speaking:
            logger.info("True interruption detected")
            await self.session.interrupt()
            return

        # -----------------------------------------------------------
        # 3️⃣ Normal conversation
        # -----------------------------------------------------------
        await super().on_user_transcript(transcript)

    # ---------------------------------------------------------------
    # RESUME LOGIC (THE KEY FIX)
    # ---------------------------------------------------------------

    async def resume_from_checkpoint(self):
        """
        Resume ONLY what wasn't spoken yet
        """
        remaining = self.full_response[self.spoken_offset:]

        if remaining.strip():
            logger.info("Resuming from checkpoint")
            await self.session.say(remaining)

# -------------------------------------------------------------------
# SERVER SETUP
# -------------------------------------------------------------------

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2",
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),

        # 🔑 THESE SETTINGS MATTER
        allow_interruptions=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.5,
        preemptive_generation=False,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    ctx.add_shutdown_callback(
        lambda: logger.info(f"Usage: {usage_collector.get_summary()}")
    )

    await session.start(
        agent=AssessmentAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

if __name__ == "__main__":
    cli.run_app(server)
