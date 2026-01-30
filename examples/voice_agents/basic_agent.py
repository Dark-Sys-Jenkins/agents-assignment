import logging
import os
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
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero, deepgram, openai

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Hema... You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )
        self.is_agent_speaking = False

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        await self.session.generate_reply()

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

    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )
    
    deepgram_stt = deepgram.STT()
    deepgram_tts = deepgram.TTS()

    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram_stt,
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=groq_llm,
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=deepgram_tts,
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



# context-aware logic for passive acknowledgement and active interupting


    ignore_words = {"yeah", "ok", "okay", "hmm", "aha", "uh-huh", "right", "sure", "yep"}  
    
    agent_instance = MyAgent()

    @session.on("agent_speech_started")
    def on_agent_speech_started(ev):
        agent_instance.is_agent_speaking = True
        logger.info("Agent started speaking")

    @session.on("agent_speech_stopped")
    def on_agent_speech_stopped(ev):
        agent_instance.is_agent_speaking = False
        logger.info("Agent stopped speaking")

    original_generate = session.generate_reply
    
    async def _safe_generate_logic(*args, **kwargs): 
        user_text = kwargs.get('user_input')
        
        if not user_text:
            try:
                chat_ctx = getattr(session, '_chat_ctx', None)
                if chat_ctx and hasattr(chat_ctx, 'messages'):
                    messages = chat_ctx.messages
                    if messages:
                        last_msg = messages[-1]
                        if last_msg.role == "user":
                            content = last_msg.content
                            if isinstance(content, str):
                                user_text = content
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, str):
                                        user_text = item
                                        break
            except Exception:
                pass

        if user_text:
            clean = user_text.lower().strip().replace('.', '').replace('!', '')
            
            if clean in ignore_words:
                if agent_instance.is_agent_speaking:
                    logger.info(f"ignoring fillers '{clean}' bcoz agent is speaking.")
                    return
                else:
                    logger.info(f"responsing to '{clean}' bcoz agent is silent.")
        
        await original_generate(*args, **kwargs)

    def filtered_generate_reply(*args, **kwargs):
        return asyncio.create_task(_safe_generate_logic(*args, **kwargs))

    session.generate_reply = filtered_generate_reply

    await session.start( #keeping same for start...
        agent=agent_instance,
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