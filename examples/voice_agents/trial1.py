import asyncio
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
)

from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
# uncomment to enable Krisp background voice/noise cancellation
from livekit.plugins import noise_cancellation
logger = logging.getLogger("basic-agent")

load_dotenv()

# These words should NOT interrupt the agent if spoken alone
SOFT_INTERRUPT_WORDS = {
    "yeah",
    "yes",
    "ok",
    "okay",
    "hmm",
    "right",
    "uh",
    "uh huh",
    "uh-huh",
    "mm",
    "mmm",
}

# If any of these appear, we *always* interrupt
INTERRUPT_KEYWORDS = {
    "wait",
    "stop",
    "pause",
    "cancel",
    "hold on",
    "actually",
}

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Romania. You interact with users via voice. "
                "Keep your responses concise and to the point. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "You are curious, friendly, and lightly humorous. "
                "You always speak English."
            )
        )

    async def on_enter(self):
         # when the agent is added to the session, it'll generate a reply
        # according to its instructions       
         self.session.generate_reply()

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    
server = AgentServer()

def prewarm(proc: JobProcess):
    # Load VAD once per worker process
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
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="openai/gpt-4.1-mini",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation

        # Keep latency low
        preemptive_generation=True,
        # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
        # when it's detected, you may resume the agent's speech

        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    agent_speaking = False

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


    @session.on("agent_started_speaking")
    def _on_agent_started():
        nonlocal agent_speaking
        agent_speaking = True
        logger.debug("agent started speaking")

    @session.on("agent_stopped_speaking")
    def _on_agent_stopped():
        nonlocal agent_speaking
        agent_speaking = False
        logger.debug("agent stopped speaking")


    @session.on("user_transcript")
    async def _on_user_transcript(ev):
        """
        This fires whenever STT produces text.

        If the agent is currently talking, we inspect the transcript
        before letting the interruption stand.
        """

        nonlocal agent_speaking

        text = ev.text.lower().strip()

        logger.info(f"user transcript while agent talking: {text}")

        # If agent is silent, do nothing
        if not agent_speaking:
            return

        # Light cleanup
        cleaned = (
            text.replace(".", "")
            .replace(",", "")
            .replace("?", "")
        )

        # Semantic override always wins
        if any(keyword in cleaned for keyword in INTERRUPT_KEYWORDS):
            logger.info("semantic interrupt detected")
            return  # allow default stop behavior

        words = cleaned.split()

        # If it's only soft filler words, resume agent speech
        if words and all(w in SOFT_INTERRUPT_WORDS for w in words):
            logger.info("soft backchannel detected, resuming agent")

            # Give LiveKit a moment to finish stopping audio
            await asyncio.sleep(0.12)

            session.resume()
            return

        # Otherwise: real interruption
        logger.info("valid interruption; letting agent stop")

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # uncomment to enable the Krisp BVC noise cancellation
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
