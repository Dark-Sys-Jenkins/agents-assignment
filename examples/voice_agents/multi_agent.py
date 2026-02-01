import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from livekit import api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    metrics,
    inference,
)
from livekit.agents.job import get_job_context
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, silero, elevenlabs, openai

load_dotenv()

logger = logging.getLogger("interrupt-demo")

IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh", "uh-huh",
    "right", "mm", "aha", "i", "see"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "cancel", "hold", "pause"
}


def tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {w.lower() for w in text.strip().split()}

class StrictSemanticSession(AgentSession):
    """
    Guarantees:
    - Ignore words cause ZERO pause / ZERO resume
    - Interrupt words cut immediately
    """

    def _interrupt_by_audio_activity(self) -> None:
        if self._current_speech is None:
            return super()._interrupt_by_audio_activity()

        if self._audio_recognition is None:
            return

        text = self._audio_recognition.current_transcript or ""
        tokens = tokenize(text)
        if tokens and tokens.issubset(IGNORE_WORDS):
            return

        if tokens & INTERRUPT_WORDS:
            pass  
        else:
            
            return

        return super()._interrupt_by_audio_activity()


common_instructions = (
    "Your name is Meena. You are a calm storyteller. "
    "You speak in long, uninterrupted narratives. "
    "Do not stop unless explicitly told to stop."
)


@dataclass
class StoryData:
    name: Optional[str] = None
    location: Optional[str] = None


class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                f"{common_instructions} "
                "Ask the user their name and location briefly."
            )
        )

    async def on_enter(self):
        await self.session.generate_reply(allow_interruptions=False)

    @function_tool
    async def information_gathered(
        self,
        context: RunContext[StoryData],
        name: str,
        location: str,
    ):
        context.userdata.name = name
        context.userdata.location = location
        return StoryAgent(name, location), "Alright, let me tell you a story."


class StoryAgent(Agent):
    def __init__(self, name: str, location: str, *, chat_ctx: Optional[ChatContext] = None):
        super().__init__(
            instructions=(
                f"{common_instructions} "
                f"Tell a long, slow, immersive story for {name} from {location}. "
                "Speak continuously in multiple paragraphs."
            ),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        await self.session.generate_reply()

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = StrictSemanticSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-3"),
        llm=inference.LLM(model="google/gemini-2.0-flash"),
        tts=elevenlabs.TTS(),
        userdata=StoryData(),
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    await session.start(agent=IntroAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
