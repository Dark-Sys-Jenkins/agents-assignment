import asyncio

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)

from livekit.plugins import silero, inference

from agents.interrupt_handler import IntelligentInterruptHandler


async def entrypoint(ctx: JobContext):

    # ession Setup  #

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=inference.STT("assemblyai/universal-streaming"),
        llm=inference.LLM("openai/gpt-4.1-mini"),
        tts=inference.TTS("cartesia/sonic-3"),
    )

    agent = Agent(
        instructions="You are a helpful voice assistant.",
    )

    # interrupt Handler #

    interrupt_handler = IntelligentInterruptHandler(
        is_agent_speaking=lambda: session.is_speaking,
        stop_audio=lambda: session.stop_audio(),
        continue_audio=lambda: None,  # audio continues naturally
    )

    @session.on("vad")
    def on_vad_event():
        print("[VAD] speech detected")
        stt_future = session.next_transcript()
        interrupt_handler.on_vad_detected(stt_future)

    @session.on("stt")
    async def on_stt_event(event):
        await interrupt_handler.handle_stt_result(event.text)

    # Start Session #

    await session.start(agent=agent, room=ctx.room)

    await session.generate_reply(
        instructions="Hello! Let me know when you're ready to begin."
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
