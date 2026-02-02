import logging
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Set, Optional
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.plugins import silero

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smart_agent")
load_dotenv()


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class TranscriptType(Enum):
    """Types of user input we can receive."""
    ACKNOWLEDGMENT = "acknowledgment"  # Filler words
    INTERRUPT = "interrupt"             # Command words
    MESSAGE = "message"                 # Real speech


@dataclass
class VocabularyConfig:
    """Configuration for word classification."""
    
    # Words that indicate user is listening (backchanneling)
    acknowledgments: Set[str] = None
    
    # Words that explicitly request interruption
    interrupts: Set[str] = None
    
    def __post_init__(self):
        if self.acknowledgments is None:
            self.acknowledgments = {
                # Simple affirmations
                "yeah", "yep", "yes", "yup", "ok", "okay", "alright",
                "i see", "got it", "gotcha", "right", "sure", "hmm",
                "uh-huh", "mm-hmm", "mhm", "aha", "oh",
                "exactly", "absolutely", "definitely", "correct", "true",
            }
        
        if self.interrupts is None:
            self.interrupts = {
                # Stop commands
                "stop", "wait", "pause", "hold", "hold on", "hang on",
                "no", "nope", "don't", "dont", "nah",
                "actually", "nevermind", "cancel",
            }
        
        # Normalize to lowercase
        self.acknowledgments = {w.lower() for w in self.acknowledgments}
        self.interrupts = {w.lower() for w in self.interrupts}


# Global vocabulary configuration
VOCAB = VocabularyConfig()


# ============================================================================
# TRANSCRIPT ANALYZER
# ============================================================================

class TranscriptAnalyzer:
    """
    Analyzes user transcripts and classifies them into types.
    
    This is a stateless analyzer that uses the vocabulary configuration
    to determine the intent behind user speech.
    """
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Remove punctuation and normalize text."""
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove common punctuation
        for char in ".,!?;:":
            normalized = normalized.replace(char, "")
        
        return normalized
    
    @staticmethod
    def extract_words(text: str) -> Set[str]:
        """Extract individual words from normalized text."""
        normalized = TranscriptAnalyzer.normalize_text(text)
        return set(normalized.split()) if normalized else set()
    
    @classmethod
    def classify(cls, text: str) -> TranscriptType:
        """
        Classify transcript into one of three types.
        
        Priority order:
        1. INTERRUPT - if any interrupt words present
        2. ACKNOWLEDGMENT - if only acknowledgment words present
        3. MESSAGE - everything else
        """
        if not text or not text.strip():
            return TranscriptType.ACKNOWLEDGMENT
        
        words = cls.extract_words(text)
        
        if not words:
            return TranscriptType.ACKNOWLEDGMENT
        
        # Check for interrupt words (highest priority)
        if words & VOCAB.interrupts:
            return TranscriptType.INTERRUPT
        
        # Check if ALL words are acknowledgments
        if words <= VOCAB.acknowledgments:  # Subset check
            return TranscriptType.ACKNOWLEDGMENT
        
        # Default to message
        return TranscriptType.MESSAGE


# ============================================================================
# STATE MANAGER
# ============================================================================

class AgentStateManager:
    """
    Tracks agent state and provides decision logic for interruptions.
    
    This class encapsulates all the logic for deciding when to
    interrupt the agent based on context.
    """
    
    def __init__(self):
        self.is_agent_speaking = False
        self.last_user_input_type: Optional[TranscriptType] = None
    
    def update_agent_state(self, speaking: bool) -> None:
        """Update whether agent is currently speaking."""
        self.is_agent_speaking = speaking
        logger.debug(f"Agent state updated: {'speaking' if speaking else 'listening'}")
    
    def should_commit_turn(
        self,
        transcript_type: TranscriptType,
        transcript_text: str
    ) -> bool:
        """
        Decide if we should commit a turn based on context.
        """
        self.last_user_input_type = transcript_type
        
        # Log the decision context
        state = "speaking" if self.is_agent_speaking else "silent"
        logger.info(
            f"Decision: transcript='{transcript_text}' | "
            f"type={transcript_type.value} | "
            f"agent={state}"
        )
        
        # ACKNOWLEDGMENT handling (context-aware)
        if transcript_type == TranscriptType.ACKNOWLEDGMENT:
            if self.is_agent_speaking:
                # User just saying "yeah" while we talk → ignore
                logger.info(f"→ IGNORED '{transcript_text}' (backchanneling)")
                return False
            else:
                # User saying "yeah" when we're quiet → treat as input
                logger.info(f"→ ACKNOWLEDGED '{transcript_text}' (valid response)")
                return True
        
        # INTERRUPT commands always commit (high priority)
        if transcript_type == TranscriptType.INTERRUPT:
            logger.info(f"→ INTERRUPTING for '{transcript_text}'")
            return True
        
        # MESSAGE always commits (normal flow)
        logger.info(f"→ PROCESSING '{transcript_text}'")
        return True


# ============================================================================
# INTERACTION CONTROLLER
# ============================================================================

class InteractionController:
    """
    Main controller that coordinates between transcript analysis,
    state management, and session control.
    
    This is the orchestration layer that ties everything together.
    """
    
    def __init__(self, session: AgentSession):
        self.session = session
        self.analyzer = TranscriptAnalyzer()
        self.state_manager = AgentStateManager()
        
        # Wire up event handlers
        self._register_handlers()
        
        logger.info("✓ InteractionController initialized")
    
    def _register_handlers(self) -> None:
        """Register event handlers with the session."""
        self.session.on("agent_state_changed", self._handle_agent_state_change)
        self.session.on("user_input_transcribed", self._handle_user_transcript)
    
    def _handle_agent_state_change(self, event) -> None:
        """Handle agent state change events."""
        is_speaking = (event.new_state == "speaking")
        self.state_manager.update_agent_state(is_speaking)
    
    def _handle_user_transcript(self, event) -> None:
        """        
        This is the main decision point - we analyze the transcript
        and decide whether to commit a turn.
        """
        # Only process final transcripts
        if not event.is_final:
            logger.debug(f"[INTERIM] {event.transcript}")
            return
        
        transcript = event.transcript
        
        # Analyze transcript type
        transcript_type = self.analyzer.classify(transcript)
        
        # Decide if we should commit the turn
        should_commit = self.state_manager.should_commit_turn(
            transcript_type,
            transcript
        )
        
        # Execute decision
        if should_commit:
            self._commit_user_turn()
    
    def _commit_user_turn(self) -> None:
        """
        Commit the user turn to trigger agent response.
        """
        try:
            self.session.commit_user_turn(
                transcript_timeout=2.0,
                stt_flush_duration=0.5
            )
            logger.debug("✓ Turn committed")
        except Exception as e:
            logger.error(f"✗ Turn commit failed: {e}", exc_info=True)


# ============================================================================
# AGENT DEFINITION
# ============================================================================

class SmartAssistant(Agent):
    """
    Voice assistant with natural conversational abilities.
    
    This agent is optimized for voice interactions with support
    for natural backchanneling (user saying "yeah", "ok" etc).
    """
    
    def __init__(self):
        super().__init__(
            instructions=self._get_instructions()
        )
    
    @staticmethod
    def _get_instructions() -> str:
        """Get system instructions for the agent."""
        return """You are a helpful and friendly AI voice assistant.

Communication Style:
- Speak naturally as if having a real conversation
- Keep responses concise and clear
- Avoid technical jargon unless asked
- Don't use emojis, markdown, or special formatting
- Be conversational but professional

User Interaction:
- The user is speaking to you via voice
- Listen carefully and respond appropriately
- If unsure, ask for clarification
- Be patient and supportive

Your Personality:
- Friendly and approachable
- Curious about user needs
- Helpful and solution-oriented
- Warm sense of humor when appropriate"""


# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Initialize server
server = AgentServer()


def initialize_models(process: JobProcess) -> None:
    """
    Pre-load models to reduce latency on first request.
    
    This runs once when the worker process starts.
    """
    logger.info("Pre-loading VAD model...")
    process.userdata["vad_model"] = silero.VAD.load()
    logger.info("✓ Models loaded")


# Register initialization function
server.setup_fnc = initialize_models


# ============================================================================
# SESSION HANDLER
# ============================================================================

@server.rtc_session()
async def handle_session(context: JobContext):
    """
    Main session handler - called for each new connection.
    
    This sets up the agent session with manual turn detection
    and our smart interaction controller.
    """
    # Add room context to logs
    context.log_context_fields = {"room": context.room.name}
    
    logger.info(f"New session started: {context.room.name}")
    
    # Configure agent session
    session = AgentSession(
        # Model configuration
        stt=inference.STT(
            model="assemblyai/universal-streaming",
            language="en"
        ),
        llm=inference.LLM(
            model="openai/gpt-4.1-mini"
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        
        # Use pre-loaded VAD
        vad=context.proc.userdata["vad_model"],
        
        # CRITICAL: Manual turn detection
        # This decouples VAD detection from audio interruption
        turn_detection="manual",
        
        # Performance optimizations
        preemptive_generation=True,      # Start LLM early
        allow_interruptions=True,        # Enable interruptions
        min_interruption_duration=0.0,   # No VAD threshold
        min_interruption_words=0,        # No word threshold
        
        # Disable automatic false interruption handling
        # (we handle it manually via our controller)
        resume_false_interruption=False,
        false_interruption_timeout=None,
    )
    
    # Initialize interaction controller
    # This handles all the smart decision-making
    controller = InteractionController(session)
    
    # Start the session
    await session.start(
        agent=SmartAssistant(),
        room=context.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )
    
    # Connect to room
    await context.connect()
    
    logger.info(f"Session ready: {context.room.name}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Smart Voice Agent...")
    cli.run_app(server)