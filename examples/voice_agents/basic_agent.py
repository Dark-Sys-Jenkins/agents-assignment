# import logging
# import asyncio

# from dotenv import load_dotenv

# from livekit.agents import (
#     Agent,
#     AgentServer,
#     AgentSession,
#     JobContext,
#     JobProcess,
#     MetricsCollectedEvent,
#     RunContext,
#     cli,
#     metrics,
#     room_io,
# )
# from livekit.agents.llm import function_tool
# from livekit.plugins import silero
# from livekit.plugins.turn_detector.multilingual import MultilingualModel

# # uncomment to enable Krisp background voice/noise cancellation
# # from livekit.plugins import noise_cancellation

# logger = logging.getLogger("basic-agent")

# load_dotenv()


# # These words should NOT interrupt the agent if spoken alone
# SOFT_INTERRUPT_WORDS = {
#     "yeah",
#     "yes",
#     "ok",
#     "okay",
#     "hmm",
#     "right",
#     "uh",
#     "uh huh",
#     "uh-huh",
#     "mm",
#     "mmm",
# }

# # If any of these appear, we *always* interrupt
# INTERRUPT_KEYWORDS = {
#     "wait",
#     "stop",
#     "pause",
#     "cancel",
#     "hold on",
#     "actually",
# }


# class MyAgent(Agent):
#     def __init__(self) -> None:
#         super().__init__(
#             instructions="Your name is Kelly. You would interact with users via voice."
#             "with that in mind keep your responses concise and to the point."
#             "do not use emojis, asterisks, markdown, or other special characters in your responses."
#             "You are curious and friendly, and have a sense of humor."
#             "you will speak english to the user",
#         )

#     async def on_enter(self):
#         # when the agent is added to the session, it'll generate a reply
#         # according to its instructions
#         self.session.generate_reply()

#     # all functions annotated with @function_tool will be passed to the LLM when this
#     # agent is active
#     @function_tool
#     async def lookup_weather(
#         self, context: RunContext, location: str, latitude: str, longitude: str
#     ):
#         """Called when the user asks for weather related information.
#         Ensure the user's location (city or region) is provided.
#         When given a location, please estimate the latitude and longitude of the location and
#         do not ask the user for them.

#         Args:
#             location: The location they are asking for
#             latitude: The latitude of the location, do not ask user for it
#             longitude: The longitude of the location, do not ask user for it
#         """

#         logger.info(f"Looking up weather for {location}")

#         return "sunny with a temperature of 70 degrees."


# server = AgentServer()


# def prewarm(proc: JobProcess):
#     proc.userdata["vad"] = silero.VAD.load()


# server.setup_fnc = prewarm


# @server.rtc_session()
# async def entrypoint(ctx: JobContext):
#     # each log entry will include these fields
#     ctx.log_context_fields = {
#         "room": ctx.room.name,
#     }
#     session = AgentSession(
#         # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
#         # See all available models at https://docs.livekit.io/agents/models/stt/
#         stt="deepgram/nova-3",
#         # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
#         # See all available models at https://docs.livekit.io/agents/models/llm/
#         llm="openai/gpt-4.1-mini",
#         # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
#         # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
#         tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
#         # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
#         # See more at https://docs.livekit.io/agents/build/turns
#         turn_detection=MultilingualModel(),
#         vad=ctx.proc.userdata["vad"],
#         # allow the LLM to generate a response while waiting for the end of turn
#         # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
#         preemptive_generation=True,
#         # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
#         # when it's detected, you may resume the agent's speech
#         resume_false_interruption=True,
#         false_interruption_timeout=1.0,
#     )
    
#     agent_speaking = False

#     # log metrics as they are emitted, and total usage after session is over
#     usage_collector = metrics.UsageCollector()

#     @session.on("metrics_collected")
#     def _on_metrics_collected(ev: MetricsCollectedEvent):
#         metrics.log_metrics(ev.metrics)
#         usage_collector.collect(ev.metrics)

#     async def log_usage():
#         summary = usage_collector.get_summary()
#         logger.info(f"Usage: {summary}")

#     # shutdown callbacks are triggered when the session is over
#     ctx.add_shutdown_callback(log_usage)
    
#     @session.on("agent_started_speaking")
#     def _on_agent_started():
#         nonlocal agent_speaking
#         agent_speaking = True
#         logger.debug("agent started speaking")

#     @session.on("agent_stopped_speaking")
#     def _on_agent_stopped():
#         nonlocal agent_speaking
#         agent_speaking = False
#         logger.debug("agent stopped speaking")


#     @session.on("user_transcript")
#     async def _on_user_transcript(ev):
#         """
#         This fires whenever STT produces text.

#         If the agent is currently talking, we inspect the transcript
#         before letting the interruption stand.
#         """

#         nonlocal agent_speaking

#         text = ev.text.lower().strip()

#         logger.info(f"user transcript while agent talking: {text}")

#         # If agent is silent, do nothing
#         if not agent_speaking:
#             return

#         # Light cleanup
#         cleaned = (
#             text.replace(".", "")
#             .replace(",", "")
#             .replace("?", "")
#         )

#         # Semantic override always wins
#         if any(keyword in cleaned for keyword in INTERRUPT_KEYWORDS):
#             logger.info("semantic interrupt detected")
#             return  # allow default stop behavior

#         words = cleaned.split()

#         # If it's only soft filler words, resume agent speech
#         if words and all(w in SOFT_INTERRUPT_WORDS for w in words):
#             logger.info("soft backchannel detected, resuming agent")

#             # Give LiveKit a moment to finish stopping audio
#             await asyncio.sleep(0.12)

#             session.resume()
#             return

#         # Otherwise: real interruption
#         logger.info("valid interruption; letting agent stop")


#     await session.start(
#         agent=MyAgent(),
#         room=ctx.room,
#         room_options=room_io.RoomOptions(
#             audio_input=room_io.AudioInputOptions(
#                 # uncomment to enable the Krisp BVC noise cancellation
#                 # noise_cancellation=noise_cancellation.BVC(),
#             ),
#         ),
#     )


# if __name__ == "__main__":
#     cli.run_app(server)


import logging
import asyncio

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")
load_dotenv()

# -------------------------------
# Agent definition
# -------------------------------

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and to the point. "
                "Do not use emojis, markdown, or special characters. "
                "You are curious, friendly, and speak English."
            )
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, location: str, latitude: str = "", longitude: str = ""
    ):
        """Look up the weather for a given location."""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

# -------------------------------
# Server setup
# -------------------------------

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

# -------------------------------
# RTC entrypoint
# -------------------------------

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    # Create session with intelligent interruption handling built-in
    # The agent_session.py you modified handles soft/hard words automatically
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        
        # IMPORTANT: These should match your agent_session.py defaults
        # The intelligent interruption system needs these specific values:
        # min_interruption_duration=0.0,          # Start STT immediately
        # min_interruption_words=1,               # Require 1 word from STT
        # allow_interruptions=True,
        # discard_audio_if_uninterruptible=True,
        # false_interruption_timeout=None,        # Disabled (we don't use pause/resume)
        # resume_false_interruption=False,        # Disabled (we prevent pauses)
        turn_detection = "manual",
        # ignore_filler_interruptions = True,
        
    )

    usage_collector = metrics.UsageCollector()

    # -------------------------------
    # Metrics
    # -------------------------------

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    # -------------------------------
    # OPTIONAL: Monitor interruption events for debugging
    # -------------------------------

    @session.on("user_input_transcribed")
    def _on_user_input(ev):
        """Monitor user transcripts for debugging."""
        if ev.is_final:
            logger.info(f"User said: {ev.transcript}")

    @session.on("agent_state_changed")
    def _on_agent_state(ev):
        """Monitor agent state changes."""
        logger.debug(f"Agent state: {ev.old_state} → {ev.new_state}")

    @session.on("user_state_changed")
    def _on_user_state(ev):
        """Monitor user state changes."""
        logger.debug(f"User state: {ev.old_state} → {ev.new_state}")

    # -------------------------------
    # Start session
    # -------------------------------

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

# -------------------------------
# CLI
# -------------------------------

if __name__ == "__main__":
    cli.run_app(server)