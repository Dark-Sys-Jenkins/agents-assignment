"""
LiveKit Agent with Intelligent Interruption Handling

This agent implements context-aware interruption filtering to distinguish between
passive backchanneling (e.g., "yeah", "ok") and active interruptions (e.g., "wait", "stop").

The agent continues speaking seamlessly when users provide encouragement, but stops
immediately when they issue commands or provide substantive input.
"""

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
from livekit.plugins import groq, silero, deepgram
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Add current directory to path for salescode_interrupt_handler import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from salescode_interrupt_handler.controller2 import Decision, InterruptionController

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("intelligent-agent")

load_dotenv()


class MyAgent(Agent):
    """Friendly voice agent with intelligent interruption handling."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep your responses concise and to the point. "
                "Do not use emojis, asterisks, markdown, or other special characters in your responses. "
                "You are curious and friendly, and have a sense of humor. "
                "You speak English to the user."
            ),
        )

    async def on_enter(self):
        """Called when the agent is added to the session."""
        # Generate initial greeting according to instructions
        self.session.generate_reply()

    # All functions annotated with @function_tool will be passed to the LLM
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


# Create the agent server
server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm function to load VAD model before session starts."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """
    Main entry point for LiveKit agent sessions.
    
    Sets up the agent with intelligent interruption handling that:
    1. Ignores backchanneling ("yeah", "ok") when agent is speaking
    2. Responds to commands ("stop", "wait") immediately
    3. Processes normal input when agent is silent
    """
    # Set log context for better debugging
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # ============================================================
    # INTELLIGENT INTERRUPT CONTROLLER INITIALIZATION
    # ============================================================
    interrupt_controller = InterruptionController()
    logger.info("✓ InterruptionController initialized")
    logger.info(f"✓ Stats: {interrupt_controller.get_stats()}")
    
    # ============================================================
    # AGENT SESSION CONFIGURATION
    # ============================================================
    session = AgentSession(
        # Speech-to-text (STT) - converts user's speech to text
        stt="deepgram/nova-3",
        
        # Large Language Model (LLM) - generates responses
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        
        # Text-to-speech (TTS) - converts text to speech
        tts=deepgram.TTS(model="aura-2-andromeda-en"),
        
        # Voice Activity Detection and turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # Allow LLM to generate response while waiting for end of turn
        preemptive_generation=True,
        
        # ============================================================
        # LAYER 1: VAD-LEVEL FILTERING
        # ============================================================
        # Block single-word interruptions at VAD level
        # "yeah" (1 word) → blocked at VAD, never reaches STT
        # "wait stop" (2 words) → passes through to STT for semantic analysis
        min_interruption_words=2,
        
        # Minimum speech duration to register as interruption (filters coughs, clicks)
        min_interruption_duration=0.6,
        
        # CRITICAL: Disable pause-resume behavior
        # Setting to None prevents the agent from pausing on potential false interruptions
        # This avoids the 1-second hiccup problem
        false_interruption_timeout=None,
        
        # Don't auto-resume after false interruption detection
        resume_false_interruption=False,
    )
    
    logger.info("✓ AgentSession configured with intelligent interrupt handling")

    # ============================================================
    # EVENT HANDLERS: LAYERS 2 & 3
    # ============================================================
    
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent):
        """
        LAYER 2: Track agent state for context-aware decisions.
        
        States: 'listening', 'thinking', 'speaking', etc.
        The controller needs to know when the agent is speaking to apply
        different filtering rules.
        """
        interrupt_controller.update_agent_state(ev.new_state)
        logger.debug(f"[STATE] {ev.old_state} → {ev.new_state}")
    
    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent):
        """
        LAYER 3: Semantic analysis and action dispatch.
        
        This is the core of the intelligent interruption system:
        1. Get transcript from STT
        2. Ask controller to make a decision based on:
           - Transcript content (what did user say?)
           - Agent state (is agent speaking or silent?)
           - Transcript finality (interim or final?)
        3. Execute appropriate action:
           - IGNORE: Clear the turn, don't interrupt agent
           - INTERRUPT: Stop agent immediately, process input
           - NO_DECISION: Let framework handle normally (agent is silent)
        
        CRITICAL FIX: Process ALL transcripts immediately, don't skip interims.
        The original bug was skipping interim fillers, which caused them to
        never be cleared, allowing the default VAD behavior to interrupt the agent.
        """
        transcript = ev.transcript.strip()
        
        # Skip empty transcripts
        if not transcript:
            return
        
        # ============================================================
        # DECISION MAKING
        # ============================================================
        # Ask the controller what to do with this transcript
        decision = interrupt_controller.decide(transcript, ev.is_final)
        
        # ============================================================
        # ACTION DISPATCH
        # ============================================================
        if decision == Decision.IGNORE:
            # This is backchanneling while agent is speaking
            # Clear it immediately to prevent interruption
            # CRITICAL: Clear on BOTH interim and final to prevent any hiccups
            session.clear_user_turn()
            
            if ev.is_final:
                logger.info(f"[CLEARED] '{transcript}' (backchannel ignored)")
            else:
                logger.debug(f"[CLEARED-INTERIM] '{transcript}' (backchannel ignored)")
        
        elif decision == Decision.INTERRUPT:
            # User wants to interrupt - stop agent immediately
            session.interrupt()
            session.clear_user_turn()
            
            if ev.is_final:
                logger.info(f"[INTERRUPTED] '{transcript}' (command/real input detected)")
            else:
                logger.debug(f"[INTERRUPTED-INTERIM] '{transcript}' (command detected)")
        
        elif decision == Decision.NO_DECISION:
            # Agent is silent, this is normal user input
            # Let the framework handle it normally (don't clear, don't interrupt)
            if ev.is_final:
                logger.info(f"[PROCESSING] '{transcript}' (normal input, agent silent)")
            else:
                logger.debug(f"[PROCESSING-INTERIM] '{transcript}' (normal input)")
        
        else:
            # Should never happen, but log if it does
            logger.error(f"[ERROR] Unknown decision type: {decision}")

    # ============================================================
    # METRICS AND USAGE LOGGING
    # ============================================================
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        """Log metrics as they are emitted."""
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        """Log total usage when session ends."""
        summary = usage_collector.get_summary()
        logger.info(f"Session ended. Usage: {summary}")
        
        # Log controller stats
        stats = interrupt_controller.get_stats()
        logger.info(f"Controller stats: {stats}")

    # Register shutdown callback
    ctx.add_shutdown_callback(log_usage)

    # ============================================================
    # START THE SESSION
    # ============================================================
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
    
    logger.info("✓ Session started successfully")


if __name__ == "__main__":
    cli.run_app(server)