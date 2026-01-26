import logging
import os
import re
import asyncio
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

from livekit.agents import StopResponse, UserInputTranscribedEvent


logger = logging.getLogger("basic-agent")
hard_mute = False
stop_latched = False


block_next_generation = False
is_agent_speaking = False
last_user_text = ""

load_dotenv()

# Soft backchannel words (ignored only while agent is speaking)
IGNORE_WORDS = [w.strip().lower() for w in os.getenv(
    "LK_IGNORE_WORDS",
    "yeah,yep,yup,yes,ok,okay,hmm,uh,uhh,uh-huh,uh huh,mhm,mm,right,alright,aha,ah,oh,cool,nice,got it,gotcha,sure"
).split(",")]


# Hard interruption words (always stop immediately)
STOP_WORDS = [w.strip().lower() for w in os.getenv(
    "LK_STOP_WORDS",
    "stop,wait,pause,hold,hold on,freeze,cancel,quiet,enough,shut up,no stop"
).split(",")]


# -------- Helper functions (small upgrade, still your logic) --------

def normalize_text(text: str):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s'-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str):
    return normalize_text(text).split()


def contains_stop_word(text: str):
    text = normalize_text(text)
    for stop in STOP_WORDS:
        pattern = r"\b" + re.escape(stop) + r"\b"
        if re.search(pattern, text):
            return True
    return False


def is_only_soft_words(text: str):
    tokens = tokenize(text)
    if not tokens:
        return False
    return all(t in IGNORE_WORDS for t in tokens)


# -------------------------------------------------------------------


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
    "If the user says stop, wait, pause, or hold on, you must immediately stop speaking and remain silent. "
    "Do not acknowledge, confirm, or respond when the user says stop. "
    "Keep your responses concise and to the point. "
    "Do not use emojis, asterisks, markdown, or other special characters in your responses. "
    "You are curious and friendly, and have a sense of humor. "
    "You will speak English to the user."
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    global is_agent_speaking, last_user_text, block_next_generation

    ctx.log_context_fields = {"room": ctx.room.name}

    # 🔴 Important: keep architecture, but reduce auto-interrupt sensitivity
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],

        preemptive_generation=True,

        # minimal tuning (not redesign)
        allow_interruptions=True,
        min_interruption_words=99,
        min_interruption_duration=10.0,
        resume_false_interruption=False,
        false_interruption_timeout=None, 
    )

    usage_collector = metrics.UsageCollector()

    # Track speaking state
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        global is_agent_speaking

        if ev.new_state == "speaking":
            is_agent_speaking = True
            logger.info("AGENT STATE = SPEAKING")
        else:
            if is_agent_speaking:
                logger.info("AGENT STATE = LISTENING (STOPPED SPEAKING)")
            is_agent_speaking = False


    # Main semantic interruption logic
    @session.on("user_input_transcribed")
    def _on_user_transcribed(ev: UserInputTranscribedEvent):
        global last_user_text, is_agent_speaking, block_next_generation

        text = (ev.transcript or "").lower().strip()
        last_user_text = text
        is_final = getattr(ev, "is_final", False)

        logger.info(f"USER SAID: {text} | final={is_final}")

        # 🔴 Hard stop → interrupt immediately (even partial, even mixed sentence)
        if contains_stop_word(text):
            logger.info("STOP WORD DETECTED — HARD INTERRUPT + FULL MUTE")

            global stop_latched, hard_mute
            stop_latched = True
            hard_mute = True
            block_next_generation = True

            session.interrupt()
            return

        # 🟡 Soft backchannel while speaking → suppress next generation
        if is_final and is_agent_speaking and is_only_soft_words(text):
            logger.info("SOFT WORD DURING SPEECH — SUPPRESS NEXT GENERATION")
            block_next_generation = True
            return


    @session.on("user_turn_completed")
    def _on_user_turn_completed():
        global last_user_text, is_agent_speaking
        global block_next_generation, hard_mute, stop_latched

        if hard_mute or block_next_generation:
            logger.info("HARD MUTE ACTIVE — FULL SUPPRESSION (NO AUDIO)")

            block_next_generation = False
            hard_mute = False
            stop_latched = False

            raise StopResponse()



    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    cli.run_app(server)
