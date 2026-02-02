"""
HYBRID INTERRUPTION HANDLING STRATEGY

Challenge:
- Slow filler words (e.g., a 1.5s "okay") should NOT trigger an interruption.
- Quick commands (e.g., a 0.5s "stop") MUST trigger an immediate interruption.
- Pure duration-based filtering is insufficient as it cannot distinguish these cases reliably.

Implementation Strategy:
- Configure VAD with MEDIUM sensitivity: Catches most valid speech but may allow some fillers.
- Auto-Resume on Fillers: If a filler triggers an interruption, the transcript handler will resume the agent.
- Force Interrupt on Commands: If a quick command is missed by VAD, the transcript handler will enforce an interrupt.

Outcome:
- Quick "stop" (0.5s): Ignored by VAD (too short) → Transcript Handler detects command and interrupts. ✅
- Slow "okay" (1.5s): Triggered by VAD → Transcript Handler identifies filler and resumes speech. ✅
- Quick "okay" (0.3s): Ignored by VAD → Transcript Handler identifies filler and suppresses it. ✅
"""

import logging
import re
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentServer, AgentSession, JobContext, JobProcess, cli
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("intelligent-kelly")
logger.setLevel(logging.INFO)
load_dotenv()

# =============================================================================
# CONFIGURATION - Command and Filler Detection
# =============================================================================

# Single words that mean "stop" as a command
STOP_WORDS = {"wait", "stop", "finish", "hold", "pause", "halt", "enough", "quiet"}

# Multi-word command phrases (normalized, no spaces)
STOP_PHRASES = {
    "holdon", "holdonthat", "waitasec", "waitasecond", "waitaminute",
    "stopit", "stopthat", "stopnow", "pausethat", "onemoment"
}

# Words that can precede a stop word to form a command
COMMAND_PREFIXES = {"no", "but", "and", "okay", "ok", "yeah", "yes", "hey", "please"}

# Pure filler/acknowledgment words (no overlap with meaningful words)
FILLER_WORDS = {
    "uhhuh", "okay", "alright", "mhm", "yeah", "yep", "yup",
    "hmm", "right", "uh", "um", "ah", "ok", "k", "sure", "yes",
    "interesting", "really", "wow", "ohh", "ooh", "aha", "mhmm",
    "gotcha", "nice", "oh", "no", "nah", "nope", "cool", "great"
}

# Multi-word filler phrases (normalized with spaces for matching)
FILLER_PHRASES = {
    "all right", "got it", "i see", "uh huh", "oh okay", "oh ok",
    "oh really", "oh wow", "oh nice", "sounds good", "makes sense",
    "i understand", "mm hmm", "uh huh"
}


def normalize_text(transcript: str) -> str:
    """Normalize transcript for consistent matching."""
    clean = transcript.lower().strip()
    clean = re.sub(r'[^\w\s]', '', clean)  # Remove punctuation
    clean = re.sub(r'\s+', ' ', clean)      # Collapse whitespace
    return clean.strip()


def contains_command(transcript: str) -> bool:
    """
    Check if transcript contains an explicit stop command.
    MUST be checked BEFORE is_filler_input() to avoid false negatives.
    """
    text = normalize_text(transcript)
    words = text.split()
    
    if not words:
        return False
    
    # Check for exact stop phrase match (e.g., "hold on")
    text_no_spaces = text.replace(" ", "")
    if text_no_spaces in STOP_PHRASES:
        return True
    
    # Check for stop phrase at start (e.g., "hold on a second please")
    for phrase in STOP_PHRASES:
        if text_no_spaces.startswith(phrase):
            return True
    
    # Direct command: first word is a stop word (e.g., "stop", "wait")
    if words[0] in STOP_WORDS:
        return True
    
    # Command after prefix: "yeah wait", "okay stop", "no hold on", "but wait"
    # Check first 3 words for pattern: [prefix] + [stop_word]
    for i in range(min(3, len(words))):
        if words[i] in STOP_WORDS:
            # If stop word is in first 3 positions, it's likely a command
            # Unless it's a long sentence where stop word is incidental
            if len(words) <= 5:
                return True
            # For longer sentences, only count if stop word is in first 2 positions
            if i < 2:
                return True
    
    # Pattern: prefix + stop word anywhere in first 4 words
    # e.g., "okay wait a second", "no hold on please"
    if len(words) >= 2:
        for i in range(min(3, len(words) - 1)):
            if words[i] in COMMAND_PREFIXES and words[i + 1] in STOP_WORDS:
                return True
    
    return False


def is_filler_input(transcript: str) -> bool:
    """
    Check if transcript is purely a filler acknowledgment.
    Only returns True if it's DEFINITELY a filler (no command content).
    """
    text = normalize_text(transcript)
    
    # CRITICAL: Command always takes priority - check first!
    if contains_command(transcript):
        return False
    
    # Empty or very short
    if not text:
        return True
    
    # Exact filler phrase match
    if text in FILLER_PHRASES:
        return True
    
    # Single word in filler set
    words = text.split()
    if len(words) == 1 and words[0] in FILLER_WORDS:
        return True
    
    # All words are fillers (e.g., "yeah yeah", "okay um", "oh really")
    if len(words) <= 3 and all(word in FILLER_WORDS for word in words):
        return True
    
    # Compound filler check (e.g., "uhhuh" -> "uh huh")
    text_no_spaces = text.replace(" ", "")
    if text_no_spaces in FILLER_WORDS:
        return True
    
    return False


# =============================================================================
# AGENT DEFINITION
# =============================================================================

class IntelligentAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. Keep responses concise and witty. "
                "When users say things like 'yeah' or 'okay' while you're speaking, "
                "it means they're listening - keep going! "
                "Only stop if they explicitly say 'wait', 'stop', or 'hold on'."
            ),
        )
        # Simplified state: only track if agent is currently speaking
        self._is_speaking = False
        # Track if VAD just interrupted (waiting for transcript to classify)
        self._interrupted_by_vad = False
    
    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
    
    @is_speaking.setter
    def is_speaking(self, value: bool) -> None:
        self._is_speaking = value
    
    @property
    def interrupted_by_vad(self) -> bool:
        return self._interrupted_by_vad
    
    @interrupted_by_vad.setter
    def interrupted_by_vad(self, value: bool) -> None:
        self._interrupted_by_vad = value

    async def on_enter(self):
        # Wait for user to speak first (no preemptive greeting)
        pass


# =============================================================================
# SERVER SETUP
# =============================================================================

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def try_clear_user_turn(session: AgentSession) -> bool:
    """Safely attempt to clear user turn to suppress LLM processing."""
    if hasattr(session, 'clear_user_turn'):
        try:
            session.clear_user_turn()
            return True
        except Exception as e:
            logger.debug(f"clear_user_turn failed: {e}")
    return False


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        
        # === HYBRID STRATEGY ===
        # Medium threshold: catches most fillers but allows quick commands through
        allow_interruptions=True,
        min_interruption_duration=0.6,   # 0.6s - slower than most commands
        min_interruption_words=2,         # Require 2+ words
        
        # Enable auto-resume for false positives (LiveKit handles this)
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
        
        preemptive_generation=False,
        min_endpointing_delay=0.5,
        max_endpointing_delay=2.5,
    )
    
    agent = IntelligentAgent()
    
    logger.info("=" * 70)
    logger.info("🚀 HYBRID INTELLIGENT INTERRUPTION HANDLER v2")
    logger.info("   Strategy: VAD(0.6s, 2words) + Transcript Classification")
    logger.info("=" * 70)
    
    # -------------------------------------------------------------------------
    # EVENT: Agent starts speaking
    # -------------------------------------------------------------------------
    @session.on("speech_created")
    def on_speech_created(ev):
        agent.is_speaking = True
        agent.interrupted_by_vad = False
        logger.info("🎤 Agent started speaking")
    
    # -------------------------------------------------------------------------
    # EVENT: Agent state changes
    # -------------------------------------------------------------------------
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        logger.debug(f"🎭 Agent: {ev.old_state} → {ev.new_state}")
        
        # Detect VAD interruption: speaking → listening transition
        if ev.old_state == "speaking" and ev.new_state == "listening":
            if agent.is_speaking:
                agent.interrupted_by_vad = True
                logger.info("⚠️ VAD interrupted - waiting for transcript...")
        
        # Update speaking state
        if ev.new_state in ("listening", "thinking"):
            agent.is_speaking = False
        elif ev.new_state == "speaking":
            agent.is_speaking = True
    
    # -------------------------------------------------------------------------
    # EVENT: User state changes (for logging only)
    # -------------------------------------------------------------------------
    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        logger.debug(f"👤 User: {ev.old_state} → {ev.new_state}")
    
    # -------------------------------------------------------------------------
    # EVENT: Transcript received - MAIN LOGIC
    # -------------------------------------------------------------------------
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev):
        # Only process final transcripts
        if not ev.is_final or not ev.transcript:
            return
        
        text = normalize_text(ev.transcript)
        if not text:
            return
        
        # Classify the input
        has_command = contains_command(text)
        is_filler = is_filler_input(text)
        
        logger.info(
            f"📝 '{text}' | speaking={agent.is_speaking} | "
            f"vad_interrupted={agent.interrupted_by_vad} | "
            f"cmd={has_command} | filler={is_filler}"
        )
        
        # =================================================================
        # CASE 1: VAD just interrupted - classify and decide
        # =================================================================
        if agent.interrupted_by_vad:
            agent.interrupted_by_vad = False  # Reset flag
            
            if has_command:
                # Real command - interruption was correct, let LLM process
                logger.info(f"🛑 COMMAND after VAD: '{text}' - valid interrupt")
                return  # Allow normal LLM processing
            
            if is_filler:
                # False positive - LiveKit's resume_false_interruption handles resume
                # Suppress transcript from LLM
                logger.info(f"🔄 FILLER after VAD: '{text}' - suppressing")
                try_clear_user_turn(session)
                return
            
            # Real input (not command, not filler) - valid interruption
            logger.info(f"✅ REAL INPUT after VAD: '{text}'")
            return  # Allow normal LLM processing
        
        # =================================================================
        # CASE 2: Agent is currently speaking (no VAD interrupt yet)
        # =================================================================
        if agent.is_speaking:
            if has_command:
                # Force interrupt on command that VAD missed
                logger.info(f"🛑 COMMAND while speaking: '{text}' - forcing interrupt")
                session.interrupt()
                return  # Allow LLM to process the command
            
            if is_filler:
                # Ignore filler - don't interrupt, don't pass to LLM
                logger.info(f"🔇 FILLER while speaking: '{text}' - ignored")
                try_clear_user_turn(session)
                return
            
            # Real input - interrupt and let LLM process
            logger.info(f"💬 INPUT while speaking: '{text}' - interrupting")
            session.interrupt()
            return
        
        # =================================================================
        # CASE 3: Agent is idle (not speaking)
        # =================================================================
        if is_filler:
            # Suppress lone fillers when idle
            logger.info(f"🍃 FILLER while idle: '{text}' - suppressed")
            try_clear_user_turn(session)
            return
        
        # Normal input - let LLM process
        logger.info(f"✅ INPUT while idle: '{text}'")
        # Allow normal processing
    
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
