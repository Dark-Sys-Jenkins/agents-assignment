from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai, silero

load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(language="en"),
        llm=openai.realtime.RealtimeModel(voice="alloy", turn_detection=None),
        ignore_interruption_words=["yeah", "ok", "hmm","mhm", "right", "uh-huh"],
        stop_interruption_words=["wait", "stop", "no"]
    )

    await session.start(
        agent=Agent(instructions="You are a helpful assistant."),
        room=ctx.room
    )

    await session.generate_reply(
        instructions="Start speaking something long."
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
