import logging
import string
from typing import AsyncIterable, Optional

from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    AgentStateChangedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.agents import stt
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")
logger.setLevel(logging.INFO)

load_dotenv()

# Backchannel words to ignore ONLY when agent is speaking
IGNORE_WORDS = {
    "yeah", "yep", "yes",
    "uh-huh", "uhhuh", "uh", "huh",
    "hmm", "hmmm", "mm", "mmm", "mhm",
    "continue",
    "ok", "okay", "k",
    "right", "alright",
    "sure",
    "got", "it", "gotit",
    "i", "see",
    "ah", "oh", "ooh",
    "cool", "nice", "good",
    "mhmm", "mmhmm", "aha", "ahh",
}

# Words that MUST interrupt even while agent is speaking
STOP_WORDS = {
    "stop", "wait", "cancel", "hold", "no", "pause", "question", "but",
}


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep your responses concise and conversational. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "Speak in English."
            )
        )
        self.is_speaking = False

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

    # ---- IMPORTANT: Filter STT events BEFORE they cause interruptions ----
    async def stt_node(
        self,
        audio: AsyncIterable[rtc.AudioFrame],
        ctx: RunContext,
    ) -> Optional[AsyncIterable[stt.SpeechEvent]]:
        stt_stream = Agent.default.stt_node(self, audio, ctx)
        if stt_stream is None:
            return None
        return self._filter_stt_events(stt_stream)

    async def _filter_stt_events(
        self,
        stream: AsyncIterable[stt.SpeechEvent],
    ) -> AsyncIterable[stt.SpeechEvent]:
        async for event in stream:
            if event.type in (
                stt.SpeechEventType.INTERIM_TRANSCRIPT,
                stt.SpeechEventType.FINAL_TRANSCRIPT,
            ):
                text = event.alternatives[0].text if event.alternatives else ""
                if self._should_drop_transcript(text):
                    logger.info(f"IGNORING backchannel: '{text}' (speaking={self.is_speaking})")
                    continue

            yield event

    def _should_drop_transcript(self, text: str) -> bool:
        # Never drop anything if agent is not speaking
        if not self.is_speaking:
            return False

        clean_text = (
            text.lower()
            .translate(str.maketrans("", "", string.punctuation))
            .strip()
        )

        if not clean_text:
            return True

        words = set(clean_text.split())

        # If contains stop words, DO NOT drop (allow interruption)
        if any(w in STOP_WORDS for w in words):
            return False

        # Drop only if user said ONLY ignore words
        return words.issubset(IGNORE_WORDS)


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
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,

        # keep interruptions enabled but now filtered by our STT layer
        allow_interruptions=True,
        min_interruption_words=1,
        min_interruption_duration=0.2,

        # allow resuming from noise interruptions
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

    agent = MyAgent()

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        agent.is_speaking = (ev.new_state == "speaking")
        logger.info(f"Agent state: {ev.new_state}")

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
