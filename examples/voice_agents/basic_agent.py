import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
    stt,
    vad, # Added for turn detection constant
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")
load_dotenv()

# 1. CONFIGURABLE IGNORE LIST
IGNORE_LIST = {'yeah', 'ok', 'aha', 'hmm', 'uh-huh', 'right', 'yep', 'okay'}

## Updated MyAgent Class

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and to the point."
            ),
            allow_interruptions=True, 
        )
        self._is_speaking = False  # Custom flag to track state

    async def on_enter(self):
        # Link the session events to our flag
        @self.session.on("agent_speech_started")
        def _started():
            self._is_speaking = True

        @self.session.on("agent_speech_stopped")
        def _stopped():
            self._is_speaking = False

    def should_ignore_input(self, text: str) -> bool:
        clean_text = text.strip().lower()
        clean_text = ''.join(c for c in clean_text if c.isalnum() or c.isspace())
        return clean_text in IGNORE_LIST

    async def stt_node(self, audio, model_settings):
        stt_stream = super().stt_node(audio, model_settings)

        async for event in stt_stream:
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                text = event.alternatives[0].text
                
                if self._is_speaking:
                    if self.should_ignore_input(text):
                        logger.info(f"--- IGNORE: '{text}' ---")
                        continue # Drop the event so the LLM doesn't get it
                    else:
                        logger.info(f"--- INTERRUPTING for: '{text}' ---")
                        # Use the public API to kill the current speech
                        self.session.interrupt()
                
            yield event

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str, latitude: str, longitude: str):
        """Called when the user asks for weather related information."""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # REQUIRED FOR ASSIGNMENT LOGIC:
        discard_audio_if_uninterruptible=False, 
    )

    @session.on("user_input_transcribed")
    def on_transcription(ev):
        # This will print EVERY word the STT hears, even if your 
        # logic layer is accidentally filtering it out.
        print(f"DEBUG STT HEARD: {ev.transcript}")

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)