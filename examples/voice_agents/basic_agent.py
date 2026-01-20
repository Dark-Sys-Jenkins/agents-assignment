import logging
import asyncio
from typing import Optional

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
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")

load_dotenv()


# ============================================================================
# INTERRUPTION HANDLER - Core Logic for Intelligent Filtering
# ============================================================================
class InterruptionHandler:
    """
    Handles intelligent interruption filtering based on agent speaking state.
    
    Logic Matrix:
    - Agent speaking + filler word (yeah, ok) → IGNORE (agent continues)
    - Agent speaking + command (stop, wait) → INTERRUPT (agent stops)
    - Agent silent + any input → PROCESS (agent responds)
    
    Author: Yash Mishra
    """
    
    def __init__(self):
        # Configurable list of filler words/phrases to ignore when agent is speaking
        self.ignore_phrases = {
            "yeah", "ok", "okay", "hmm", "uh-huh", 
            "right", "aha", "mhm", "sure", "yep",
            "got it", "i see", "alright", "uh huh",
            "mm-hmm", "yeah yeah"
        }
        
        # Track agent's current speaking state
        self.agent_is_speaking = False
        
        # Keywords that should ALWAYS interrupt the agent
        self.interrupt_keywords = {
            "stop", "wait", "no", "hold", "pause", 
            "hold on", "wait a second", "stop that",
            "hang on", "one second"
        }
        
        logger.info(f"🎯 InterruptionHandler initialized")
        logger.info(f"📝 Ignore phrases: {self.ignore_phrases}")
        logger.info(f"⚠️ Interrupt keywords: {self.interrupt_keywords}")
    
    def set_agent_speaking(self, is_speaking: bool):
        """
        Update the agent's speaking state.
        
        Args:
            is_speaking: True if agent is currently speaking, False otherwise
        """
        self.agent_is_speaking = is_speaking
        state = "SPEAKING" if is_speaking else "SILENT"
        logger.debug(f"🔊 Agent state changed: {state}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for matching.
        Removes punctuation, extra whitespace, and converts to lowercase.
        
        Args:
            text: Raw transcribed text
            
        Returns:
            Cleaned text string
        """
        import re
        # Convert to lowercase and strip whitespace
        cleaned = text.lower().strip()
        # Remove common punctuation (but preserve spaces between words)
        cleaned = re.sub(r'[!?.,:;"\']', '', cleaned)
        # Normalize multiple spaces to single space
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    
    def should_ignore_interruption(self, transcribed_text: str) -> bool:
        """
        Determine if user input should be ignored based on content and agent state.
        
        Args:
            transcribed_text: The transcribed user speech
            
        Returns:
            True if should ignore (agent continues), False if should process (agent stops)
        """
        if not transcribed_text:
            return True
        
        # Clean the text (remove punctuation, normalize)
        text_lower = self._clean_text(transcribed_text)
        
        if not text_lower:  # After cleaning, might be empty
            return True
        
        # RULE 1: If agent is NOT speaking, NEVER ignore user input
        # The user deserves a response when agent is silent
        if not self.agent_is_speaking:
            logger.debug(f"✅ Agent silent → Processing: '{text_lower}'")
            return False
        
        # RULE 2: Check for explicit interrupt keywords
        # These should ALWAYS stop the agent, even if mixed with filler
        for keyword in self.interrupt_keywords:
            if keyword in text_lower:
                logger.info(f"🛑 Interrupt keyword '{keyword}' detected → Stopping agent")
                return False
        
        # RULE 3: Check if it's ONLY filler words (no real content)
        words = text_lower.split()
        
        # Single word case: "yeah", "ok", etc.
        if len(words) == 1 and words[0] in self.ignore_phrases:
            logger.info(f"🙉 Ignoring filler word while speaking: '{text_lower}'")
            return True
        
        # Multi-word case: Check if ALL words are fillers
        # e.g., "yeah yeah" or "ok sure" → ignore
        # e.g., "yeah wait" or "ok but" → don't ignore
        all_filler = all(word in self.ignore_phrases for word in words)
        
        if all_filler:
            logger.info(f"🙉 Ignoring all-filler phrase while speaking: '{text_lower}'")
            return True
        
        # RULE 4: Mixed input - has real content
        # e.g., "yeah but wait" → contains "wait" (not in ignore list)
        logger.info(f"💬 Processing real/mixed input: '{text_lower}'")
        return False

# ============================================================================
# CUSTOM AGENT CLASS
# ============================================================================
class MyAgent(Agent):
    """Custom agent with interruption handler integration."""
    
    def __init__(self, interruption_handler: InterruptionHandler) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
            "With that in mind keep your responses concise and to the point. "
            "Do not use emojis, asterisks, markdown, or other special characters in your responses. "
            "You are curious and friendly, and have a sense of humor. "
            "You will speak English to the user.",
        )
        self.interruption_handler = interruption_handler

    async def on_enter(self):
        """Called when agent enters the session."""
        logger.info("👋 Agent Kelly entering session")
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """
        Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """
        logger.info(f"🌤️ Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."


# ============================================================================
# SERVER SETUP
# ============================================================================
server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm function to load VAD model before session starts."""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("🔥 VAD model prewarmed")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the agent session.
    Sets up the agent with intelligent interruption handling.
    """
    
    # Set up logging context
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    logger.info(f"🚀 Starting session in room: {ctx.room.name}")
    
    # Initialize the interruption handler
    interruption_handler = InterruptionHandler()
    
    # Create agent session with optimized settings
    session = AgentSession(
        # Speech-to-text (STT) - converts user speech to text
        stt="deepgram/nova-3",
        
        # Large Language Model (LLM) - agent's brain
        llm="openai/gpt-4.1-mini",
        
        # Text-to-speech (TTS) - agent's voice
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        
        # Turn detection and VAD
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # Allow LLM to start generating while waiting for user to finish
        preemptive_generation=True,
        
        # CRITICAL: Disable automatic false interruption resume
        # We handle this manually with our custom logic
        resume_false_interruption=False,
        
        # Reduced timeout for faster response (150ms instead of 1000ms)
        false_interruption_timeout=0.15,
    )
    
    # ========================================================================
    # EVENT HANDLERS - Track agent speaking state
    # ========================================================================
    
    @session.on("agent_speech_started")
    def on_agent_started_speaking(agent):
        """
        Called when agent starts speaking (TTS begins).
        Update handler state to prevent filler word interruptions.
        """
        logger.info("🗣️ Agent started speaking")
        interruption_handler.set_agent_speaking(True)
    
    @session.on("agent_speech_stopped")
    def on_agent_stopped_speaking(agent):
        """
        Called when agent stops speaking (TTS ends).
        Update handler state to allow normal user responses.
        """
        logger.info("🔇 Agent stopped speaking")
        interruption_handler.set_agent_speaking(False)
    
    @session.on("user_speech_committed")
    async def on_user_speech(event):
        """
        Called when user speech is transcribed and committed.
        
        This is the critical interception point where we:
        1. Get the transcribed text
        2. Check if it should be ignored (based on agent state + content)
        3. Either process or discard the interruption
        
        Args:
            event: Contains the transcribed user speech
        """
        # Extract transcribed text from event
        transcribed_text = event.text if hasattr(event, 'text') else str(event)
        logger.info(f"👤 User said: '{transcribed_text}'")
        
        # Apply intelligent filtering logic
        should_ignore = interruption_handler.should_ignore_interruption(transcribed_text)
        
        if should_ignore:
            logger.info("✋ IGNORING - Agent continues speaking seamlessly")
            # By returning early, we prevent the framework from processing
            # this as an interruption. The agent's audio stream continues.
            return
        else:
            logger.info("⚠️ PROCESSING - Valid interruption, agent will stop")
            # The framework handles stopping the agent automatically
            # when this function completes without returning early
    
    # ========================================================================
    # METRICS COLLECTION
    # ========================================================================
    
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        """Collect and log metrics for monitoring."""
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        """Log final usage summary when session ends."""
        summary = usage_collector.get_summary()
        logger.info(f"📊 Final Usage Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # ========================================================================
    # START SESSION
    # ========================================================================
    
    await session.start(
        agent=MyAgent(interruption_handler),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Uncomment to enable Krisp background voice/noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )
    
    logger.info("✅ Session started successfully")


if __name__ == "__main__":
    cli.run_app(server)