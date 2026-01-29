#!/usr/bin/env python
"""
Test script to demonstrate the interrupt handler with real audio.

This script creates a simple agent that speaks and can be interrupted
by backchanneling words (like "yeah", "ok") without stopping,
or by real interruptions (like "stop", "I disagree").

Requirements:
- OPENAI_API_KEY environment variable set
- Optional: DEEPGRAM_API_KEY (for STT)
- Optional: CARTESIA_API_KEY (for TTS)

Run:
    python test_interrupt_handler_live.py
"""

import asyncio
import logging
from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-interrupt-handler")


class TestAgent(Agent):
    """A simple test agent that demonstrates interrupt handling."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful assistant. "
                "Keep your responses concise and conversational. "
                "When responding, speak naturally and pausefully. "
                "Do not use markdown, asterisks, or special formatting."
            ),
        )

    async def on_enter(self):
        """Generate greeting when agent enters."""
        logger.info("Agent entered session, generating greeting...")
        self.session.generate_reply()

    @function_tool
    async def tell_joke(self, context: RunContext) -> str:
        """Tell a joke when the user asks."""
        return "Why did the chicken cross the road? To get to the other side!"


async def main():
    """
    Main test function that creates a session and demonstrates interrupt handling.
    
    This creates a local session without needing a LiveKit server.
    You can also test with an actual LiveKit server by modifying the session setup.
    """
    logger.info("Starting interrupt handler test...")
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST: Interrupt Handler with Real Audio")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This test demonstrates:")
    logger.info("  1. Agent speaking with real audio output")
    logger.info("  2. Backchanneling words (yeah, ok) NOT interrupting the agent")
    logger.info("  3. Real interruptions (stop, I disagree) DO interrupt the agent")
    logger.info("")
    logger.info("To test:")
    logger.info("  - Start the agent")
    logger.info("  - Let it speak")
    logger.info("  - Try saying 'yeah' or 'ok' - agent continues")
    logger.info("  - Try saying 'stop' or 'I disagree' - agent gets interrupted")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Create agent session with real audio I/O
        session = AgentSession(
            # STT: Speech-to-Text (user's voice to text)
            stt="deepgram/nova-3",
            # LLM: Large Language Model (agent's brain)
            llm="openai/gpt-4-mini",
            # TTS: Text-to-Speech (agent's voice output)
            tts="cartesia/sonic-2",
            # VAD: Voice Activity Detection
            vad=silero.VAD.load(),
            # Turn detection for natural conversations
            turn_detection=MultilingualModel(),
            # Allow interruptions (with our filter)
            allow_interruptions=True,
            # Min words needed to trigger interrupt
            min_interruption_words=0,
        )

        # Create the agent
        agent = TestAgent()

        # Run the session (this will start listening for audio)
        logger.info("Starting session...")
        logger.info("Waiting for audio input...")
        logger.info("")

        # In a real scenario, you'd run this in a LiveKit room context
        # For local testing, you might want to use room_io or similar
        await session.start(agent)

        logger.info("Session started! Listening for audio...")
        logger.info("Press Ctrl+C to exit.")

        # Keep the session running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await session.aclose()

    except Exception as e:
        logger.error(f"Error running test: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
