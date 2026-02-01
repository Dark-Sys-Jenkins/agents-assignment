import logging
import re
from dotenv import load_dotenv

from livekit.agents import (
   Agent, AgentServer, AgentSession, JobContext, JobProcess,
    cli, metrics, UserInputTranscribedEvent, AgentStateChangedEvent,
    UserStateChangedEvent, SpeechCreatedEvent, AgentFalseInterruptionEvent
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation
STOP_WORDS = {"wait", "no", "stop", "finish", "hold", "pause", "hold on"}
FILLER_WORDS = {
    "uhhuh", "okay", "alright", "mhm", "yeah", "yep", "yup", 
    "hmm", "right", "uh", "um", "ah", "gotit", "isee", "ok", "k",
    "sure", "yes", "interesting", "really", "wow", "ohh", "ooh",
    "aha", "uhuh", "mhmm", "gotcha", "nice"
}
logger = logging.getLogger("intelligent-kelly")

load_dotenv()


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )
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
   
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        allow_interruptions=True,
        min_interruption_duration=0.8,  
        min_interruption_words=2,
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
        discard_audio_if_uninterruptible=True,
        preemptive_generation=False,
        min_endpointing_delay=0.6,
        max_endpointing_delay=3.0,
    )
    kelly = MyAgent()
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

    
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        """
        This handler provides a SECONDARY layer of defense.
        It runs after STT completes, so it can't prevent the initial VAD interruption,
        but it can prevent filler words from reaching the LLM and generating responses.
        """
        if not ev.is_final or not ev.transcript:
            return
        
        clean_text = re.sub(r'[^\w\s]', '', ev.transcript.lower()).strip()
        words = set(clean_text.split())
        raw_phrase = clean_text.replace(" ", "")  # For "uhhuh" type phrases
        
        if not words:
            return
        
        logger.info(f"📝 TRANSCRIPT: '{clean_text}' | Kelly speaking: {kelly.is_speaking}")
        
        
        if words.intersection(STOP_WORDS):
            logger.info(f"🛑 COMMAND DETECTED: '{clean_text}' → Calling interrupt()")
            session.interrupt()
            return
    
        if kelly.is_speaking and (raw_phrase in FILLER_WORDS or words.issubset(FILLER_WORDS)):
            logger.info(f"🔇 FILLER SUPPRESSED: '{clean_text}' ignored during speech")
           
            return
        
        if not kelly.is_speaking and (raw_phrase in FILLER_WORDS or words.issubset(FILLER_WORDS)):
            logger.info(f"🍃 LONE FILLER: '{clean_text}' suppressed (Kelly idle)")
            return
        
        logger.info(f"✅ VALID INPUT: '{clean_text}' forwarded to LLM")
       
    await session.start(agent=kelly, room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)