import logging
import os
import asyncio
from enum import Enum
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    UserInputTranscribedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.plugins import silero, deepgram, openai, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()
logger = logging.getLogger("basic-agent")

# =================================================================================
# 1. LOGIC CONTROLLER
# =================================================================================

class Decision(Enum):
    IGNORE = "ignore"
    INTERRUPT = "interrupt"
    NO_DECISION = "no_decision"

class InterruptionController:
    def __init__(self):
        self.interrupt_words = {
            "stop", "wait", "cancel", "pause", "no", "hold", "hang", "shh"
        }
        self.filler_words = {
            "yeah", "yep", "yes", "ok", "okay", "sure", "cool", 
            "right", "correct", "uh-huh", "mhm", "aha", "wow"
        }

    def decide(self, transcript: str, is_final: bool) -> Decision:
        text = transcript.lower().strip().replace('.', '').replace('!', '').replace('?', '')
        words = text.split()
        
        if not words:
            return Decision.NO_DECISION

        if any(w in self.interrupt_words for w in words):
            return Decision.INTERRUPT

        if all(w in self.filler_words for w in words):
            return Decision.IGNORE

        return Decision.NO_DECISION

# =================================================================================
# 2. AGENT DEFINITION
# =================================================================================

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Jarvis. You are a helpful assistant. "
                "You provide detailed and interesting answers. "
                "CRITICAL: If the user says 'stop', 'wait', or interrupts you, STOP immediately and remain silent. "
                "Do not reply with 'stop' or 'okay'. Just wait for the next question."
            ),
        )

    async def on_enter(self):
        logger.info("Agent connected. Waiting for user input...")
        pass

# =================================================================================
# 3. MAIN ENTRYPOINT
# =================================================================================

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    interrupt_controller = InterruptionController()
    
    session = AgentSession(
        stt="deepgram/nova-3",
        llm=openai.LLM(
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        tts="cartesia/sonic-2",
        
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        min_interruption_words=2, 
        resume_false_interruption=False, 
        preemptive_generation=True,
    )

    # ------------------------------------------------------------------
    # EVENT: MANUAL INTERRUPT HANDLER
    # ------------------------------------------------------------------
    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent):
        transcript = ev.transcript.strip()
        if not transcript:
            return

        decision = interrupt_controller.decide(transcript, ev.is_final)

        if decision == Decision.INTERRUPT:
            logger.info(f"INTERRUPT COMMAND DETECTED: '{transcript}'")
            session.interrupt()  # Force stop audio
            
            # --- THE FIX ---
            # If the user said "Stop", we clear it so the LLM doesn't hear it.
            # This prevents the agent from replying "Stop" or "Okay".
            # It will just be silent and wait for your next command.
            if ev.is_final:
                session.clear_user_turn()
            
        elif decision == Decision.IGNORE:
            if ev.is_final:
                logger.info(f"IGNORING FILLER: '{transcript}'")
                session.clear_user_turn()

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