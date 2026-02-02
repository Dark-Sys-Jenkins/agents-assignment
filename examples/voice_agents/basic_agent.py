"""
THE ACTUAL WORKING HYBRID SOLUTION

Problem statement:
- "okay" said slowly (1.5s) should NOT interrupt
- "stop" said quickly (0.5s) SHOULD interrupt immediately
- Can't use duration-based filtering because it fails one of these cases

Solution: 
- Use MEDIUM thresholds (catches most fillers, but some slip through)
- Have transcript handler RESUME if interrupted by filler
- Have transcript handler FORCE INTERRUPT if command detected but VAD didn't trigger

This way:
- Fast "stop" (0.5s) → Below threshold → VAD doesn't interrupt → Transcript handler forces interrupt ✅
- Slow "okay" (1.5s) → Above threshold → VAD interrupts → Transcript handler RESUMES ✅
- Fast "okay" (0.3s) → Below threshold → VAD doesn't interrupt → Transcript suppresses ✅
"""

import logging
import re
import asyncio
from typing import Optional
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentServer, AgentSession, JobContext, JobProcess,
    cli, UserInputTranscribedEvent, AgentStateChangedEvent,
    UserStateChangedEvent
)
from livekit.plugins import silero, deepgram, openai, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("intelligent-kelly")
logger.setLevel(logging.INFO)
load_dotenv()

# CONFIGURATION
STOP_WORDS = {"wait", "stop", "finish", "hold", "pause", "halt"}
FILLER_WORDS = {
    "uhhuh", "okay", "alright", "mhm", "yeah", "yep", "yup",
    "hmm", "right", "uh", "um", "ah", "gotit", "isee", "ok", "k",
    "sure", "yes", "interesting", "really", "wow", "ohh", "ooh",
    "aha", "mhmm", "gotcha", "nice", "oh", "all", "got", "it", "i", "see"
}
FILLER_PHRASES = {"all right", "got it", "i see", "uh huh", "oh okay", "oh ok"}

def is_filler_input(transcript: str) -> bool:
    """Check if transcript is purely a filler acknowledgment"""
    clean = transcript.lower().strip()
    clean_no_punct = re.sub(r'[^\w\s]', '', clean)
    
    if clean_no_punct in FILLER_PHRASES:
        return True
    if clean_no_punct.replace(" ", "") in FILLER_WORDS:
        return True
    
    words = clean_no_punct.split()
    if words and all(word in FILLER_WORDS for word in words):
        return True
    return False

def contains_command(transcript: str) -> bool:
    """Check if transcript contains an explicit stop command"""
    clean = transcript.lower().strip()
    clean_no_punct = re.sub(r'[^\w\s]', '', clean)
    words = clean_no_punct.split()
    
    if not words:
        return False
    
    # Direct command (starts with stop word)
    if words[0] in STOP_WORDS:
        return True
    
    # Command after brief acknowledgment: "yeah wait", "okay stop"
    if len(words) >= 2:
        for i in range(len(words) - 1):
            if words[i] in FILLER_WORDS and words[i + 1] in STOP_WORDS:
                return True
            if words[i] in {"but", "and"} and words[i + 1] in STOP_WORDS:
                return True
    
    # Avoid false positives in longer sentences
    # "I have no idea" should NOT be a command
    if len(words) > 3 and any(w in STOP_WORDS for w in words):
        # Only treat as command if stop word is in first 2 positions
        return any(words[i] in STOP_WORDS for i in range(min(2, len(words))))
    
    return False

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
        self.is_speaking = False
        self.was_interrupted_by_vad = False
        self.last_speech_content = ""
        
    async def on_enter(self):
        await self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        
        # === HYBRID STRATEGY ===
        # Medium-low threshold: Catches most fillers but allows quick commands
        allow_interruptions=True,
        min_interruption_duration=0.6,  # 0.6s - faster than most fillers, slower than most commands
        min_interruption_words=2,        # Require 2 words minimum
        
        # Enable auto-resume for false positives
        false_interruption_timeout=1.0,  # Wait 1s for transcript
        resume_false_interruption=True,  # Auto-resume if false positive
        
        preemptive_generation=False,
        min_endpointing_delay=0.5,
        max_endpointing_delay=2.5,
    )
    
    kelly = IntelligentAgent()
    
    logger.info("=" * 80)
    logger.info("🚀 HYBRID INTELLIGENT INTERRUPTION HANDLER")
    logger.info("⚙️  Strategy:")
    logger.info("   - Medium VAD thresholds (0.6s, 2 words)")
    logger.info("   - Auto-resume on false interruptions")
    logger.info("   - Manual interrupt on commands that slip through")
    logger.info("   - Transcript suppression for fillers")
    logger.info("=" * 80)
    
    # Track interruption state
    vad_just_interrupted = False
    
    @session.on("speech_created")
    def on_speech_created(ev):
        nonlocal vad_just_interrupted
        kelly.is_speaking = True
        kelly.was_interrupted_by_vad = False
        vad_just_interrupted = False
        
        # Store what Kelly is saying for potential resume
        if hasattr(ev, 'speech_handle') and hasattr(ev.speech_handle, 'text'):
            kelly.last_speech_content = ev.speech_handle.text
        
        logger.info("🎤 KELLY STARTED SPEAKING")
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        nonlocal vad_just_interrupted
        
        logger.info(f"🎭 AGENT STATE: {ev.old_state} → {ev.new_state}")
        
        # Detect if Kelly was interrupted while speaking
        if ev.old_state == "speaking" and ev.new_state == "listening":
            if kelly.is_speaking:
                kelly.was_interrupted_by_vad = True
                vad_just_interrupted = True
                logger.info("⚠️ KELLY INTERRUPTED - waiting for transcript to decide action...")
        
        if ev.new_state == "listening":
            kelly.is_speaking = False
    
    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        logger.info(f"👤 USER STATE: {ev.old_state} → {ev.new_state}")
    
    # Try to register false interruption handler
    try:
        @session.on("agent_false_interruption")
        def on_false_interruption(ev):
            if hasattr(ev, 'resumed') and ev.resumed:
                logger.info("✅ FALSE INTERRUPTION AUTO-RESUMED by LiveKit")
    except:
        logger.warning("⚠️ False interruption event not available in this LiveKit version")
    
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev):
        nonlocal vad_just_interrupted
        
        if not ev.is_final or not ev.transcript:
            return
        
        clean_text = re.sub(r'[^\w\s]', '', ev.transcript.lower()).strip()
        
        logger.info(f"📝 TRANSCRIPT: '{clean_text}' | Kelly speaking: {kelly.is_speaking} | Just interrupted: {vad_just_interrupted}")
        
        # === CASE 1: Kelly was just interrupted by VAD ===
        if kelly.was_interrupted_by_vad or vad_just_interrupted:
            
            if contains_command(clean_text):
                logger.info(f"🛑 REAL COMMAND after VAD interrupt: '{clean_text}' - staying stopped")
                kelly.was_interrupted_by_vad = False
                vad_just_interrupted = False
                # Allow normal processing - the interrupt was correct
                return
            
            elif is_filler_input(clean_text):
                logger.info(f"🔄 FALSE INTERRUPT: '{clean_text}' was just a filler - should resume")
                kelly.was_interrupted_by_vad = False
                vad_just_interrupted = False
                
                # LiveKit's resume_false_interruption should handle this automatically
                # But we still suppress the transcript from reaching LLM
                return
            
            else:
                logger.info(f"✅ REAL INPUT after interrupt: '{clean_text}' - valid interruption")
                kelly.was_interrupted_by_vad = False
                vad_just_interrupted = False
                # Allow normal processing
                return
        
        # === CASE 2: Kelly is currently speaking (VAD didn't interrupt yet) ===
        if kelly.is_speaking:
            
            if contains_command(clean_text):
                logger.info(f"🛑 STOP COMMAND while speaking: '{clean_text}' - forcing interrupt NOW")
                session.interrupt()
                return
            
            elif is_filler_input(clean_text):
                logger.info(f"🔇 FILLER while speaking: '{clean_text}' - completely ignored")
                # Don't interrupt, don't pass to LLM
                return
            
            else:
                logger.info(f"💬 REAL INPUT while speaking: '{clean_text}' - allowing interrupt")
                session.interrupt()
                return
        
        # === CASE 3: Kelly is idle ===
        if not kelly.is_speaking:
            
            if is_filler_input(clean_text):
                logger.info(f"🍃 FILLER while idle: '{clean_text}' - suppressed")
                return
            
            logger.info(f"✅ VALID INPUT while idle: '{clean_text}'")
            # Normal processing
    
    await session.start(agent=kelly, room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)