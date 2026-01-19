"""
Advanced Smart Interruption Agent

Features:
- Timing-aware interruption detection
- Audio urgency analysis
- Confidence scoring
"""

import sys
from pathlib import Path

# Add local package path BEFORE other imports to find the new interruption_handler
_repo_root = Path(__file__).resolve().parents[2]
_candidates = [_repo_root / "livekit-agents", _repo_root]
for _p in _candidates:
    if _p.exists():
        sys.path.insert(0, str(_p))
        break

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import numpy as np

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, google, cartesia, silero


env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from livekit.agents.voice.interruption_handler import (
    TimingAwareInterruptionHandler,
    InterruptionIntent,
    AudioAnalyzer,
    AgentState,
)

try:
    from interruption_config import (
        SOFT_ACKNOWLEDGMENTS,
        HARD_INTERRUPTIONS,
        POLITE_INTERRUPTIONS,
        MIN_SPEECH_DURATION,
        SHORT_SPEECH_THRESHOLD,
        LONG_SPEECH_THRESHOLD,
        BASE_THRESHOLD,
    )
    logger.info("Loaded custom interruption configuration")
except ImportError:
    SOFT_ACKNOWLEDGMENTS = None
    HARD_INTERRUPTIONS = None
    POLITE_INTERRUPTIONS = None
    MIN_SPEECH_DURATION = 1.0
    SHORT_SPEECH_THRESHOLD = 3.0
    LONG_SPEECH_THRESHOLD = 8.0
    BASE_THRESHOLD = 0.7
    logger.info("Using default interruption configuration")


class AdvancedInterruptionSession(AgentSession):
    """
    Custom AgentSession with advanced interruption detection.
    Uses timing awareness + audio urgency detection.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.interruption_handler = TimingAwareInterruptionHandler(
            min_speech_duration=MIN_SPEECH_DURATION,
            short_speech_threshold=SHORT_SPEECH_THRESHOLD,
            long_speech_threshold=LONG_SPEECH_THRESHOLD,
            base_threshold=BASE_THRESHOLD,
            soft_words=SOFT_ACKNOWLEDGMENTS,
            hard_words=HARD_INTERRUPTIONS,
            polite_phrases=POLITE_INTERRUPTIONS,
        )

        self.audio_analyzer = AudioAnalyzer()
        self._last_user_audio: Optional[np.ndarray] = None
        self._agent_speaking = False

        logger.info("Advanced interruption session initialized")

    async def _on_agent_speech_started(self):
        """Called when agent starts speaking"""
        self._agent_speaking = True
        self.interruption_handler.update_agent_state(AgentState.SPEAKING)
        logger.debug("Agent started speaking")

    async def _on_agent_speech_stopped(self):
        """Called when agent stops speaking"""
        self._agent_speaking = False
        self.interruption_handler.update_agent_state(AgentState.IDLE)
        logger.debug("Agent stopped speaking")

    async def _should_interrupt(self, transcript: str) -> bool:
        """
        Advanced interruption logic with full context.

        This is called by the agent framework when user speaks during agent speech.
        """
        # Get agent speech duration
        speech_duration = self.interruption_handler.get_speech_duration()

        # Extract audio features if available
        audio_features = None
        if self._last_user_audio is not None and len(self._last_user_audio) > 0:
            try:
                audio_features = self.audio_analyzer.extract_features(
                    self._last_user_audio,
                    sample_rate=16000
                )
                logger.debug(f"Audio features: energy={audio_features.rms_energy:.3f}, "
                           f"zcr={audio_features.zero_crossing_rate:.3f}, "
                           f"duration={audio_features.duration:.2f}s")
            except Exception as e:
                logger.warning(f"Failed to extract audio features: {e}")

        # Make decision with full context
        score = self.interruption_handler.decide(
            text=transcript,
            speech_duration=speech_duration,
            audio_features=audio_features
        )

        if score.decision == InterruptionIntent.INTERRUPT:
            logger.info(f"INTERRUPTING (confidence={score.confidence:.2f})")
            logger.info(f"User said: '{transcript}'")
            logger.info(f"Agent spoke for: {speech_duration:.1f}s")
            logger.info(f"Scores: semantic={score.semantic_score:.2f}, "
                       f"timing={score.timing_score:.2f}, urgency={score.urgency_score:.2f}")
        else:
            logger.info(f"CONTINUING (confidence={score.confidence:.2f})")
            logger.info(f"User said: '{transcript}' (acknowledged)")
            logger.info(f"Agent continues speaking")

        return score.decision == InterruptionIntent.INTERRUPT

    def _on_user_audio(self, audio_data: bytes):
        """Capture user audio for feature extraction"""
        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            self._last_user_audio = audio_array
        except Exception as e:
            logger.debug(f"Error capturing user audio: {e}")


async def entrypoint(ctx: JobContext):
    """Main agent with advanced interruption handling"""
    await ctx.connect()
    logger.info("Connected to LiveKit room: %s", ctx.room.name)

    agent = Agent(
        instructions=(
            "You are a helpful AI assistant. "
            "Give detailed, informative responses (4-6 sentences) so users can test "
            "interrupting you at different points. "
            "Be friendly and natural. "
        )
    )

    logger.info("Initializing providers...")

    voice_activity_detector = silero.VAD.load()
    logger.info("VAD: Silero")

    speech_to_text = deepgram.STT(model="nova-3")
    logger.info("STT: Deepgram Nova-3")

    language_model = google.LLM(
        model="gemini-2.5-flash-lite-preview-09-2025",
        temperature=0.7,
    )
    logger.info("LLM: gemini-2.5-flash-lite-preview-09-2025")

    text_to_speech = None
    if os.getenv("CARTESIA_API_KEY"):
        try:
            text_to_speech = cartesia.TTS()
            logger.info("TTS: Cartesia")
            logger.info("Note: If you get 402 errors, your Cartesia account may need credits")
        except Exception as e:
            logger.warning(f"Failed to initialize Cartesia TTS: {e}")
            logger.info("Falling back to Google Cloud TTS")

    if text_to_speech is None:
        text_to_speech = google.TTS()
        logger.info("TTS: Google Cloud TTS")

    session = AdvancedInterruptionSession(
        vad=voice_activity_detector,
        stt=speech_to_text,
        llm=language_model,
        tts=text_to_speech,
    )

    logger.info("Starting agent...")
    await session.start(agent=agent, room=ctx.room)

    logger.info("Generating greeting...")
    await session.generate_reply(
        instructions=(
            "Greet the user warmly and explain you're demonstrating advanced interruption handling. "
            "Tell them to try interrupting you while you speak - "
            "soft words like 'yeah' or 'okay' will be ignored, "
            "but 'wait' or 'hold on' will stop you. "
            "Also mention that the system analyzes timing and urgency."
        )
    )

    logger.info("Agent is live")


if __name__ == "__main__":

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))