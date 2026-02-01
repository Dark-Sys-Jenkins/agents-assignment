import logging

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

    
    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # uncomment to enable the Krisp BVC noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
