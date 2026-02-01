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
    inference
)
from livekit.agents.job import get_job_context
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, silero, elevenlabs

load_dotenv()

logger = logging.getLogger("multi-agent")

# Words we want the agent to keep talking through
IGNORE_WORDS = ["yeah", "okay", "ok", "i see", "uh-huh", "go on"]
# Words that should force an immediate stop
HARD_COMMANDS = ["stop", "wait", "hold on", "shut up", "pause"]

common_instructions = (
    "Your name is Echo. You are a story teller. "
    "IMPORTANT: If the user says filler words like 'Yeah' or 'Okay', keep your flow. "
    "Only stop if the user asks a specific question or gives a direct command."
)

@dataclass
class StoryData:
    name: Optional[str] = None
    location: Optional[str] = None

class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"{common_instructions} Your goal is to gather the user's name and location. "
            "Start with a short, friendly introduction.",
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

        story_agent = StoryAgent(name, location)
        logger.info(f"Switching to StoryAgent for: {name}")
        return story_agent, "Great! I have everything I need. Let's begin."

class StoryAgent(Agent):
    def __init__(self, name: str, location: str, *, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            instructions=f"{common_instructions}. Tell a personalized story for {name} from {location}. "
            "Maintain the story flow unless explicitly interrupted.",
            llm=inference.LLM(model="gemini-2.0-flash"),
            tts=elevenlabs.TTS(), 
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        await self.session.generate_reply()

    @function_tool
    async def story_finished(self, context: RunContext[StoryData]):
        self.session.interrupt()
        await self.session.generate_reply(
            instructions=f"Say a warm goodbye to {context.userdata.name}", 
            allow_interruptions=False
        )
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession[StoryData](
        vad=ctx.proc.userdata["vad"],
        llm=inference.LLM(model="gemini-2.0-flash"),
        stt=deepgram.STT(model="nova-3"),
        tts=elevenlabs.TTS(),
        userdata=StoryData(),
    )

    session.min_endpointing_delay = 0.6 
    @session.on("user_input_transcribed")
    def on_transcript(transcript: str):
        text = transcript.lower().strip()
        
        if any(cmd in text for cmd in HARD_COMMANDS):
            logger.info(f"Hard command '{text}' detected. Interrupting.")
            session.interrupt() 
        
        elif text in IGNORE_WORDS:
            logger.info(f"Ignoring filler: {text}")

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    ctx.add_shutdown_callback(lambda: logger.info(f"Usage: {usage_collector.get_summary()}"))

    await session.start(agent=IntroAgent(), room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)
