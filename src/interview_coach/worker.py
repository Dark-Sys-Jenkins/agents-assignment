"""LiveKit worker entrypoint."""

from __future__ import annotations

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, cli
from livekit.plugins import openai, silero

from .agent import InterviewCoach
from .settings import Settings

load_dotenv()

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    settings = Settings.from_env()
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
        llm=openai.LLM(model=settings.llm_model),
        tts=openai.TTS(voice=settings.tts_voice),
    )
    await session.start(agent=InterviewCoach(settings), room=ctx.room)
    await session.generate_reply(
        instructions=(
            "Welcome the candidate and ask if they are ready to begin "
            "the practice interview."
        )
    )


def main() -> None:
    """Run the LiveKit agent CLI."""
    cli.run_app(server)


if __name__ == "__main__":
    main()
