import logging

from dotenv import load_dotenv
from livekit import rtc

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
from livekit.plugins import groq
from livekit.plugins import deepgram

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()

IGNORE_WORDS = ["yeah", "okay", "ok", "hmm", "hmmm", "right", "uhuh", "uh-huh", "ahh", "ah", "aha", "mhmm"]

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
        pass

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
    # 1st change -> adding IGNORE_WORDS list
    session = AgentSession(
        stt = "deepgram/nova-3",
        llm = groq.LLM(model="llama-3.1-8b-instant"),
        tts = deepgram.TTS(
            model="aura-asteria-en"
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=False,
        # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
        # when it's detected, you may resume the agent's speech

        # 2nd change -> Disabling false interruption to implement own logic layer 
        resume_false_interruption=False,
        allow_interruptions=True,
        #false_interruption_timeout=2.0,
    )

    #3rd change -> Adding logic layer
    #Buffer to hold the agent's speech state
    validation_state = {"waiting_for_stt": False}

    @session.on("user_speech_committed")
    def _on_user_speech(ev: rtc.Transcription):
        is_agent_speaking = session.agent_output_playing
        transcript = ev.text.lower().strip().replace(".", "").replace(",", "")
        words = transcript.split()

        if validation_state["waiting_for_stt"]:
            is_only_ignore_words = all(word in IGNORE_WORDS for word in words)
            if is_only_ignore_words:
                logger.info(f"Ignoring false interruption from user: {transcript}")
                session.resume_speaking() 
            else:
                logger.info(f"Valid user interruption detected while agent was speaking : {transcript}")
                session.generate_reply()
            validation_state["waiting_for_stt"] = False
        else:
            logger.info(f"Processing valid input: '{transcript}' (Agent speaking: {is_agent_speaking})")
            session.generate_reply()

    
    # log metrics as they are emitted, and total usage after session is over
    @session.on("agent_response_generated")
    def _on_llm_response(ev):
        logger.info(f"LLM OUTPUT: {ev.text}")
        session.allow_interruptions = False
        validation_state["waiting_for_stt"] = True
    usage_collector = metrics.UsageCollector()

    @session.on("user_started_speaking")
    def _on_user_start():
        if session.agent_output_playing:
            logger.debug("User started speaking while agent was talking -> holding interruption until STT is done.")

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
