import logging
import os
import re
from enum import Enum
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    UserStateChangedEvent,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# -------------------------------------------------
# ENV + LOGGER
# -------------------------------------------------

load_dotenv()
bot_logger = logging.getLogger("history-voice-agent")

# -------------------------------------------------
# INTERRUPTION CLASSIFICATION
# -------------------------------------------------

class InterruptionType(Enum):
    PASSIVE = "passive"
    STOP = "stop"
    ACTIVE = "active"
    EMPTY = "empty"


class TranscriptClassifier:
    PASSIVE_TERMS = {
        "yeah", "ok", "okay", "hmm", "right",
        "uh", "uh-huh", "yes", "aha", "cool", "nice"
    }
    
    STOP_TERMS = {
        "stop", "wait", "cancel", "pause",
        "no", "hold", "quiet", "kelly", "hush"
    }
    
    @staticmethod
    def normalize(text: str) -> list[str]:
        return [w for w in re.split(r"[^a-z]+", text.lower()) if w]
    
    @classmethod
    def classify(cls, text: str) -> InterruptionType:
        words = cls.normalize(text)
        
        if not words:
            return InterruptionType.EMPTY
        
        # Check for stop commands first (highest priority)
        if any(word in cls.STOP_TERMS for word in words):
            return InterruptionType.STOP
        
        # Check if all words are passive
        if all(word in cls.PASSIVE_TERMS for word in words):
            return InterruptionType.PASSIVE
        
        
        return InterruptionType.ACTIVE


class InterruptionHandler:
    def __init__(self, session: AgentSession):
        self.session = session
        self.classifier = TranscriptClassifier()
    
    def handle(self, text: str, agent_state: str) -> None:
        interrupt_type = self.classifier.classify(text)
        words = self.classifier.normalize(text)
        
        bot_logger.info("[STT] '%s' | %s", text, words)
        
        # Only process interruptions when agent is speaking
        if agent_state != "speaking":
            return
        
        # Route based on classification
        if interrupt_type == InterruptionType.STOP:
            bot_logger.warning("[INTERRUPT] stop command")
            self.session.interrupt(force=True)
        elif interrupt_type == InterruptionType.PASSIVE:
            bot_logger.info("[IGNORE] backchannel")
        elif interrupt_type == InterruptionType.ACTIVE:
            bot_logger.warning("[INTERRUPT] general speech")
            self.session.interrupt(force=True)
        # EMPTY type is implicitly ignored


# -------------------------------------------------
# AGENT
# -------------------------------------------------

class HistoryAssistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "Your name is Kelly. You are a knowledgeable historian. "
                "Explain historical topics clearly and concisely. "
                "Avoid emojis, markdown, or special symbols. "
                "Keep a friendly and engaging tone."
            )
        )

    async def on_enter(self):
        bot_logger.info("[AGENT] entering session")
        self.session.generate_reply()

    @function_tool
    async def historical_lookup(self, context: RunContext, topic: str):
        bot_logger.info("[TOOL] lookup topic: %s", topic)
        return f"Here is some historical context about {topic}."


# -------------------------------------------------
# SERVER
# -------------------------------------------------

agent_server = AgentServer()


def prewarm(proc: JobProcess):
    bot_logger.info("[PREWARM] loading VAD")
    proc.userdata["vad_model"] = silero.VAD.load()
    bot_logger.info("[PREWARM] VAD ready")


agent_server.setup_fnc = prewarm


# -------------------------------------------------
# SESSION ENTRYPOINT
# -------------------------------------------------

@agent_server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    bot_logger.info("[SESSION] room=%s", ctx.room.name)
    
    llm_engine = openai.LLM(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="google/gemini-2.0-flash-001",
    )

    voice_session = AgentSession(
        stt="deepgram/nova-3",
        llm=llm_engine,
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad_model"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
    )

    usage_tracker = metrics.UsageCollector()
    interruption_handler = InterruptionHandler(voice_session)

    @voice_session.on("metrics_collected")
    def collect_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_tracker.collect(ev.metrics)

    async def log_usage():
        bot_logger.info("[USAGE] %s", usage_tracker.get_summary())

    ctx.add_shutdown_callback(log_usage)

    @voice_session.on("agent_state_changed")
    def agent_state(ev: AgentStateChangedEvent):
        bot_logger.info(
            "[STATE] agent %s → %s",
            ev.old_state,
            ev.new_state,
        )

    @voice_session.on("user_state_changed")
    def user_state(ev: UserStateChangedEvent):
        bot_logger.info(
            "[STATE] user %s → %s",
            ev.old_state,
            ev.new_state,
        )

    @voice_session.on("user_input_transcribed")
    def handle_transcript(ev: UserInputTranscribedEvent):
        if not ev.is_final:
            return

        text = (ev.transcript or "").strip()
        if not text:
            return

        interruption_handler.handle(text, voice_session.agent_state)

    await voice_session.start(
        agent=HistoryAssistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":
    os.makedirs("proof", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)-18s %(message)s",
    )

    file_logger = logging.FileHandler(
        "proof/history-agent-log.txt", encoding="utf-8"
    )
    file_logger.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-5s %(name)-18s %(message)s")
    )

    logging.getLogger().addHandler(file_logger)

    bot_logger.info("🚀 History Voice Agent starting")
    cli.run_app(agent_server)