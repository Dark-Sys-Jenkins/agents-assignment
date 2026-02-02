import logging
import os
import re

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
from livekit.agents.voice.events import (
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)
from livekit.plugins import silero

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()

# ====================================
# CONTEXT-AWARE INTERRUPTION SETTINGS
# ====================================

# Words that should NOT interrupt agent speech or reach the LLM
IGNORE_WORDS = {
    "yeah", "yes", "ok", "okay", "hmm", "uh-huh", "uh huh",
    "mhm", "mm-hmm", "right", "sure", "yep", "yup", "aha",
    "mm", "mhmm", "alright", "got", "it"
}

# Words that should ALWAYS interrupt agent speech
INTERRUPT_WORDS = {
    "stop", "wait", "hold on", "hold up", "no", "cancel",
    "nevermind", "never mind", "actually", "but", "however",
    "pause", "hold"
}

def normalize_text(text: str) -> str:
    """Normalize text for comparison - lowercase and remove punctuation."""
    return re.sub(r'[^\w\s]', '', text.lower())

def is_only_ignore_words(text: str) -> bool:
    """Check if text contains ONLY passive acknowledgement words."""
    normalized = normalize_text(text)
    words = normalized.split()
    if not words:
        return False
    return all(word in IGNORE_WORDS for word in words)

def contains_interrupt_word(text: str) -> bool:
    """Check if text contains any active interrupt command."""
    normalized = normalize_text(text)
    words = normalized.split()
    return any(word in INTERRUPT_WORDS for word in words)

def get_llm_model():
    """Get LLM model based on environment variable."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "mistral":
        return "mistral/mistral-small"
    return "openai/gpt-4o-mini"

llm_model = get_llm_model()
logger.info(f"Using LLM: {llm_model}")


class MyAgent(Agent):
    # Class variable to track state when user speech was detected
    _agent_was_speaking_at_user_speech = False
    
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )
        self._is_speaking = False

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()

    async def on_user_turn_completed(self, turn_ctx, new_message):
        """
        CRITICAL: This is called BEFORE the LLM processes user input.
        With manual turn detection, we control when to commit user turns and generate replies.
        """
        user_text = new_message.text_content
        
        # Use the captured state from when user started speaking
        was_speaking = MyAgent._agent_was_speaking_at_user_speech
        
        # Check if agent was speaking and user said only passive words
        if was_speaking and is_only_ignore_words(user_text):
            logger.info(f"✓ IGNORING passive words during speech: '{user_text}'")
            # Don't call generate_reply - this prevents LLM from processing it
            return
        
        if contains_interrupt_word(user_text):
            logger.info(f"✗ INTERRUPT command detected: '{user_text}' - stopping agent")
            # Interrupt the agent's current speech
            await self.session.interrupt()
        elif was_speaking:
            logger.info(f"⚠️  Interrupting with: '{user_text}'")
            # Non-passive words during speech - interrupt
            await self.session.interrupt()
        else:
            logger.info(f"💬 Processing user input: '{user_text}'")
        
        # Let the default behavior handle it (generate reply)
        return await super().on_user_turn_completed(turn_ctx, new_message)

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """

        logger.info(f"Looking up weather for {location}")

        return "sunny with a temperature of 70 degrees."


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
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt="deepgram/nova-3",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # Configurable via LLM_PROVIDER environment variable (openai or mistral)
        llm=llm_model,
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2",
        # Manual turn detection - we control when turns complete to filter passive words
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection="manual",
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        # SMART INTERRUPTION: Allow listening during speech, but control interruption manually
        allow_interruptions=True,
        # Minimum words before triggering interruption (we handle filtering in event handlers)
        min_interruption_words=1,
    )

    # ====================================
    # CONTEXT-AWARE INTERRUPTION HANDLERS
    # ====================================
    
    # Get reference to the agent to update its state
    agent = MyAgent()
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(event: AgentStateChangedEvent):
        """Track when agent starts/stops speaking."""
        agent._is_speaking = (event.new_state == "speaking")
        if event.new_state == "speaking":
            logger.info("🎤 Agent started speaking")
        elif event.new_state == "listening":
            logger.info("🎧 Agent stopped speaking")
    
    @session.on("user_input_transcribed")
    def on_user_transcript(event: UserInputTranscribedEvent):
        """
        Capture agent state when user speaks and manually commit turns.
        With manual turn detection, we decide when to commit user input.
        """
        if event.is_final and event.transcript.strip():
            # Store whether agent was speaking when this transcript started
            MyAgent._agent_was_speaking_at_user_speech = agent._is_speaking
            logger.info(f"📝 Transcript: '{event.transcript}' (agent_was_speaking={agent._is_speaking})")
            
            # MANUAL TURN CONTROL: Decide whether to commit this as a user turn
            # Check if it's only passive words while agent is speaking
            if agent._is_speaking and is_only_ignore_words(event.transcript):
                logger.info(f"🛑 Skipping turn commit for passive words: '{event.transcript}'")
                # Do NOT commit - agent continues speaking
                return
            
            # Otherwise, commit the turn (this will trigger on_user_turn_completed)
            logger.info(f"✓ Committing user turn: '{event.transcript}'")
            session.commit_user_turn()

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
