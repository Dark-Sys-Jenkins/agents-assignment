import logging
import re
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentServer, AgentSession, JobContext, JobProcess,
    cli, metrics, UserInputTranscribedEvent, AgentStateChangedEvent,
    UserStateChangedEvent, SpeechCreatedEvent, AgentFalseInterruptionEvent
)
from livekit.plugins import silero, deepgram, openai, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("intelligent-kelly")
logger.setLevel(logging.INFO)
load_dotenv()

# CONFIGURATION: Easily adjustable lists for modularity
STOP_WORDS = {"wait", "no", "stop", "finish", "hold", "pause", "hold on"}
FILLER_WORDS = {
    "uhhuh", "okay", "alright", "mhm", "yeah", "yep", "yup", 
    "hmm", "right", "uh", "um", "ah", "gotit", "isee", "ok", "k",
    "sure", "yes", "interesting", "really", "wow", "ohh", "ooh",
    "aha", "uhuh", "mhmm", "gotcha", "nice"
}

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. Keep responses concise and witty. "
                "If you hear acknowledgements like 'yeah' or 'ok' while explaining something, "
                "that means the user is listening - keep going! "
                "Only stop if they explicitly ask you to wait or stop."
            ),
        )
        # More reliable state tracking
        self.is_speaking = False
        self.current_speech_handle = None
        
    async def on_enter(self):
        await self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # === CRITICAL: Configure false interruption handling ===
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        
        # === PRIMARY DEFENSE: Built-in False Interruption Handling ===
        # These parameters tell LiveKit to wait for real speech before committing to an interruption
        allow_interruptions=True,
        
        # Require at least 0.8 seconds of detected speech before interrupting
        # This filters out most short fillers like "yeah", "ok", "hmm"
        min_interruption_duration=0.8,  
        
        # Require at least 2 words to be transcribed before confirming interruption
        # Single filler words won't trigger interruption
        min_interruption_words=2,
        
        # Wait up to 1 second for transcription after VAD detects speech
        # If no real words are transcribed, treat it as a false interruption
        false_interruption_timeout=1.0,
        
        # Automatically resume speaking if interruption was false positive
        # This is THE KEY FEATURE for seamless continuation
        resume_false_interruption=True,
        
        # Don't buffer audio while agent is speaking
        discard_audio_if_uninterruptible=True,
        
        # Other important settings
        preemptive_generation=False,
        min_endpointing_delay=0.6,
        max_endpointing_delay=3.0,
    )
    
    kelly = MyAgent()
    
    # === STATE TRACKING ===
    
    @session.on("speech_created")
    def on_speech_created(ev: SpeechCreatedEvent):
        """Track when Kelly actually starts speaking audio"""
        kelly.is_speaking = True
        kelly.current_speech_handle = ev.speech_handle
        logger.info("🎤 KELLY STARTED SPEAKING")
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        """Track agent state transitions"""
        logger.info(f"🎭 AGENT STATE: {ev.old_state} → {ev.new_state}")
        
        # Kelly is no longer speaking when she returns to listening
        if ev.new_state == "listening":
            kelly.is_speaking = False
            kelly.current_speech_handle = None
            logger.info("👂 Kelly finished and is now listening")
    
    @session.on("user_state_changed")
    def on_user_state_changed(ev: UserStateChangedEvent):
        """Track user state for debugging"""
        logger.info(f"👤 USER STATE: {ev.old_state} → {ev.new_state}")
    
    @session.on("agent_false_interruption")
    def on_false_interruption(ev: AgentFalseInterruptionEvent):
        """Log when false interruptions are detected and resumed"""
        if ev.resumed:
            logger.info("✅ FALSE INTERRUPTION: Kelly resumed seamlessly")
        else:
            logger.warning("⚠️ FALSE INTERRUPTION: Not auto-resumed")
    
    # === SECONDARY FILTER: Transcript-Level Suppression ===
    
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        """
        This handler provides a SECONDARY layer of defense.
        It runs after STT completes, so it can't prevent the initial VAD interruption,
        but it can prevent filler words from reaching the LLM and generating responses.
        """
        if not ev.is_final or not ev.transcript:
            return
        
        # Normalize text: lowercase, remove punctuation
        clean_text = re.sub(r'[^\w\s]', '', ev.transcript.lower()).strip()
        words = set(clean_text.split())
        raw_phrase = clean_text.replace(" ", "")  # For "uhhuh" type phrases
        
        if not words:
            return
        
        logger.info(f"📝 TRANSCRIPT: '{clean_text}' | Kelly speaking: {kelly.is_speaking}")
        
        # === CASE 1: Command words ALWAYS cause interruption ===
        if words.intersection(STOP_WORDS):
            logger.info(f"🛑 COMMAND DETECTED: '{clean_text}' → Calling interrupt()")
            session.interrupt()
            return
        
        # === CASE 2: Pure filler words while Kelly is speaking ===
        # These should be ignored - don't let them reach the LLM
        if kelly.is_speaking and (raw_phrase in FILLER_WORDS or words.issubset(FILLER_WORDS)):
            logger.info(f"🔇 FILLER SUPPRESSED: '{clean_text}' ignored during speech")
            # By returning here without calling session.interrupt() or forwarding to LLM,
            # we ensure this transcript is effectively dropped
            return
        
        # === CASE 3: Lone filler when Kelly is silent ===
        # Still suppress these - they shouldn't trigger LLM processing
        if not kelly.is_speaking and (raw_phrase in FILLER_WORDS or words.issubset(FILLER_WORDS)):
            logger.info(f"🍃 LONE FILLER: '{clean_text}' suppressed (Kelly idle)")
            return
        
        # === CASE 4: Real user input (commands, questions, statements) ===
        logger.info(f"✅ VALID INPUT: '{clean_text}' forwarded to LLM")
        # Let this proceed normally - it will reach the LLM
    
    await session.start(agent=kelly, room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)