"""
Intelligent Interruption Handling Agent

This agent demonstrates the intelligent backchanneling filter feature that
distinguishes between passive acknowledgements ("yeah", "ok", "hmm") and
active interruptions ("wait", "stop", "no").

Key Features:
- Agent continues speaking when user says backchanneling words
- Agent stops immediately when user says interrupt commands
- Same words are treated as valid input when agent is silent

The filtering is done at the framework level in AgentSession, so the
agent just needs to enable filter_backchanneling=True (default).
"""

import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("interruption-agent")
load_dotenv()


class IntelligentInterruptionAgent(Agent):
    """
    A voice agent with intelligent interruption handling.
    
    The agent will:
    - Continue speaking when user says "yeah", "ok", "hmm", etc.
    - Stop immediately when user says "wait", "stop", "no", etc.
    - Respond to short answers when agent is silent
    """
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant that provides detailed explanations. "
                "When asked about a topic, give a thorough response. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "Speak clearly and at a moderate pace."
            ),
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_enter(self):
        """Greet the user when the session starts."""
        self.session.generate_reply(
            instructions="Greet the user and ask what they would like to learn about today."
        )

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str = "", longitude: str = ""
    ):
        """Look up the weather for a given location."""
        self.logger.info(f"Weather lookup for {location}")
        return "It's sunny and 72 degrees Fahrenheit with clear skies."

    @function_tool
    async def explain_topic(self, context: RunContext, topic: str):
        """
        Explain a topic in detail. This is useful for testing interruption handling
        as the explanation will be long enough for the user to potentially interrupt.
        """
        self.logger.info(f"Explaining topic: {topic}")
        explanations = {
            "history": (
                "History is the study of past events, particularly human affairs. "
                "It encompasses the analysis of written records, artifacts, and other "
                "sources to understand how societies evolved over time. Historians use "
                "various methods including archaeology, linguistics, and anthropology "
                "to piece together narratives of the past. The field covers everything "
                "from ancient civilizations like Egypt and Mesopotamia to modern events. "
                "Understanding history helps us learn from past mistakes and appreciate "
                "how current institutions and cultures developed."
            ),
            "science": (
                "Science is a systematic enterprise that builds and organizes knowledge "
                "in the form of testable explanations and predictions about the universe. "
                "The scientific method involves observation, hypothesis formation, "
                "experimentation, and analysis. Major branches include physics, chemistry, "
                "biology, and earth sciences. Science has led to incredible technological "
                "advances from electricity to medicine to space exploration. It continues "
                "to push the boundaries of human understanding and capability."
            ),
        }
        return explanations.get(topic.lower(), f"I can provide a detailed explanation about {topic}.")


# Create the agent server
server = AgentServer()


def prewarm(proc: JobProcess):
    """Preload the VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """
    Main entry point for the agent session.
    
    This sets up the AgentSession with intelligent backchanneling filtering.
    The filter_backchanneling option (enabled by default) will:
    - Ignore "yeah", "ok", "hmm" etc. when agent is speaking
    - Allow interruption for "wait", "stop", "no" etc.
    - Process all input normally when agent is silent
    """
    ctx.log_context_fields = {"room": ctx.room.name}
    
    # Create session with backchanneling filter enabled (default)
    # You can customize the word lists if needed:
    #   backchanneling_words={"yeah", "ok", "custom_word"},
    #   interrupt_words={"wait", "stop", "custom_interrupt"},
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Backchanneling filter is enabled by default
        filter_backchanneling=True,
        # Optional: customize word lists via environment variables
        # BACKCHANNELING_WORDS="yeah,ok,hmm,custom"
        # INTERRUPT_WORDS="wait,stop,no,custom"
    )
    
    # Log state changes for debugging
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        logger.debug(
            f"Agent state changed: {ev.old_state} -> {ev.new_state}"
        )
    
    # Log user transcripts for debugging
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev):
        agent_state = session.agent_state
        logger.info(
            f"User transcript (agent_state={agent_state}): '{ev.transcript}' "
            f"(is_final={ev.is_final})"
        )
    
    # Log false interruption events
    @session.on("agent_false_interruption")
    def on_agent_false_interruption(ev):
        logger.debug(f"False interruption detected, resumed={ev.resumed}")
    
    await session.start(
        agent=IntelligentInterruptionAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
