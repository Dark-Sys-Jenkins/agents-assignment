import os
import logging
from dotenv import load_dotenv
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins import silero

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

print("ENV CHECK:")
print("LIVEKIT_URL =", os.getenv("LIVEKIT_URL"))
print("LIVEKIT_API_KEY =", os.getenv("LIVEKIT_API_KEY"))
print("LIVEKIT_API_SECRET =", os.getenv("LIVEKIT_API_SECRET"))

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
import asyncio

logger = logging.getLogger("intelligent-interruption-agent")
logger.setLevel(logging.INFO)



# Passive acknowledgment words - IGNORED when agent is speaking
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "right", "uhh", "uh", "uh-huh", "aha",
    "yep", "yup", "mhm",
}

# Active interruption commands - ALWAYS stop the agent
INTERRUPT_WORDS = {
    "stop", "wait", "no", "cancel", "hold", "pause", "hang on", "hold on"
}



def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, remove punctuation"""
    normalized = text.lower().strip()
    for char in [".", ",", "!", "?", ":", ";", "-", "'", '"']:
        normalized = normalized.replace(char, "")
    return normalized


def is_only_passive_acknowledgment(text: str) -> bool:
    """Check if input consists ONLY of passive acknowledgment words"""
    normalized = normalize_text(text)
    words = normalized.split()

    if len(words) == 0:
        return False

    return all(word in IGNORE_WORDS for word in words)


def contains_interrupt_command(text: str) -> bool:
    """Check if text contains any interrupt command words"""
    normalized = normalize_text(text)

    for phrase in INTERRUPT_WORDS:
        if " " in phrase and phrase in normalized:
            return True

    words = normalized.split()
    return any(word in INTERRUPT_WORDS for word in words)


def is_passive_prefix(text: str) -> bool:
    """
    Detect early partial transcript forms for passive words.
    This prevents early interruptions on partial STT like: "o", "ok", "h", "hm", "ri", etc.
    """
    normalized = normalize_text(text)

    if normalized == "":
        return False

    passive_prefixes = {
        "o", "ok", "oka", "okay",
        "h", "hm", "hmm",
        "r", "ri", "rig", "righ", "right",
        "y", "ye", "yea", "yeah",
        "m", "mh", "mhm",
        "u", "uh", "uhh"
    }

    return normalized in passive_prefixes


def should_interrupt(text: str, agent_was_speaking: bool) -> bool:
    """
    Core decision logic: Determine if the agent should be interrupted and input processed.

    Logic Matrix:
    - If agent was NOT speaking: ALWAYS respond
    - If agent WAS speaking:
      - Contains interrupt command: INTERRUPT and process
      - Only passive words: IGNORE
      - Anything else: INTERRUPT and process
    """
    if not agent_was_speaking:
        logger.info(f"✓ RESPOND: Agent was silent - will process '{text}'")
        return True

    if contains_interrupt_command(text):
        logger.info(f"🛑 INTERRUPT: Command detected in '{text}'")
        return True

    if is_only_passive_acknowledgment(text):
        logger.info(f"✓ IGNORE: Passive acknowledgment '{text}' - Agent continues")
        return False

    logger.info(f"🛑 INTERRUPT: Active input detected '{text}'")
    return True



class IntelligentAgent(Agent):
    """
    AI Agent with intelligent interruption handling.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise and natural. "
                "Do not use emojis, asterisks, markdown, or special characters in your speech. "
                "You are friendly, helpful, and speak naturally in English. "
                "When explaining complex topics, break them into digestible parts. "
                "If the user gives short acknowledgments like 'yeah', 'okay', or 'right', "
                "understand they are listening and continue your explanation naturally without stopping."
            ),
            allow_interruptions=True
        )

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str = "", longitude: str = ""
    ):
        """Get weather information for a location"""
        logger.info(f"Weather lookup requested for: {location}")
        return f"The weather in {location} is sunny with a temperature of 70 degrees Fahrenheit."



def prewarm(proc: JobProcess):
    """Preload models into process memory for faster session startup"""
    logger.info("Prewarming: Loading VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Prewarming complete")


server = AgentServer()
server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for each RTC session"""
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info(f"Starting new session in room: {ctx.room.name}")

    

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection="manual",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        discard_audio_if_uninterruptible=False
    )

    usage_collector = metrics.UsageCollector()

    agent_speaking_state = {"is_speaking": False}
    user_state = {"was_agent_speaking": False, "current_transcript": ""}

    

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        if ev.new_state == "speaking":
            agent_speaking_state["is_speaking"] = True
            logger.info("🗣️ Agent STARTED speaking")
        else:
            agent_speaking_state["is_speaking"] = False
            logger.info("🔇 Agent STOPPED speaking")

    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        if ev.new_state == "speaking":
            user_state["was_agent_speaking"] = agent_speaking_state["is_speaking"]
            user_state["current_transcript"] = ""
            logger.info(
                f"🎤 User started speaking | Agent was speaking: {user_state['was_agent_speaking']}"
            )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(transcript):
        user_state["current_transcript"] = transcript.transcript
        text = normalize_text(user_state["current_transcript"])

        logger.info(f"📝 Transcript received: '{text}' (final: {transcript.is_final})")

        
        if not transcript.is_final:
            if user_state["was_agent_speaking"] and is_passive_prefix(text):
                logger.info(f"✓ IGNORE PARTIAL PASSIVE: '{text}'")
                return

            if contains_interrupt_command(text) and user_state["was_agent_speaking"]:
                logger.info(f"🛑 Early INTERRUPT: Command detected in partial '{text}'")
                session.interrupt()
            return


        if user_state["was_agent_speaking"] and is_only_passive_acknowledgment(text):
            logger.info(f"✓ IGNORE FINAL PASSIVE: '{text}'")
            session.clear_user_turn()
            return

        if should_interrupt(text, user_state["was_agent_speaking"]):
            if user_state["was_agent_speaking"] and agent_speaking_state["is_speaking"]:
                logger.info(f"🛑 INTERRUPT: Stopping agent for '{text}'")
                session.interrupt()

            logger.info(f"✅ COMMIT: Processing final input '{text}'")
            session.commit_user_turn()
        else:
            logger.info(f"✓ CLEAR: Ignoring final input '{text}'")
            session.clear_user_turn()

    @session.on("metrics_collected")
    def on_metrics_collected(ev: MetricsCollectedEvent):
        """Collect and log usage metrics"""
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        """Log final usage statistics when session ends"""
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session ended. Usage summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    

    logger.info("🚀 Starting intelligent agent session...")
    logger.info("=" * 60)
    logger.info("BEHAVIOR:")
    logger.info("- Agent speaking + user says 'yeah/ok/hmm/right' → AGENT CONTINUES, input ignored")
    logger.info("- Agent speaking + user says 'stop/wait' → AGENT STOPS, processes input")
    logger.info("- Agent silent + user says anything → PROCESSES input")
    logger.info("=" * 60)

    agent = IntelligentAgent()

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )



if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("LiveKit Intelligent Interruption Agent")
    logger.info("=" * 60)
    logger.info(f"Ignore words: {IGNORE_WORDS}")
    logger.info(f"Interrupt words: {INTERRUPT_WORDS}")
    logger.info("=" * 60)

    cli.run_app(server)