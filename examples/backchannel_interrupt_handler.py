"""
Context-Aware Interrupt Handler for LiveKit Agents
This demonstrates intelligent handling of user interruptions:
- Ignores backchannel responses ("yeah", "okay", "mhmm") while agent is speaking
- Responds to the same words when agent is silent
- Immediately stops on command words ("stop", "wait")
"""

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    cli,
)
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit import rtc
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Backchannel words to filter when agent is speaking
BACKCHANNEL_WORDS = {"yeah", "okay", "ok", "mhmm", "mm-hmm", "uh-huh", "right", "sure"}

# Command words that always interrupt
STOP_WORDS = {"stop", "wait", "pause", "halt"}


class InterruptHandlerAgent(Agent):
    """Agent with context-aware interrupt handling"""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful assistant. "
                "Engage in natural conversation with the user. "
                "When you hear acknowledgments like 'yeah' or 'okay', respond naturally. "
                "If interrupted with 'stop' or 'wait', acknowledge and pause."
            )
        )
        self._is_speaking = False

    async def on_speech_started(self, ctx: rtc.SpeechEventContext) -> None:
        """Called when the agent starts speaking"""
        self._is_speaking = True
        logger.info("Agent started speaking")

    async def on_speech_ended(self, ctx: rtc.SpeechEventContext) -> None:
        """Called when the agent finishes speaking"""
        self._is_speaking = False
        logger.info("Agent finished speaking")

    async def on_user_transcript_received(
        self, ctx: JobContext, transcript: str
    ) -> bool:
        """
        Filter user transcripts based on agent state
        Returns True if the transcript should be processed, False to ignore it
        """
        transcript_lower = transcript.strip().lower()

        # Always process stop commands immediately
        if any(word in transcript_lower for word in STOP_WORDS):
            logger.info(f"STOP command detected: '{transcript}' - Processing immediately")
            return True

        # Filter backchannel responses when agent is speaking
        if self._is_speaking and transcript_lower in BACKCHANNEL_WORDS:
            logger.info(
                f"Ignoring backchannel '{transcript}' while agent is speaking"
            )
            return False

        # Process backchannel responses when agent is silent
        if not self._is_speaking and transcript_lower in BACKCHANNEL_WORDS:
            logger.info(f"Processing backchannel '{transcript}' while agent is silent")
            return True

        # Process all other transcripts normally
        logger.info(f"Processing transcript: '{transcript}'")
        return True


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent session"""
    await ctx.connect()

    logger.info("Starting interrupt handler agent session")

    # Create agent with interrupt handling
    agent = InterruptHandlerAgent()

    # Create session with LiveKit plugins
    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(voice="79a125e8-cd45-4c13-8a67-188112f4dd22"),  # British Lady
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(),
    )

    # Start the session
    await session.start(ctx.room, agent)

    # Greet the user
    await session.say(
        "Hello! I'm your assistant with context-aware interrupt handling. "
        "Try saying 'yeah' while I'm talking, or 'stop' to interrupt me immediately.",
        allow_interruptions=True,
    )

    logger.info("Agent session started successfully")


if __name__ == "__main__":
    cli.run_app(server)
