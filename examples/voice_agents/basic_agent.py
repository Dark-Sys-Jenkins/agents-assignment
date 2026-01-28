import logging
import string
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
)
from livekit.agents.llm import function_tool, TranscriptionEvent
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")

load_dotenv()

# --- STEP 1: Define the Configurable Ignore List ---
IGNORE_LIST = ["yeah", "ok", "okay", "hmm", "right", "uh-huh", "aha"]

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
            "Keep your responses concise and to the point. "
            "Do not use emojis, asterisks, markdown, or special characters. "
            "You are curious, friendly, and have a sense of humor. "
            "Speak English to the user.",
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
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

    # --- STEP 2: Update AgentSession Settings ---
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        # We disable default interruptions to implement our custom logic matrix
        allow_interruptions=False, 
    )

    # --- STEP 3: Implement Context-Aware Interruption Logic ---
    @session.on("user_transcript_finished")
    def _on_transcript(ev: TranscriptionEvent):
        # Clean the text: lowercase and remove punctuation
        text = ev.transcript.lower().strip().translate(str.maketrans('', '', string.punctuation))
        words = text.split()
        
        if not words:
            return

        # Check the logic matrix: Agent is Speaking vs Agent is Silent
        if session.agent.is_speaking:
            # Semantic check: Are ALL words in the ignore list?
            is_filler_only = all(word in IGNORE_LIST for word in words)
            
            if is_filler_only:
                # LOGIC: IGNORE (Agent continues speaking without pausing)
                logger.info(f"PASSIVE ACKNOWLEDGEMENT DETECTED: Ignoring '{text}'")
                return 
            else:
                # LOGIC: INTERRUPT (User said something like "Wait" or "Stop")
                logger.info(f"ACTIVE INTERRUPTION DETECTED: Stopping for '{text}'")
                session.agent.interrupt()
        else:
            # LOGIC: RESPOND (Normal behavior when agent is silent)
            logger.info(f"VALID INPUT WHILE SILENT: Processing '{text}'")

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