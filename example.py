from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import silero
from livekit.agents.voice.interrupt_layer import IntelligentInterruptSession

@function_tool
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""
    return {"weather": "sunny", "temperature": 70}


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="You are a friendly voice assistant built by LiveKit.",
        tools=[lookup_weather],
    )
    ignored_words = {"yeah","sure", "ok", "okay", "hmm", "aha", "right", "uh-huh", "yep", "yup"}

    session = IntelligentInterruptSession(
        ignored_words=ignored_words,
        vad=silero.VAD.load(),
        stt="deepgram/nova-2:en",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
    )

    @session.on("user_input_transcribed")
    def on_user_transcript(event):
        print(f"🎤 USER: {event.transcript} (final: {event.is_final})")
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        if hasattr(event.item, 'role') and event.item.role == 'assistant':
            print(f"🤖 AGENT: {event.item.content}")
    
    @session.on("agent_started_speaking")
    def on_agent_start():
        print("🔊 Agent started speaking")
    
    @session.on("agent_stopped_speaking")
    def on_agent_stop():
        print("🔇 Agent stopped speaking")
    
    @session.on("user_started_speaking")
    def on_user_start():
        print("🎙️ User started speaking (VAD detected)")

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="greet the user and ask about their day")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
