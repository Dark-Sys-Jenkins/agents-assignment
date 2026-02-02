import asyncio
import logging
import re

from dotenv import load_dotenv
import os

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)

from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("interrupt-handler")
logger.setLevel(logging.INFO)

load_dotenv()

# Load word lists from environment variables with sensible defaults
# Users can customize via .env file: SOFT_INTERRUPT_WORDS="yeah,ok,hmm,..."
_default_soft_words = (
    "yeah,yes,yep,yup,yea,ya,uh huh,uh-huh,uhhuh,"
    "ok,okay,k,alright,allright,all right,"
    "hmm,hm,mmm,mm,mhm,mhmm,uhm,um,uh,ah,oh,ohh,ooh,"
    "got it,gotit,i see,isee,i get it,understood,right,correct,"
    "sure,nice,cool,great,good,awesome,interesting,"
    "really,wow,whoa,aha,ohhh,gotcha"
)

_default_interrupt_keywords = "wait,stop,pause,cancel,hold on,hold,actually,halt,finish,no"

# Parse from environment or use defaults
SOFT_INTERRUPT_WORDS = set(
    os.getenv("SOFT_INTERRUPT_WORDS", _default_soft_words).lower().split(",")
)
SOFT_INTERRUPT_WORDS = {word.strip() for word in SOFT_INTERRUPT_WORDS if word.strip()}

INTERRUPT_KEYWORDS = set(
    os.getenv("INTERRUPT_KEYWORDS", _default_interrupt_keywords).lower().split(",")
)
INTERRUPT_KEYWORDS = {word.strip() for word in INTERRUPT_KEYWORDS if word.strip()}

logger.info(f"Loaded {len(SOFT_INTERRUPT_WORDS)} soft words and {len(INTERRUPT_KEYWORDS)} interrupt keywords")
logger.debug(f"First 10 soft words: {list(SOFT_INTERRUPT_WORDS)[:10]}")
logger.debug(f"Interrupt keywords: {list(INTERRUPT_KEYWORDS)}")

def is_only_soft_words(text: str) -> bool:
    """Check if text contains ONLY soft acknowledgment words"""
    if not text:
        return False
    
    # Clean the text - convert to lowercase and remove ALL punctuation
    cleaned = text.lower().strip()
    # Remove ALL non-alphanumeric characters except spaces
    cleaned = re.sub(r'[^a-z0-9\s]', '', cleaned)
    cleaned = cleaned.strip()
    
    logger.debug(f"[SOFT WORD CHECK] Original: '{text}' | Cleaned: '{cleaned}'")
    
    if not cleaned:
        return False
    
    # Check if it's a single soft word (with spaces removed for phrases like "uh huh")
    cleaned_no_spaces = cleaned.replace(" ", "")
    if cleaned_no_spaces in SOFT_INTERRUPT_WORDS:
        logger.debug(f"[SOFT WORD CHECK] ✅ Matched as single word: '{cleaned_no_spaces}'")
        return True
    
    # Check if ALL words are soft words
    words = cleaned.split()
    if words and all(word in SOFT_INTERRUPT_WORDS for word in words):
        logger.debug(f"[SOFT WORD CHECK] ✅ All words are soft: {words}")
        return True
    
    logger.debug(f"[SOFT WORD CHECK] ❌ NOT soft words: {words}")
    return False

def contains_interrupt_keyword(text: str) -> bool:
    """Check if text contains an interrupt keyword"""
    if not text:
        return False
    
    # Clean the text - convert to lowercase and remove ALL punctuation
    import re
    cleaned = text.lower().strip()
    # Remove ALL non-alphanumeric characters except spaces
    cleaned = re.sub(r'[^a-z0-9\s]', '', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned:
        return False
    
    words = cleaned.split()
    if not words:
        return False
    
    # Check if any interrupt keyword appears
    # Prioritize first 2 words to avoid false positives in longer sentences
    if len(words) <= 3:
        return any(word in INTERRUPT_KEYWORDS for word in words)
    else:
        # For longer sentences, only check first 2 positions
        return any(words[i] in INTERRUPT_KEYWORDS for i in range(min(2, len(words))))

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Luna. You interact with users via voice. "
                "Keep your responses concise and to the point. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "You are curious, friendly, and lightly humorous. "
                "You always speak English."
            )
        )

    async def on_enter(self):
        self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        # Auto-resume on false interruptions (critical for seamless ignoring)
        resume_false_interruption=True,
        false_interruption_timeout=0.8,  # Shorter timeout for faster resume
        # Lower threshold to allow interrupt keywords through while filtering very short sounds
        min_interruption_duration=0.3,  # 300ms - allows "stop" but filters very brief sounds
    )

    agent_speaking = False
    was_vad_interrupted = False
    last_processed_soft_word = None

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    @session.on("agent_started_speaking")
    def _on_agent_started():
        nonlocal agent_speaking, was_vad_interrupted
        agent_speaking = True
        was_vad_interrupted = False
        logger.debug("Agent started speaking")

    @session.on("agent_stopped_speaking")
    def _on_agent_stopped():
        nonlocal agent_speaking
        agent_speaking = False
        logger.debug("Agent stopped speaking")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        nonlocal was_vad_interrupted
        # Detect when VAD interrupts the agent
        if ev.old_state == "speaking" and ev.new_state == "listening":
            was_vad_interrupted = True
            logger.debug("⚠️ VAD interruption detected")

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev):
        """
        Intelligent interruption handler with COMPLETE IGNORING:
        - Agent speaking + soft word → COMPLETELY IGNORE (invisible to agent)
        - Agent speaking + interrupt keyword → INTERRUPT (force stop)
        - Agent speaking + real input → INTERRUPT (allow)
        - Agent silent + anything → PROCESS NORMALLY
        
        Processes both interim and final transcripts for instant detection.
        """
        nonlocal agent_speaking, was_vad_interrupted, last_processed_soft_word

        # Skip empty transcripts
        if not ev.transcript:
            return

        text = ev.transcript.strip()
        is_final = ev.is_final
        
        # === AGENT IS SPEAKING ===
        if agent_speaking:
            
            # Check for interrupt keywords FIRST (highest priority)
            if contains_interrupt_keyword(text):
                if is_final:
                    logger.info(f"INTERRUPT KEYWORD: '{text}' - STOPPING IMMEDIATELY")
                    last_processed_soft_word = None
                    was_vad_interrupted = False
                    session.interrupt()
                return
            
            # Check if it's ONLY soft words
            if is_only_soft_words(text):
                # Avoid duplicate processing of the same soft word
                if is_final and text == last_processed_soft_word:
                    logger.debug(f"⏭Skipping duplicate: '{text}'")
                    return
                
                if is_final:
                    logger.info(f"SOFT WORD DETECTED: '{text}' | VAD interrupted: {was_vad_interrupted}")
                    last_processed_soft_word = text
                    
                    # Only resume if VAD actually interrupted
                    if was_vad_interrupted:
                        logger.info(f"RESUMING AGENT - '{text}' was a false interrupt")
                        session.resume()
                        was_vad_interrupted = False
                    else:
                        logger.info(f"IGNORING - '{text}' didn't cause interruption (VAD threshold worked)")
                else:
                    logger.debug(f"Soft word (interim): '{text}' | agent_speaking: {agent_speaking}")
                
                return
            
            # Otherwise it's real input - allow interruption
            if is_final:
                logger.info(f"REAL INPUT: '{text}' - interrupting agent")
                last_processed_soft_word = None
                was_vad_interrupted = False
                session.interrupt()
            return

        # === AGENT IS SILENT ===
        else:
            if is_final:
                logger.info(f"AGENT SILENT - processing normally: '{text}'")
                last_processed_soft_word = None
                was_vad_interrupted = False
            # Process normally - don't interfere

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)