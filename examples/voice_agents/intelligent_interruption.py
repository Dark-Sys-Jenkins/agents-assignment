"""
Intelligent Interruption Handling Example

This example demonstrates the intelligent interruption handling feature that:
1. Ignores backchannel words ("yeah", "ok", "hmm") when agent is speaking
2. Allows interruption for command words ("wait", "stop", "no")
3. Handles mixed sentences ("yeah but wait") by detecting command words
4. Treats all input as valid when agent is silent

Test scenarios:
- Scenario 1: Say "yeah", "ok", "hmm" while agent is talking - Agent continues seamlessly
- Scenario 2: Say "yeah" when agent is silent - Agent responds normally
- Scenario 3: Say "stop" or "wait" while agent is talking - Agent stops immediately
- Scenario 4: Say "yeah but wait" while agent is talking - Agent stops (command detected)
"""

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
)
from livekit.agents.voice import (
    InterruptionFilter,
    InterruptionFilterConfig,
    set_default_filter,
)
from livekit.plugins import silero

logger = logging.getLogger("intelligent-interruption-agent")

load_dotenv()


class LongExplanationAgent(Agent):
    """An agent that gives long explanations to test interruption handling."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""Your name is Alex. You are a helpful assistant that gives detailed explanations.

When asked about a topic, provide a long, detailed explanation that takes at least 30 seconds to read.
This helps test the interruption handling feature.

Keep your voice natural and conversational. When you hear the user say things like
"yeah", "ok", "uh-huh", or "hmm" while you're speaking, know that they're just acknowledging
they're listening - don't stop speaking. Only stop if they say "wait", "stop", "hold on",
or ask a question.

If the user says "yeah" when you're done speaking, treat it as them being ready for more
or asking a follow-up question.

Do not use emojis, asterisks, markdown, or other special characters in your responses.""",
        )

    async def on_enter(self):
        # Greet the user and start a long explanation
        self.session.generate_reply()


def create_custom_filter() -> InterruptionFilter:
    """Create a custom interruption filter with additional backchannel words."""
    config = InterruptionFilterConfig()

    # Add additional backchannel words if needed
    additional_backchannels = [
        "uh huh", "i understand", "i get it", "makes sense",
        "interesting", "fascinating", "wow", "really",
    ]
    config.backchannel_words.extend(additional_backchannels)

    # You can also add custom interrupt words
    additional_interrupts = [
        "excuse me", "one moment", "hold that thought",
    ]
    config.interrupt_words.extend(additional_interrupts)

    return InterruptionFilter(config)


server = AgentServer()


def prewarm(proc: JobProcess):
    # Load VAD model
    proc.userdata["vad"] = silero.VAD.load()

    # Configure the custom interruption filter
    custom_filter = create_custom_filter()
    set_default_filter(custom_filter)

    logger.info("Intelligent interruption filter configured")
    logger.info(f"Backchannel words: {custom_filter.config.backchannel_words[:10]}...")
    logger.info(f"Interrupt words: {custom_filter.config.interrupt_words[:10]}...")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        # Speech-to-text
        stt="deepgram/nova-3",
        # LLM
        llm="openai/gpt-4.1-mini",
        # Text-to-speech
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD
        vad=ctx.proc.userdata["vad"],
        # Enable interruptions
        allow_interruptions=True,
        # Configure false interruption handling
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
        # Minimum duration before considering an interruption (helps with noise)
        min_interruption_duration=0.3,
    )

    # Log events for debugging
    @session.on("user_input_transcribed")
    def on_transcript(ev):
        logger.info(f"User said: '{ev.transcript}' (final={ev.is_final})")

    @session.on("agent_state_changed")
    def on_agent_state(ev):
        logger.info(f"Agent state: {ev.old_state} -> {ev.new_state}")

    @session.on("agent_false_interruption")
    def on_false_interruption(ev):
        logger.info(f"False interruption detected, resumed={ev.resumed}")

    await session.start(
        agent=LongExplanationAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
