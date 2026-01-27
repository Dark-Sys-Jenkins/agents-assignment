import logging
import re
import asyncio

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
    StopResponse,
    UserInputTranscribedEvent,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()

# Configurable Ignore List - Soft inputs
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "right", "uh-huh", "uh huh", "mhm", "yep", "yup", "nice", "cool", "great"
}

# Command words for interruption
STOP_WORDS = {
    "stop", "wait", "hold", "pause", "cancel", "stop talking", "shut up"
}

def normalize_text(text: str) -> str:
    # remove punctuation and lower case
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def is_soft_input(text: str) -> bool:
    cleaned = normalize_text(text)
    words = cleaned.split()
    return all(w in IGNORE_WORDS for w in words)

def contains_command(text: str) -> bool:
    cleaned = normalize_text(text)
    return any(cmd in cleaned for cmd in STOP_WORDS)

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Professor Orion. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point and also descriptive about your response."
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

        return f"The weather in {location} is sunny with a temperature of 70 degrees."


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

    # Internal state for this session
    state = {
        "is_agent_speaking": False,
        "block_next_generation": False,
    }

    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt="deepgram/nova-3",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="openai/gpt-4.1-mini",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        #tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        tts="deepgram/aura-2",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        
        # KEY CHANGE: Decrease sensitivity of auto-interrupt to prevent "false starts" on soft words
        # We handle interruptions manually based on semantics
        allow_interruptions=True,
        min_interruption_words=99,  # Effectively disable VAD-based interruption
        min_interruption_duration=10.0,
        
        # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
        # when it's detected, you may resume the agent's speech
        resume_false_interruption=False,
    )

    # Track speaking state
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        if ev.new_state == "speaking":
            state["is_agent_speaking"] = True
        else:
            state["is_agent_speaking"] = False

    # Handle semantic interruptions
    @session.on("user_input_transcribed")
    def _on_user_transcribed(ev: UserInputTranscribedEvent):
        text = ev.transcript
        is_final = ev.is_final
        
        if not text:
            return

        logger.info(f"User transcript: {text} (Final: {is_final})")

        # 1. Check for Command Words -> Hard Interrupt
        if contains_command(text):
            logger.info("Command detected - Interrupting")
            session.interrupt()
            state["block_next_generation"] = False # Proceed to generate response to command (e.g. silence or ack if needed, but usually we just interrupt and let turn complete)
            return

        # 2. Check for Soft Inputs -> Ignore if agent is speaking
        if state["is_agent_speaking"] and is_final:
            if is_soft_input(text):
                logger.info("Soft input detected while speaking - Ignoring")
                state["block_next_generation"] = True
                return

    @session.on("user_turn_completed")
    def _on_user_turn_completed(ev=None):
        # If we decided to block generation (soft input), suppress the response
        if state["block_next_generation"]:
            state["block_next_generation"] = False
            logger.info("Blocking response generation for soft input")
            raise StopResponse()

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
