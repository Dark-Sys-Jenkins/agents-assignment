"""
Voice Agent with Intelligent Interruption Handling

ZERO-PAUSE IMPLEMENTATION:
- Sets allow_interruptions=False to prevent VAD from auto-pausing
- Manually calls interrupt() ONLY for real command words
- Filler words are completely ignored - no pause at all

Run with: python examples/voice_agents/voice_agent_with_interruption.py console
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    UserInputTranscribedEvent,
    AgentStateChangedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero

from interrupt_handler import InterruptionHandler, InterruptionConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interruption-agent")

# Add a file handler to ensure we capture logs even if stdout redirection fails
file_handler = logging.FileHandler("agent_debug.log", mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Transcript logger - writes clean transcripts to file for demo review
transcript_logger = logging.getLogger("transcript")
transcript_handler = logging.FileHandler("conversation_transcript.txt", mode='w')
transcript_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
transcript_logger.addHandler(transcript_handler)
transcript_logger.setLevel(logging.INFO)
transcript_logger.propagate = False  # Don't propagate to root logger

load_dotenv()


class InterruptionAwareAgent(Agent):
    """
    Agent with intelligent interruption handling.
    
    Key behaviors:
    - Ignores backchanneling (yeah/ok/hmm) while speaking - NO PAUSE
    - Stops immediately on commands (wait/stop/no)
    - Responds to all input when silent
    """
    
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful, knowledgeable General AI Assistant. You can discuss ANY topic 
            including science, history, sports, pop culture, coding, and more.
            
            Key Behaviors:
            1. Answer questions directly and informatively using your broad knowledge.
            2. If the user asks for a story, explanation, or long response about ANYTHING, 
               provide a very detailed, multi-paragraph answer. 
            3. The user is testing an "Interruption System", so LONG continuous speech is helpful 
               to give them time to interrupt you.
            4. Do not mention that you are an AI or that you are testing, just act naturally.
            
            Keep your responses conversational and natural.
            Do not use emojis or special characters.
            Speak clearly and naturally.""",
            # Allow interruptions at agent level - session will handle the logic
        )
    
    async def on_enter(self):
        """Greet the user when session starts."""
        self.session.generate_reply(
            instructions="Greet the user and explain that you can demonstrate intelligent interruption handling. "
            "Tell them they can say 'yeah' or 'ok' while you speak and you won't stop, "
            "but if they say 'stop' or 'wait', you'll stop immediately."
        )
    

    
    @function_tool
    async def get_weather(self, context: RunContext, location: str):
        """Called when the user asks about the weather.
        
        Args:
            location: The city or region to get weather for
        """
        logger.info(f"Getting weather for {location}")
        return f"The weather in {location} is sunny and around 22 degrees Celsius. Perfect day to be outside!"


# Server setup
server = AgentServer()


def prewarm(proc: JobProcess):
    """Preload VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """
    Main entry point for the agent session.
    
    CRITICAL: This implementation sets allow_interruptions=False to prevent
    the VAD from automatically pausing the agent. We then manually call
    session.interrupt() ONLY when a real command word is detected.
    """
    
    # Add room info to log context
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Create the interruption handler with debug mode
    handler_config = InterruptionConfig(
        filler_words={
            'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'mhm', 'mm-hmm',
            'right', 'aha', 'sure', 'yep', 'yup', 'got it', 'uh', 'um',
            'yes', 'yea', 'ya', 'uh huh', 'mm', 'mhmm', 'uhuh'
        },
        interrupt_words={
            'wait', 'stop', 'no', 'hold', 'pause', 'hold on',
            'wait a second', 'hang on', 'one moment', 'actually',
            'wait wait', 'stop stop', 'hold on a second'
        },
        debug=True,  # Enable to see decision logs
    )
    handler = InterruptionHandler(handler_config)
    
    # ================================================================
    # CRITICAL: Create session with interruptions enabled but fast resume
    # This allows STT to work while agent speaks, but resumes almost instantly
    # ================================================================
    
    # ================================================================
    # Configure Deepgram STT and TTS via LiveKit (Uses your LiveKit credits)
    # ================================================================
    # OpenAI is NOT supported via LiveKit managed services
    # Supported providers: deepgram, assemblyai, elevenlabs, cartesia
    
    session = AgentSession(
        # LiveKit-managed Deepgram STT
        stt="deepgram/nova-3",
        # LiveKit-managed OpenAI LLM
        llm="openai/gpt-4o-mini",
        # LiveKit-managed Cartesia TTS
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD for voice activity detection
        vad=ctx.proc.userdata["vad"],
        
        # ================================================================
        # ZERO-PAUSE FIX: Set turn_detection to "manual"
        # This disables VAD-based automatic interruption/pausing
        # The agent will NEVER pause automatically on user speech
        # We manually call session.interrupt() only for command words
        # ================================================================
        turn_detection="manual",
        
        # Disable automatic interruptions - we handle them manually
        allow_interruptions=False,
        
        # Don't discard audio - we need to hear user input even when agent speaks
        discard_audio_if_uninterruptible=False,
        
        # These settings help with turn detection timing
        min_endpointing_delay=0.3,
        max_endpointing_delay=2.0,
        
        # Enable preemptive generation for smoother streaming and lower latency
        preemptive_generation=True,
    )
    
    logger.info(f"Using Deepgram STT (nova-3) and Cartesia TTS (sonic-2) via LiveKit")
    
    # ================================================================
    # Event Handlers for Intelligent Interruption
    # ================================================================
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        """Track when agent starts/stops speaking."""
        if ev.new_state == "speaking":
            handler.on_agent_speech_started()
            logger.info("[AGENT SPEAKING] Filler words will be ignored (zero pause)")
            transcript_logger.info("[AGENT SPEAKING]")
        elif ev.new_state in ("listening", "thinking", "idle"):
            if ev.old_state == "speaking":
                handler.on_agent_speech_ended()
                logger.info("[AGENT STOPPED] Now listening - all input will be processed")
                transcript_logger.info("[AGENT STOPPED]")
    
    @session.on("user_input_transcribed")
    def on_user_input(ev: UserInputTranscribedEvent):
        """
        Handle user transcripts with MANUAL interruption control.
        
        CRITICAL: Since allow_interruptions=False, the agent will NOT pause
        when VAD detects speech. We manually call session.interrupt() ONLY
        when we detect a real command word.
        
        For filler words: Do NOTHING - agent continues seamlessly
        For command words: Call session.interrupt() manually
        """
        transcript = ev.transcript.strip()
        
        if not transcript:
            return
        
        # Log what we received
        logger.info(f"[TRANSCRIPT] '{transcript}' (final={ev.is_final}) | Agent speaking: {handler.is_agent_speaking()}")
        
        # Log to transcript file
        if ev.is_final:
            transcript_logger.info(f"USER: {transcript}")
        
        # Make the decision (handler handles partial/final logic based on config)
        should_interrupt = handler.should_interrupt(transcript, is_final=ev.is_final)
        
        if handler.is_agent_speaking():
            if should_interrupt:
                # User said a command word - MANUALLY interrupt the agent
                logger.info(f"[INTERRUPT] User said '{transcript}' while agent speaking")
                transcript_logger.info(f"[USER INTERRUPTED WITH: {transcript}]")
                session.interrupt(force=True)  # force=True needed since allow_interruptions=False
            else:
                # Filler word - do NOTHING, agent continues seamlessly without any pause
                logger.info(f"[IGNORE] Filler '{transcript}' - agent continues (zero pause)")
                transcript_logger.info(f"[FILLER IGNORED: {transcript}]")
                # DO NOT call session.interrupt() or any other method
                # The agent will keep speaking without any pause
        else:
            # Agent is silent - commit the user turn to trigger a response
            logger.info(f"[PROCESSING] '{transcript}' (agent was silent)")
            # With turn_detection="manual", we must manually commit the turn
            session.commit_user_turn(transcript_timeout=1.0)
    
    # ================================================================
    # Metrics Logging
    # ================================================================
    
    usage_collector = metrics.UsageCollector()
    
    @session.on("metrics_collected")
    def on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
        
        # Print interruption handler stats
        handler.print_stats()
    
    ctx.add_shutdown_callback(log_usage)
    
    # ================================================================
    # Start the Session
    # ================================================================
    
    await session.start(
        agent=InterruptionAwareAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Uncomment if using Krisp noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
