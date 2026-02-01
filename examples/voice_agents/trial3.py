import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentStateChangedEvent,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    UserInputTranscribedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import groq, silero,deepgram
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Add current directory to path for salescode_interrupt_handler import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from salescode_interrupt_handler.controllers import Decision, InterruptionController

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

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

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    # @function_tool
    # async def lookup_weather(
    #     self, context: RunContext, location: str, latitude: str, longitude: str
    # ):
    #     """Called when the user asks for weather related information.
    #     Ensure the user's location (city or region) is provided.
    #     When given a location, please estimate the latitude and longitude of the location and
    #     do not ask the user for them.

    #     Args:
    #         location: The location they are asking for
    #         latitude: The latitude of the location, do not ask user for it
    #         longitude: The longitude of the location, do not ask user for it
    #     """

    #     logger.info(f"Looking up weather for {location}")

    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Initialize the intelligent interrupt controller
    interrupt_controller = InterruptionController()
    logger.info("[START] InterruptionController initialized")
    
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt="deepgram/nova-3",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
       tts=deepgram.TTS(model="aura-2-andromeda-en"),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        
        # ============================================================
        # INTELLIGENT INTERRUPT HANDLER CONFIGURATION
        # ============================================================
        # LAYER 1: Block single-word fillers at VAD level
        # "yeah" = 1 word → BLOCKED → NO PAUSE
        min_interruption_words=2,
        
        # Minimum speech duration to register as interruption (filters coughs, etc.)
        min_interruption_duration=0.6,
        
        # CRITICAL: Disable the pause-resume behavior that causes 1-second hiccups
        # Setting to None means no waiting/pausing on potential false interruptions
        false_interruption_timeout=None,
        
        # Don't auto-resume after false interruption detection
        resume_false_interruption=False,
        # ============================================================
    )
    
    logger.info("✓ AgentSession configured with intelligent interrupt handling")

    # ============================================================
    # EVENT HANDLERS FOR LAYER 2 & 3: Semantic Filtering
    # ============================================================
    
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent):
        """Track agent state for context-aware interrupt decisions."""
        interrupt_controller.update_agent_state(ev.new_state)
        logger.debug(f"Agent state: {ev.old_state} → {ev.new_state}")
    
    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent):
        """
        Process user transcripts through the intelligent interrupt controller.
        
        LAYER 2: Semantic analysis of transcript content
        LAYER 3: Dispatch appropriate action based on decision
        
        Fix #5: Efficient interim processing - only check for interrupt commands
        in interim transcripts, skip full analysis for likely fillers.
        """
        transcript = ev.transcript.strip()
        if not transcript:
            return
        
        # Fix #5: OPTIMIZATION - Fast path for interim transcripts
        # Only process interim if it might be an interrupt command
        # Filler words can wait for final transcript (saves CPU)
        if not ev.is_final:
            # Quick lowercase + hyphen normalization for fast check
            quick_norm = transcript.lower().replace('-', ' ')
            
            # Fast check: Does it contain obvious interrupt words?
            interrupt_hints = {"stop", "wait", "no", "pause", "hold", "but", "actually", "what", "huh"}
            has_interrupt = any(word in quick_norm for word in interrupt_hints)
            
            if not has_interrupt:
                # Likely filler, skip interim processing entirely
                logger.debug(f"[SKIP] (interim, likely filler): '{transcript}'")
                return
        
        # Full decision for final transcripts OR interim with interrupt hints
        decision = interrupt_controller.decide(transcript, ev.is_final)
        
        # Dispatch action based on decision
        if decision == Decision.IGNORE:
            # Only clear on final transcripts to avoid redundant calls
            if ev.is_final:
                session.clear_user_turn()
                logger.info(f"[CLEARED] '{transcript}' (backchannel ignored)")
        elif decision == Decision.INTERRUPT:
            # Stop agent immediately - user wants the floor
            session.interrupt()
            session.clear_user_turn()
            if ev.is_final:
                logger.info(f"INTERRUPTED: '{transcript}' (command detected)")
        # Decision.NO_DECISION: Let framework handle normally (agent is silent)

    # ============================================================
    # METRICS AND USAGE LOGGING
    # ============================================================
    
    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Session ended. Usage: {summary}")

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