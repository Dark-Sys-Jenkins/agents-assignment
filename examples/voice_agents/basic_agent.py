# examples/voice_agents/basic_agent.py
"""
Context-Aware Interruption Handling for LiveKit Voice Agents

This module implements a smart interruption filtering layer that distinguishes between:
- Passive acknowledgements ("yeah", "ok", "hmm") which should be IGNORED while agent speaks
- Active interruptions ("stop", "wait", "no") which should INTERRUPT the agent
- Mixed content ("yeah but wait") which should INTERRUPT (contains command words)

The logic is STATE-AWARE:
- When agent is SPEAKING: Filter backchannels, allow real interrupts
- When agent is SILENT: Process all input normally (including "yeah" as valid response)

Key Design Decision:
We set `allow_interruptions=False` to disable automatic VAD-triggered interruptions,
then manually control when interrupts happen based on transcript content analysis.
This prevents the "hiccup" where VAD triggers a pause before STT determines it's just "yeah".

Author: Assignment Implementation
See README.md for full documentation.
"""

import logging
import os
import re
from datetime import datetime
from typing import Set, List

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    UserInputTranscribedEvent,
    AgentStateChangedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")
load_dotenv()

# =============================================================================
# CONFIGURABLE WORD LISTS
# =============================================================================
# These lists can be customized via environment variables:
#   BACKCHANNEL_WORDS="yeah,ok,hmm,right"  (comma-separated)
#   INTERRUPT_WORDS="stop,wait,no,cancel"  (comma-separated)
# =============================================================================

_DEFAULT_BACKCHANNEL_WORDS: Set[str] = {
    # Short Fillers & Continuers (common during active listening)
    "ah", "aha", "hm", "hmm", "mhm", "mhmm",
    "mm-hmm", "mmhmm", "uh-huh", "um", "uh", "uhhuh",
    
    # Single letter variations (common STT transcription errors)
    "k", "m", "h", "a",

    # Affirmations & Agreement
    "absolutely", "exactly", "indeed", "right", "sure",
    "true", "understood", "correct", "definitely",

    # Casual Acknowledgments
    "alright", "cool", "fine", "nice", "ok", "okay",
    "yeah", "yep", "yes", "yup",

    # Multi-word phrases (handled as individual tokens)
    "go", "on", "got", "it", "i", "see", "makes", "sense",
    "keep", "going", "tell", "me", "more", "sounds", "good",

    # Reactions (passive, not commanding)
    "really", "wow", "interesting",
}

_DEFAULT_INTERRUPT_WORDS: Set[str] = {
    # Strong command words that ALWAYS trigger interruption
    "stop", "wait", "no", "hold", "cancel",
    "pause", "enough", "quiet", "silence", "shut",
    # Multi-word phrases (handled as individual tokens)
    "hang",  # "hang on"
    "but",   # "yeah but..." indicates user wants to interject
    "however", "actually", "question",
}

def _parse_word_list(env_name: str, default: Set[str]) -> Set[str]:
    """Parse a comma-separated word list from environment variable.
    
    Args:
        env_name: Name of the environment variable to read
        default: Default set of words if env var is not set
        
    Returns:
        Set of lowercase words for matching
    """
    raw = os.getenv(env_name)
    if not raw:
        return default.copy()  # Return a copy to prevent mutation
    return {w.strip().lower() for w in raw.split(",") if w.strip()}

# Initialize configurable word lists from environment or defaults
BACKCHANNEL_WORDS: Set[str] = _parse_word_list("BACKCHANNEL_WORDS", _DEFAULT_BACKCHANNEL_WORDS)
INTERRUPT_WORDS: Set[str] = _parse_word_list("INTERRUPT_WORDS", _DEFAULT_INTERRUPT_WORDS)

# =============================================================================
# TUNABLE THRESHOLDS
# =============================================================================
# MIN_WORD_LENGTH: Words shorter than this AND not in backchannel list may be
#                  ignored to filter STT noise. Default: 3
# DEBOUNCE_WINDOW_MS: Prevent duplicate interrupts within this window. Default: 300ms
# =============================================================================
MIN_WORD_LENGTH_FOR_NON_BACKCHANNEL: int = int(os.getenv("MIN_WORD_LENGTH", "3"))
DEBOUNCE_WINDOW_MS: int = int(os.getenv("DEBOUNCE_WINDOW_MS", "300"))


def _normalize_tokens(text: str) -> List[str]:
    """Normalize text into tokens for analysis.
    
    Handles:
    - Punctuation removal ("uh-huh." -> "uh-huh")
    - Hyphenated words ("uh-huh" stays as one token)
    - Case normalization
    - Common STT artifacts
    
    Args:
        text: Raw transcript text
        
    Returns:
        List of normalized lowercase tokens
    """
    if not text:
        return []
    # Remove trailing punctuation and extra whitespace
    text = text.strip().rstrip('.!?,;:"\'')
    # Split on non-word characters except hyphens (preserves "uh-huh")
    tokens = re.findall(r'\b[\w-]+\b', text.lower())
    # Filter empty tokens and pure punctuation
    return [t for t in tokens if t and not t.startswith('-')]


def is_soft_backchannel(text: str) -> bool:
    """Check if utterance consists ONLY of backchannel words.
    
    This is the primary filter for passive acknowledgements. Returns True only if
    EVERY word in the utterance is in the backchannel list.
    
    Examples:
        - "uh-huh." -> True
        - "yeah okay" -> True  
        - "K." -> True (common STT error for "okay")
        - "okay wait" -> False (contains interrupt word)
        - "tell me about Python" -> False (contains non-backchannel words)
    
    Args:
        text: Raw transcript text
        
    Returns:
        True if utterance should be ignored while agent is speaking
    """
    tokens = _normalize_tokens(text)
    if not tokens:
        return False
    # ALL tokens must be in backchannel list for this to be a soft backchannel
    return all(tok in BACKCHANNEL_WORDS for tok in tokens)


def contains_strong_interrupt(text: str) -> bool:
    """Check if utterance contains ANY strong interrupt word.
    
    This is the priority check - if ANY interrupt word is present, even in a
    mixed sentence like "yeah but wait", we should interrupt.
    
    Examples:
        - "stop" -> True
        - "yeah wait" -> True (contains "wait")
        - "no no no" -> True
        - "yeah okay" -> False
    
    Args:
        text: Raw transcript text
        
    Returns:
        True if agent should be interrupted immediately
    """
    tokens = _normalize_tokens(text)
    return any(tok in INTERRUPT_WORDS for tok in tokens)


def has_substantial_content(text: str) -> bool:
    """Check if text contains meaningful non-backchannel content.
    
    This catches real questions or commands that might slip through, like:
    - "yeah tell me more about Python" - contains "python" (substantial)
    - "okay what is that" - contains "what" (substantial, question word)
    
    Args:
        text: Raw transcript text
        
    Returns:
        True if text contains words that suggest real user intent
    """
    tokens = _normalize_tokens(text)
    for tok in tokens:
        # Word must be long enough AND not in backchannel list
        if len(tok) >= MIN_WORD_LENGTH_FOR_NON_BACKCHANNEL and tok not in BACKCHANNEL_WORDS:
            return True
    return False


class InterruptionDebouncer:
    """Prevents duplicate interruption calls within a short time window.
    
    This is important because:
    1. STT may send multiple interim transcripts for the same utterance
    2. User might say "stop stop stop" which should only trigger once
    3. Prevents race conditions in rapid speech scenarios
    """
    
    def __init__(self, window_ms: int = DEBOUNCE_WINDOW_MS) -> None:
        self.window_ms = window_ms
        self._last_interrupt_time: datetime | None = None
    
    def should_interrupt(self) -> bool:
        """Check if enough time has passed since last interrupt.
        
        Returns:
            True if we should allow this interrupt, False if debounced
        """
        now = datetime.now()
        if self._last_interrupt_time is None:
            self._last_interrupt_time = now
            return True
        
        elapsed_ms = (now - self._last_interrupt_time).total_seconds() * 1000
        if elapsed_ms > self.window_ms:
            self._last_interrupt_time = now
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset the debouncer state (e.g., when agent starts speaking)."""
        self._last_interrupt_time = None


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. "
                "You are a full conversational AI assistant and can freely discuss, explain, "
                "and reason about any topic the user asks. "
                "You are NOT limited to any single domain. "
                "You should only use tools when they are clearly useful, "
                "and you should never say that you are incapable of answering general questions. "
                "If a question is abstract or conceptual, explain it in simple terms. "
                "If the user asks about weather, you may use the weather tool. "
                "Keep responses concise, natural, and conversational. "
                "Do not use emojis, markdown, or special formatting. "
                "Speak in English."
            ),
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
        latitude: str,
        longitude: str,
    ):
        """
        OPTIONAL helper tool.
        Use this tool ONLY when the user explicitly asks for weather information.
        Do NOT use this tool for general conversation or explanations.
        """
        logger.info(f"Weather tool invoked for location: {location}")
        return "It is currently sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent session.
    
    This configures the AgentSession with:
    - allow_interruptions=False: Disables automatic VAD-triggered interruptions
    - We then manually control interrupts via the user_input_transcribed handler
    - This prevents the "hiccup" where VAD pauses before STT determines it's just "yeah"
    """
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        # STT: Deepgram Nova 3 for fast, accurate transcription
        stt="deepgram/nova-3",
        # LLM: Google Gemini 2.5 Flash for quick responses
        llm="google/gemini-2.5-flash",
        # TTS: Cartesia Sonic 2 with specific voice ID
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # Turn detection for multi-language support
        turn_detection=MultilingualModel(),
        # VAD for voice activity detection
        vad=ctx.proc.userdata["vad"],
        # Pre-generate responses for lower latency
        preemptive_generation=True,
        # CRITICAL: Disable automatic interruptions - we handle this manually
        # This prevents the agent from stopping on VAD triggers before we analyze the content
        allow_interruptions=False,
        # Don't discard audio - we need to analyze it
        discard_audio_if_uninterruptible=False,
        # Minimum speech duration to consider (helps filter noise)
        min_interruption_duration=0.5,
        # Minimum words needed (our manual handler adds context-awareness on top)
        min_interruption_words=1,
    )

    # Metrics logging
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # =========================================================================
    # INTELLIGENT INTERRUPTION LAYER
    # =========================================================================
    # This is the core logic for context-aware backchannel filtering.
    # 
    # The key insight: We use allow_interruptions=False to prevent automatic
    # VAD-triggered interruptions, then manually decide when to interrupt based
    # on the CONTENT of what the user says, not just that they spoke.
    # =========================================================================

    # Mutable state container for agent speaking status
    agent_state = {"is_speaking": False, "current_state": "listening"}
    debouncer = InterruptionDebouncer()

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent) -> None:
        """Track when the agent is speaking vs listening.
        
        Agent states: 'listening', 'thinking', 'speaking'
        We only filter backchannels when state is 'speaking'.
        """
        agent_state["current_state"] = ev.new_state
        agent_state["is_speaking"] = ev.new_state == "speaking"
        
        logger.debug(f"Agent state: {ev.old_state} -> {ev.new_state}")
        
        # Reset debouncer when agent starts speaking for fresh interrupt detection
        if ev.new_state == "speaking":
            debouncer.reset()

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        """Context-aware interruption handler.
        
        Logic Matrix:
        - "Yeah/Ok/Hmm" + Speaking -> IGNORE: Continue without pause
        - "Wait/Stop/No" + Speaking -> INTERRUPT: Stop immediately
        - "Yeah/Ok/Hmm" + Silent -> RESPOND: Process as valid input
        - "Yeah but wait" + Speaking -> INTERRUPT: Contains command word
        """
        text = (ev.transcript or "").strip()
        if not text:
            return

        # Log for debugging (use DEBUG level in production)
        logger.debug(
            f"Transcription: '{text}' | Final: {ev.is_final} | "
            f"Agent State: {agent_state['current_state']}"
        )

        # =====================================================================
        # CASE 1: Agent is NOT speaking -> Allow normal behavior
        # =====================================================================
        # When the agent is silent/listening, ALL user input should be processed
        # normally, including "yeah" (which might be answering "Are you ready?")
        if not agent_state["is_speaking"]:
            logger.debug(f"Agent idle, processing normally: '{text}'")
            return  # Let the framework handle this normally

        # =====================================================================
        # CASE 2: Agent IS speaking -> Apply filtering logic
        # =====================================================================

        # Priority 1: Strong interrupt words ALWAYS trigger interruption
        # Check this even on interim transcripts for faster response
        if contains_strong_interrupt(text):
            if debouncer.should_interrupt():
                logger.info(f"🛑 Strong interrupt detected: '{text}' | Interrupting agent")
                session.interrupt(force=True)
            else:
                logger.debug(f"Strong interrupt debounced: '{text}'")
            return

        # For interim transcripts while speaking: track but don't act yet
        # This prevents premature decisions on incomplete utterances
        if not ev.is_final:
            logger.debug(f"Interim while speaking, waiting for final: '{text}'")
            return

        # =====================================================================
        # FINAL TRANSCRIPT ANALYSIS (agent is speaking)
        # =====================================================================

        logger.info(f"📝 Final transcript while agent speaking: '{text}'")

        # Check 1: Pure soft backchannel? -> IGNORE completely
        if is_soft_backchannel(text):
            logger.info(f"✓ Ignoring soft backchannel: '{text}'")
            session.clear_user_turn()  # Discard this input
            return

        # Check 2: Contains substantial content (real question/command)?
        if has_substantial_content(text):
            if debouncer.should_interrupt():
                logger.info(f"🛑 Substantial content detected: '{text}' | Interrupting")
                session.interrupt(force=True)
            else:
                logger.debug(f"Substantial interrupt debounced: '{text}'")
            return

        # Check 3: Very short input that's a backchannel (STT artifacts like "K.")
        normalized = _normalize_tokens(text)
        if len(normalized) == 1 and len(normalized[0]) <= 2:
            if normalized[0] in BACKCHANNEL_WORDS:
                logger.info(f"✓ Ignoring likely STT artifact: '{text}' -> '{normalized[0]}'")
                session.clear_user_turn()
                return

        # Check 4: Multiple short backchannel words together
        if all(len(tok) <= 2 and tok in BACKCHANNEL_WORDS for tok in normalized):
            logger.info(f"✓ Ignoring multi-word backchannel: '{text}'")
            session.clear_user_turn()
            return

        # Default fallback: Ambiguous input - interrupt to be safe
        # This ensures we don't miss real user intent
        if debouncer.should_interrupt():
            logger.info(f"⚠️ Ambiguous input while speaking: '{text}' | Interrupting (fallback)")
            session.interrupt(force=True)
        else:
            logger.debug(f"Ambiguous interrupt debounced: '{text}'")

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)