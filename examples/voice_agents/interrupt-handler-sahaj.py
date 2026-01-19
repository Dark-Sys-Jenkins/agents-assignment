import logging
import asyncio
import re
import os

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

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger("basic-agent")

load_dotenv()

print("ASSEMBLYAI_API_KEY:", bool(os.getenv("ASSEMBLYAI_API_KEY")))
print("GOOGLE_API_KEY:", bool(os.getenv("GOOGLE_API_KEY")))
print("CARTESIA_API_KEY:", bool(os.getenv("CARTESIA_API_KEY")))


IGNORE_WORDS = {"yeah", "ok", "hmm", "uhh", "uh-huh", "right", "aha","okay"}
INTERRUPT_WORDS = {"stop", "wait", "no", "cancel", "hold"}

class AgentSpeechState:
    def __init__(self):
        self.is_speaking = False

speech_state = AgentSpeechState()


def normalize(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", "", text)
    return text.split()


def analyze_transcript(text: str, agent_is_speaking: bool):
    tokens = normalize(text)

    if not tokens:
        return "ignore"

    has_interrupt = any(t in INTERRUPT_WORDS for t in tokens)
    only_fillers = all(t in IGNORE_WORDS for t in tokens)

    if agent_is_speaking:
        if has_interrupt:
            return "interrupt"
        if only_fillers:
            return "ignore"
        return "interrupt"   # mixed content

    return "respond"

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
        stt="assemblyai/universal-streaming:en",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="google/gemini-3-flash",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
        # when it's detected, you may resume the agent's speech
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )
    
    
    @session.on("tts_started")
    def _on_tts_started():
        logger.info("Agent started speaking")
        speech_state.is_speaking = True


    @session.on("tts_finished")
    def _on_tts_finished():
        logger.info("Agent finished speaking")
        speech_state.is_speaking = False

    async def handle_transcript(text: str):
        # tiny delay so STT arrives before acting on VAD
        await asyncio.sleep(0.15)

        decision = analyze_transcript(text, speech_state.is_speaking)
        logger.info(f"Transcript='{text}' | speaking={speech_state.is_speaking} | decision={decision}")

        if speech_state.is_speaking:
            if decision == "ignore":
                # Do nothing - let agent continue speaking
                logger.info("Ignoring filler words while agent is speaking")
                return
            
            if decision == "interrupt":
                logger.info("Interrupting agent due to user command")
                await session.interrupt()
                await session.generate_reply(user_input=text)
                return
        
        # Agent is silent - always respond (both for "respond" decision and normal input)
        if decision == "respond" or not speech_state.is_speaking:
            await session.generate_reply(user_input=text)


    @session.on("transcript")
    def _on_transcript(ev):
        # Depending on SDK version this might be ev.text or ev.alternatives[0].text
        text = getattr(ev, "text", None)
        if not text:
            return

        asyncio.create_task(handle_transcript(text))

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
