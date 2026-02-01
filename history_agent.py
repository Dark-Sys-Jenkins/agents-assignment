from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
)
from livekit.plugins import google
from google.genai import types
from interrupt_controller import InterruptController
from logging_utils import configure_logger
from session_handlers import (
    create_usage_logger,
    register_interrupt_handlers,
    register_metrics_handlers,
)
from livekit.agents.job import get_job_context
from livekit.agents.llm import function_tool
from livekit.plugins import  silero
from config import llm, stt, tts, ignore_words, interrupt_words

logger = configure_logger("history-agent", log_file=Path(__file__).parent / "history_agent.log")


# uncomment to enable Krisp BVC noise cancellation, currently supported on Linux and MacOS
# from livekit.plugins import noise_cancellation

## The storyteller agent is a multi-agent that can handoff the session to another agent.
## This example demonstrates more complex workflows with multiple agents.
## Each agent could have its own instructions, as well as different STT, LLM, TTS,
## or realtime models.


common_instructions = (
    "Your name is Echo. You are a history teller that interacts with the user via voice."
    "You are a history expert."
)


@dataclass
class StoryData:
    # Shared data that's used by the storyteller agent.
    # This structure is passed as a parameter to function calls.

    name: Optional[str] = None
    location: Optional[str] = None


class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"{common_instructions} Your goal is to gather a few pieces of "
            "information from the user to make the story personalized and engaging."
            "Make user aware of history facts related to their location."
            "You should ask the user for their name and where they are from."
            "Be conservative in speaking. Tell things briefly"
            "Start the conversation with a short introduction.",
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        logger.info("IntroAgent entering the session, generating intro message")
        self.session.generate_reply()

    @function_tool
    async def information_gathered(
        self,
        context: RunContext[StoryData],
        name: str,
        location: str,
    ):
        """Called when the user has provided the information needed to make the story
        personalized and engaging.

        Args:
            name: The name of the user
            location: The location of the user
        """

        context.userdata.name = name
        context.userdata.location = location

        story_agent = StoryAgent(name, location)
        # by default, StoryAgent will start with a new context, to carry through the current
        # chat history, pass in the chat_ctx
        # story_agent = StoryAgent(name, location, chat_ctx=self.chat_ctx)

        logger.info(
            "switching to the story agent with the provided user data: %s", context.userdata
        )
        return story_agent, "Let's start the story!"


class StoryAgent(Agent):
    def __init__(self, name: str, location: str, *, chat_ctx: Optional[ChatContext] = None) -> None:
        super().__init__(
            instructions=f"{common_instructions}. You should use the user's information in "
            "order to make the story personalized."
            "create the entire story, weaving in elements of their information, and make it "
            "interactive, occasionally interating with the user."
            "do not end on a statement, where the user is not expected to respond."
            "when interrupted, ask if the user would like to continue or end."
            f"The user's name is {name}, from {location}.",
            # Disable server-side turn detection to allow custom interrupt logic
            llm=google.realtime.RealtimeModel(
                voice="echo",
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
                ),
            ),
            tts=None,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        # when the agent is added to the session, we'll initiate the conversation by
        # using the LLM to generate a reply
        logger.info("StoryAgent entering the session, generating first story message")
        self.session.generate_reply()

    @function_tool
    async def story_finished(self, context: RunContext[StoryData]):
        """When you are fininshed telling the story (and the user confirms they don't
        want anymore), call this function to end the conversation."""
        # interrupt any existing generation
        logger.info("Story finished, ending the session")
        self.session.interrupt()

        # generate a goodbye message and hang up
        # awaiting it will ensure the message is played out before returning
        await self.session.generate_reply(
            instructions=f"say goodbye to {context.userdata.name}", allow_interruptions=False
        )

        
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))
        logger.info("Room disconnected successfully")


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession[StoryData](
        vad=ctx.proc.userdata["vad"],
        # any combination of STT, LLM, TTS, or realtime API can be used
        # llm=openai.LLM(model="gpt-4o-mini"),
        llm=llm,
        # stt=deepgram.STT(model="nova-3"),
        stt=stt,
        # tts=openai.TTS(voice="echo"),
        tts=tts,
        userdata=StoryData(),
        # Use manual turn detection to allow custom interrupt logic via should_interrupt()
        turn_detection="manual",
    )

    # interrupt controller to decide when to interrupt agent speech
    interrupt_controller = InterruptController(ignore_words=ignore_words, interrupt_words=interrupt_words)

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()
    register_metrics_handlers(session, usage_collector, logger)
    register_interrupt_handlers(session, interrupt_controller, logger)
    create_usage_logger(ctx, usage_collector, logger)

    await session.start(
        agent=IntroAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)