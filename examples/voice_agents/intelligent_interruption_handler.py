"""
Intelligent Interruption Handler Example

This example demonstrates the backchannel filtering feature that allows
the agent to continue speaking when the user says filler words like
"yeah", "ok", "hmm" while still responding to real interruptions.

Test scenarios:
1. Ask the agent to tell a long story, then say "yeah", "okay", "uh-huh"
   while it's speaking - agent should continue without stopping.

2. Let the agent ask you a question, then respond with "yeah" -
   agent should process it as valid input.

3. While agent is speaking, say "wait" or "stop" -
   agent should immediately stop.

4. While agent is speaking, say "yeah but wait" -
   agent should stop (because "but wait" is meaningful content).

Environment variables required:
- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET
- DEEPGRAM_API_KEY (or other STT provider)
- OPENAI_API_KEY (or other LLM provider)
- ELEVEN_API_KEY (or other TTS provider)
"""

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, silero


class StoryTellerAgent(Agent):
    """An agent that tells long stories - perfect for testing backchannel handling."""

    def __init__(self, *, tools: list | None = None) -> None:
        super().__init__(
            instructions="""You are a friendly storyteller who loves to share
            detailed, engaging stories. When asked to tell a story, make it
            long and descriptive (at least 4-5 paragraphs).

            You enjoy when listeners say things like "yeah", "okay", "uh-huh"
            to show they're engaged - these are normal listener reactions and
            don't mean they want you to stop.

            However, if someone says "stop", "wait", or asks a question,
            you should pause and address them.
            """,
            tools=tools,
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Greet the user warmly and offer to tell them a fascinating story."
        )


@function_tool
async def tell_story(
    context: RunContext,
    topic: str,
):
    """Tell a long, engaging story about a given topic.

    Args:
        topic: The topic or theme of the story
    """
    return f"Tell a detailed, engaging story about {topic}. Make it at least 4-5 paragraphs long with vivid descriptions."


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # Create the agent with the storyteller persona and tools
    agent = StoryTellerAgent(tools=[tell_story])

    # Create session with intelligent interruption handling
    # The backchannel filter is enabled by default, but we can customize it
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="nova"),
        # Backchannel filtering is enabled by default
        # You can customize the word lists if needed:
        # backchannel_words=frozenset(["yeah", "ok", "hmm", "mhm", "sure"]),
        # interrupt_words=frozenset(["stop", "wait", "no", "what", "why"]),
    )

    # Optional: Add event handlers to see the filter in action
    @session.on("user_input_transcribed")
    def on_transcript(event):
        print(f"[TRANSCRIPT] {event.transcript} (final={event.is_final})")

    @session.on("agent_state_changed")
    def on_state_change(event):
        print(f"[AGENT STATE] {event.old_state} -> {event.new_state}")

    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
