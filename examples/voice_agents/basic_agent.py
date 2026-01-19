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
    StopResponse,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("basic-agent")
logging.basicConfig(level=logging.INFO)

load_dotenv()

# -------------------------------
# Interruption configuration
# -------------------------------

IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "right", "aha"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "pause", "hold"
}


# -------------------------------
# Agent Definition
# -------------------------------

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and natural. "
                "Do not use emojis, markdown, or special characters. "
                "You are friendly, curious, and professional. "
                "You speak English."
            ),
            allow_interruptions=False,
        )
        self.is_speaking = False

    async def on_enter(self):
        # Track agent speaking state using official LiveKit event
        self.session.on("agent_state_changed", self._on_agent_state_changed)

        # Initial greeting
        await self.session.generate_reply()

    def _on_agent_state_changed(self, event):
        state = getattr(event, "new_state", None)
        self.is_speaking = (state == "speaking")
        logger.debug(f"Agent state changed → {state}")

    async def on_user_turn_completed(self, turn_ctx, new_message):
        text = (new_message.text_content or "").lower().strip()
        if not text:
            return
        
        tokens = set(text.split())

        # 1. Flexible Detection
        # is_soft_ack: user said ONLY words in the ignore list
        is_soft_ack = tokens.issubset(IGNORE_WORDS)
        
        # has_interrupt: user said AT LEAST ONE word in the interrupt list
        # This fixes sentences like "Yeah but wait" or "Stop now"
        has_interrupt = not tokens.isdisjoint(INTERRUPT_WORDS)

        logger.info(
            f"User said: '{text}' | speaking={self.is_speaking} "
            f"| soft_ack={is_soft_ack} | interrupt={has_interrupt}"
        )

        # 2. State-Aware Actions
        if self.is_speaking:
            if has_interrupt:
                # MANDATORY: Manually stop the current audio playback
                logger.info("Hard interruption -> Manually stopping agent audio")
                self.session.interrupt() 
                
                # Prevent the agent from starting a new reply to the "Stop" command
                raise StopResponse()

            if is_soft_ack:
                # SEAMLESS: Raising StopResponse here is the ONLY way to prevent 
                # the "Thinking" pause while keeping the current audio playing.
                logger.info("Soft ack during speech -> Ignoring to maintain seamless flow")
                raise StopResponse()

        # 3. Silent Case (Scenario 3 of Assignment)
        # If the agent is silent, we 'return' so it responds to "Yeah" as a valid answer.
        return

    # Example tool
    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather information."""
        logger.info(f"Looking up weather for {location}")
        return "It is sunny with a temperature of 70 degrees."


# -------------------------------
# Agent Server Setup
# -------------------------------

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],

        # Performance & stability
        preemptive_generation=False,
        resume_false_interruption=False,
        # false_interruption_timeout=1.0,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)