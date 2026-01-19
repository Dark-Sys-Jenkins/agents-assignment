import os
import logging
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

logger = logging.getLogger("test-interrupt-agent")
load_dotenv()

class TestInterruptAgent(Agent):
    def __init__(self) -> None:
        ignore_words_env = os.getenv("INTERRUPTION_IGNORE_WORDS")
        ignore_list = (
            [word.strip() for word in ignore_words_env.split(",") if word.strip()]
            if ignore_words_env
            else ["yeah", "ok", "uh-huh", "hmm", "okay", "fine", "right", "yep", "yup","hm-hm","hm","hmmm"]
        )
        super().__init__(
            instructions="You are a helpful assistant. You tell long stories when asked.",
            # KEY CHANGE: This is what we are testing
            interruption_ignore_list=ignore_list,
        )

    async def on_enter(self):
        print("DEBUG: Agent - on_enter triggered. Attempting to connect/say hello.")
        try:
            await self.say("Hello, I am your interruption testing agent. Ask me to tell you a story.")
            print("DEBUG: Agent - Successfully sent hello message.")
        except Exception as e:
            print(f"DEBUG: Agent - Error in on_enter: {e}")
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(self, location: str):
        return "sunny with a temperature of 70 degrees."

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session(agent_name="test-agent")
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=TestInterruptAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
