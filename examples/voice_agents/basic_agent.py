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
    RunContext,
    UserInputTranscribedEvent,
    AgentStateChangedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agent_intruppter_checker import decision_maker, Category, write_report

logger = logging.getLogger("basic-agent")
load_dotenv()


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Bellatrix. "
                "You are a friendly, helpful English conversational AI assistant."
                "You can discuss any topic naturally and explain concepts clearly."
                "Do not use emojis, markdown formatting, or special characters."
                "Keep responses concise and conversational."
                "You should only use tools when they are clearly useful."
            ),
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
    logger.info("Prewarming VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("VAD model loaded successfully")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="google/gemini-2.5-flash",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
        min_interruption_duration=0.4,
        min_interruption_words=1,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Session usage summary: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    class AgentState:
        speaking: bool = False

    state = AgentState()

    @session.on("agent_state_changed")
    def on_state_change(ev: AgentStateChangedEvent):
        state.speaking = ev.new_state == "speaking"

    @session.on("user_input_transcribed")
    def on_user_speech(event: UserInputTranscribedEvent):
        text = (event.transcript or "").strip()
        if not text or not state.speaking:
            return

        res = decision_maker(text)

        logger.debug(
            f"Decision: text='{text}', category={res.category}, interrupt={res.interrupt}"
        )
        
        write_report(text, res.category, res.interrupt)

        if not event.is_final:
            if res.interrupt:
                logger.info(f"INTERRUPT detected (interim): '{text}'")
                session.interrupt(force=True)
            return

        if res.category == Category.BACKCHANNEL:
            logger.info(f"Ignoring backchannel: '{text}'")
            session.clear_user_turn()
            return

        if res.category == Category.INTERRUPT:
            logger.info(f"INTERRUPT command: '{text}'")
            session.interrupt(force=True)
            return

        if res.category == Category.MIXED:
            if len(text.split()) >= 3:
                logger.info(f"INTERRUPT (mixed): '{text}'")
                session.interrupt(force=True)
            else:
                session.clear_user_turn()

    logger.info("Starting agent session...")
    write_report("Starting agent session...", Category.UNKNOWN, False)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)