# examples/voice_agents/intelligent_interruption_agent.py
import asyncio
import logging
import os
import sys

from typing import Set

from dotenv import load_dotenv

# Load .env file (try common locations)
script_dir = os.path.dirname(os.path.abspath(__file__))
examples_env = os.path.join(script_dir, '..', '.env')
load_dotenv(examples_env)
load_dotenv()

from livekit.agents import (
    Agent,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice import AgentSession
# from livekit.agents.voice.audio_recognition import TurnDetectionMode  # Removed: Type alias, not needed for string literal
from livekit.agents.voice.events import AgentStateChangedEvent, UserInputTranscribedEvent
from smart_interruption_session import SmartInterruptionSession

# Import real plugins
from livekit.plugins import deepgram, openai, silero

# Configure logging
logger = logging.getLogger("intelligent-interruption")
logger.setLevel(logging.INFO)

# Add console handler to see logs
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class AgentStateTracker:
    """Monitors agent speech state for context-aware interruption handling"""
    
    def __init__(self):
        self.is_speaking = False
        self._lock = asyncio.Lock()
    
    async def on_agent_state_changed(self, is_speaking: bool):
        async with self._lock:
            self.is_speaking = is_speaking
            logger.debug(f"Agent speaking state changed to: {self.is_speaking}")
    
    def is_agent_speaking(self) -> bool:
        """Thread-safe check of current agent state"""
        return self.is_speaking

class InterruptionClassifier:
    """Classifies user input as backchanneling vs interruption"""
    
    # Configurable word lists
    IGNORE_WORDS = {
        'yeah', 'yep', 'yes',
        'ok', 'okay', 'k',
        'hmm', 'mhmm', 'mm-hmm',
        'uh-huh', 'aha', 'right',
        'sure', 'alright'
    }
    
    INTERRUPT_KEYWORDS = {
        'stop', 'wait', 'hold', 'pause',
        'no', 'nope',
        'hang on', 'hold on', 'hold up'
    }
    
    def __init__(self, ignore_words=None, interrupt_keywords=None):
        if ignore_words:
            self.IGNORE_WORDS = set(ignore_words)
        if interrupt_keywords:
            self.INTERRUPT_KEYWORDS = set(interrupt_keywords)

    def has_interrupt_keyword(self, text: str) -> bool:
        """
        Quick check if text contains any interrupt keyword.
        Used for early detection in interim transcripts.
        """
        tokens = set(text.lower().split())
        
        # Check single-word keywords
        if tokens & self.INTERRUPT_KEYWORDS:
            return True
        
        # Check multi-word phrases
        text_lower = text.lower()
        for keyword in self.INTERRUPT_KEYWORDS:
            if " " in keyword and keyword in text_lower:
                return True
        
        return False
    
    def is_pure_backchanneling(self, text: str) -> bool:
        """
        Strict check if text is ONLY backchanneling words.
        """
        if not text or not text.strip():
            return False
        
        tokens = set(text.lower().strip().split())
        return tokens.issubset(self.IGNORE_WORDS)

    def should_interrupt(self, transcript: str, agent_speaking: bool) -> bool:
        """
        Decision logic:
        1. If agent is silent -> always process input (return True)
        2. If agent is speaking:
           - Contains interrupt keyword -> interrupt (return True)
           - Only contains ignore words -> don't interrupt (return False)
           - Mixed/unknown -> interrupt to be safe (return True)
        """
        if not agent_speaking:
            # Agent is silent, all user input is valid
            logger.info(f"Agent silent - accepting all input: '{transcript}'")
            return True
        
        # Agent is speaking - classify the input
        text = transcript.lower().strip()
        tokens = set(text.split())
        
        # Check for explicit interrupt keywords (single-word tokens)
        if tokens & self.INTERRUPT_KEYWORDS:
            logger.info(f"Interrupt keyword detected in: '{text}'")
            return True

        # Check for multi-word interrupt phrases like "hold on"
        for keyword in self.INTERRUPT_KEYWORDS:
            if " " in keyword and keyword in text:
                logger.info(f"Interrupt phrase detected: '{keyword}' in '{text}'")
                return True

        # Check if it's ONLY backchanneling words
        if tokens and tokens.issubset(self.IGNORE_WORDS):
            logger.info(f"Pure backchanneling detected: '{text}' - ignoring")
            return False
        
        # Mixed content or unknown - err on side of interrupting
        logger.info(f"Mixed/unknown input: '{text}' - allowing interrupt")
        return True

class IntelligentInterruptionHandler:
    """
    Main handler that integrates state tracking and classification
    to provide intelligent interruption control
    """
    
    def __init__(self, ignore_words=None, interrupt_keywords=None):
        self.state_tracker = AgentStateTracker()
        self.classifier = InterruptionClassifier(ignore_words, interrupt_keywords)
    
    async def on_agent_state_changed(self, event: AgentStateChangedEvent):
        """Hook: Called when agent state changes"""
        # "speaking" state in LiveKit agents means the agent is currently outputting audio
        is_speaking = event.new_state == "speaking"
        await self.state_tracker.on_agent_state_changed(is_speaking)
    
    async def handle_user_transcript(
        self, 
        event: UserInputTranscribedEvent,
        session
    ) -> bool:
        """
        Process user transcript and decide interruption behavior.
        
        Returns:
            bool: True if interruption was allowed/executed, False if ignored
        """
        transcript = event.transcript
        is_speaking = self.state_tracker.is_agent_speaking()
        should_interrupt = self.classifier.should_interrupt(transcript, is_speaking)
        
        logger.info(
            f"[DECISION] Transcript: '{transcript}' | "
            f"Agent speaking: {is_speaking} | "
            f"Should interrupt: {should_interrupt}"
        )
        
        if is_speaking:
            if should_interrupt:
                # Real interruption - stop the agent's current speech
                logger.info(">>> INTERRUPTING agent speech")
                
                # Stop current TTS playback
                await session.interrupt()
                
                # Commit the user's turn so the agent processes it and responds
                await session.commit_user_turn()
                
                logger.info("Interruption executed & turn committed")
                return True
            else:
                # Backchanneling - ignore completely
                logger.info(">>> IGNORING backchanneling - agent continues")
                
                # Don't commit the turn - this discards the input
                # The session will naturally ignore uncommitted turns in manual mode
                # If clear_user_turn exists, use it to explicitly clear
                if hasattr(session, 'clear_user_turn'):
                    await session.clear_user_turn()
                
                logger.info("Backchanneling discarded - agent continues seamlessly")
                return False
        else:
            # Agent is silent - commit the turn (normal processing)
            logger.info(">>> COMMITTING user turn (agent was silent)")
            await session.commit_user_turn()
            logger.info("Valid input during silence - processing")
            return True

async def entrypoint(ctx: JobContext):
    # Load env vars for configuration
    ignore_words_str = os.getenv('IGNORE_WORDS', '')
    interrupt_keywords_str = os.getenv('INTERRUPT_KEYWORDS', '')
    
    ignore_words = None
    interrupt_keywords = None
    
    if ignore_words_str:
        ignore_words = [w.strip() for w in ignore_words_str.split(',') if w.strip()]
        logger.info(f"Custom IGNORE_WORDS loaded: {ignore_words}")
    
    if interrupt_keywords_str:
        interrupt_keywords = [w.strip() for w in interrupt_keywords_str.split(',') if w.strip()]
        logger.info(f"Custom INTERRUPT_KEYWORDS loaded: {interrupt_keywords}")

    # Initialize handler
    handler = IntelligentInterruptionHandler(ignore_words, interrupt_keywords)
    logger.info("Intelligent Interruption Handler initialized")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to LiveKit room")

    # Determine if we should use fakes or real plugins
    use_fakes = os.getenv('USE_FAKE_DATA', 'false').lower() == 'true'
    
    if use_fakes:
        logger.info("Using FAKE components (no API cost)")
        
        # Try to import fakes from tests directory
        try:
            # Try multiple possible import paths
            try:
                from tests.fakes import FakeLLM, FakeTTS, FakeVAD, FakeSTT
            except ImportError:
                from fakes import FakeLLM, FakeTTS, FakeVAD, FakeSTT
            
            vad_instance = FakeVAD()
            stt_instance = FakeSTT()
            llm_instance = FakeLLM()
            tts_instance = FakeTTS()
            logger.info(" Successfully loaded fake components")
            
        except ImportError as e:
            logger.error(f" Failed to import fake components: {e}")
            logger.error("Make sure fakes.py is in the tests/ directory or current directory")
            raise
    else:
        logger.info("Using REAL plugins (Deepgram/OpenAI)")
        vad_instance = silero.VAD.load()
        stt_instance = deepgram.STT(model="nova-3")
        llm_instance = openai.LLM(model="gpt-4o-mini")
        tts_instance = openai.TTS(voice="echo")

    # Create session with manual turn detection
    # Create session with manual turn detection
    session = SmartInterruptionSession(
        handler=handler,
        vad=vad_instance,
        stt=stt_instance,
        llm=llm_instance,
        tts=tts_instance,
        turn_detection="manual",  #  FIXED: Use string literal, TurnDetectionMode is a type alias
        allow_interruptions=True,  # Critical: enables session.interrupt()
    )
    
    logger.info(f"AgentSession created with {'FAKE' if use_fakes else 'REAL'} components")
    
    agent_logic = Agent(
        instructions=(
            "You are a helpful assistant that provides detailed explanations. "
            "When explaining something, give thorough responses. "
            "If someone interrupts you with 'stop' or 'wait', acknowledge and ask what they need. "
            "Ignore acknowledgments like 'yeah', 'ok', 'hmm' while you're speaking."
        ),
    )

    # Attach Event Handlers BEFORE starting the session
    # Attach Event Handlers:
    # Note: SmartInterruptionSession handles interruption logic internally via SmartAgentActivity.
    # We only keep the state tracker hook if needed for logging/external monitoring, 
    # but the logic is now inside the activity.
    
    # We still need to update the handler's state tracker so the session can use it via self.handler
    @session.on("agent_state_changed")
    def on_agent_state_changed(event: AgentStateChangedEvent):
        asyncio.create_task(handler.on_agent_state_changed(event))
    
    # We REMOVE the manual user_input_transcribed hook because SmartAgentActivity handles 
    # the decision making and committing.

    logger.info("Event handlers registered")
    
    # Start the session (only once!)
    await session.start(agent=agent_logic, room=ctx.room)
    
    logger.info("Agent session started and running")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))