import logging

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, AgentServer, JobContext, JobProcess, cli
from livekit.plugins import silero

logger = logging.getLogger("backchanneling-agent")
load_dotenv()


class SimpleAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful assistant named Kelly. "
                "When asked to explain something, give detailed explanations. "
                "Keep responses conversational and avoid special characters."
            )
        )

    async def on_enter(self):
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2",
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=True,
    )

    await session.start(agent=SimpleAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)