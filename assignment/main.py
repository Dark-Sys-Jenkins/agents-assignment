import asyncio
import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    UserStateChangedEvent,
    cli,
)
from livekit.plugins import cartesia, deepgram, groq, silero

from state_manager import StateManager
from transcript_handler import handle_transcript

logger = logging.getLogger("agent")

load_dotenv()

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=groq.LLM(model="llama-3.1-8b-instant"),
        stt=deepgram.STT(),
        tts=cartesia.TTS(),
        user_away_timeout=12.5,
    )

    state_manager = StateManager()

    inactivity_task: asyncio.Task | None = None

    async def user_presence_task():
        for _ in range(3):
            await session.generate_reply(
                instructions="The user has been inactive. Check if they are present."
            )
            await asyncio.sleep(10)

        session.shutdown()

    @session.on("user_state_changed")
    def _user_state_changed(ev: UserStateChangedEvent):
        nonlocal inactivity_task
        if ev.new_state == "away":
            inactivity_task = asyncio.create_task(user_presence_task())
            return

        if inactivity_task is not None:
            inactivity_task.cancel()

    # agent state tracking
    @session.on("agent_state_changed")
    def _agent_state_changed(ev):
        state_manager.update_agent_state(ev.new_state)

    # transcript handling
    @session.on("user_transcript")
    def _handle_transcript(ev):
        handle_transcript(session, state_manager, ev.text)

    await session.start(
        agent=Agent(instructions="You are a helpful assistant."),
        room=ctx.room
    )


if __name__ == "__main__":
    cli.run_app(server)