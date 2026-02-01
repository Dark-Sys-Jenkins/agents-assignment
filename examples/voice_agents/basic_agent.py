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

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

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
