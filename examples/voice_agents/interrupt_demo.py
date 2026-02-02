# Intelligent Interruption Handling Demo Agent
#
# This example demonstrates the intelligent interruption handling feature that
# distinguishes between passive acknowledgements (backchanneling) and actual
# interruptions during voice conversations.
#
# When the agent is speaking:
#   - "yeah", "ok", "hmm" → Agent continues speaking (backchannel)
#   - "stop", "wait", "no" → Agent stops immediately (interruption)
#   - "yeah but wait" → Agent stops (mixed input with interrupt word)
#
# When the agent is silent:
#   - All user input is processed normally, including backchannel words
#
# Prerequisites:
#   1. Set environment variables:
#      - LIVEKIT_URL (e.g., wss://your-project.livekit.cloud)
#      - LIVEKIT_API_KEY
#      - LIVEKIT_API_SECRET
#      - DEEPGRAM_API_KEY (or other STT provider)
#      - OPENAI_API_KEY (or other LLM provider)
#
#   2. Get a free LiveKit Cloud account at: https://cloud.livekit.io
#   3. Get a free Deepgram account at: https://console.deepgram.com
#
# Running the demo:
#   python interrupt_demo.py dev
#
# Then connect via LiveKit Agents Playground:
#   https://agents-playground.livekit.io/

import logging

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("interrupt-demo")

load_dotenv()


class DemoAgent(Agent):
    """Demo agent for testing intelligent interruption handling.
    
    This agent tells long stories when asked, making it easy to test
    whether backchanneling words trigger interruptions.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly storyteller named Alex.

Your job is to help demonstrate the intelligent interruption handling feature.
When asked for a story, tell a LONG, engaging story (at least 3-4 paragraphs).

When the user says things like "yeah", "ok", "uh-huh", or "hmm" while you're 
speaking, these are just acknowledgements - keep talking!

But if they say "stop", "wait", "hold on", or "actually" - stop and listen.

Keep your responses conversational but long enough to test interruptions.
Do not use emojis or special characters. Speak naturally.""",
        )

    async def on_enter(self):
        """Greet the user when the session starts."""
        self.session.generate_reply(
            instructions="Greet the user and tell them you're here to tell stories. "
            "Ask if they'd like to hear a story. Keep it brief - just 1-2 sentences."
        )

    @function_tool
    async def tell_story(self, context: RunContext, topic: str = "adventure"):
        """Tell a story about a given topic.
        
        Args:
            topic: The topic or theme for the story
        """
        logger.info(f"Telling a story about: {topic}")
        return f"Tell a long, engaging story about {topic}. Make it at least 3-4 paragraphs."


server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm the VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Entry point for the voice agent session."""
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Create session with intelligent interruption handling enabled
    session = AgentSession(
        # Speech-to-text - Deepgram Nova 3 provides fast, accurate transcription
        stt="deepgram/nova-3",
        
        # LLM - GPT-4.1-mini is fast and capable for storytelling
        llm="openai/gpt-4.1-mini",
        
        # Text-to-speech - Cartesia Sonic 2 for natural speech
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        
        # Turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # Enable preemptive generation for lower latency
        preemptive_generation=True,
        
        # Enable false interruption resumption
        resume_false_interruption=True,
        
        # =================================================================
        # INTELLIGENT INTERRUPTION HANDLING - The feature being demonstrated
        # =================================================================
        
        # Enable the interruption filter (default: True)
        interruption_filter_enabled=True,
        
        # Optional: Custom backchannel words to ignore when agent is speaking
        # Uncomment to customize:
        # backchannel_words={
        #     "yeah", "yes", "yep", "ok", "okay", 
        #     "hmm", "mhm", "uh-huh", "right", "sure",
        # },
        
        # Optional: Custom words that always trigger interruption
        # Uncomment to customize:
        # interrupt_words={
        #     "stop", "wait", "hold on", "pause", "no",
        #     "actually", "but", "however",
        # },
    )

    logger.info("Starting session with intelligent interruption handling enabled")

    await session.start(
        agent=DemoAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)