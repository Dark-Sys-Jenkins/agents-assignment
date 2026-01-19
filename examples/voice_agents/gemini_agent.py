import logging
import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import silero
from livekit.plugins.google.realtime import RealtimeModel

logger = logging.getLogger("gemini-agent")

load_dotenv()


class GeminiAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful and friendly assistant. Keep your responses concise.",
            llm=RealtimeModel(
                api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash-exp",
                instructions="You are a helpful and friendly assistant.",
            ),
        )

    async def on_enter(self):
        pass


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Initialize the agent here to pass to session
    agent = GeminiAgent()
    
    session = AgentSession(
        llm=agent.llm,
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                echo_cancellation=True,
                noise_suppression=True,
                auto_gain_control=True,
            ),
        ),
    )


if __name__ == "__main__":
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        logger.error("GOOGLE_API_KEY or GEMINI_API_KEY must be set in .env or environment variables")
        exit(1)
        
    cli.run_app(server)
