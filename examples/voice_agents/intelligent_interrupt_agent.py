"""
LiveKit Intelligent Interruption Handling Agent

This agent implements context-aware interruption handling that distinguishes between:
- Passive acknowledgements (yeah, ok, hmm) - IGNORED when agent is speaking
- Active interruptions (stop, wait, no) - ALWAYS processed
- Mixed inputs (yeah but wait) - Processed because they contain commands

The implementation works at the framework level by modifying how the agent handles
transcripts during speech. When the agent is speaking and detects a filler word,
it automatically resumes speaking instead of interrupting.

Configuration:
- IGNORE_WORDS env var: Comma-separated list of filler words to ignore
- INTERRUPT_WORDS env var: Comma-separated list of words that always interrupt
- Or customize programmatically using set_interruption_filter()
"""

import logging
import os

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
    AgentServer,
    # Intelligent Interruption Filter - exposed from framework
    InterruptionFilter,
    set_interruption_filter,
    DEFAULT_IGNORE_WORDS,
    DEFAULT_INTERRUPT_WORDS,
)
from livekit.agents.llm import function_tool
from livekit.agents.voice.events import UserInputTranscribedEvent
from livekit.plugins import silero, deepgram, openai

load_dotenv()

logger = logging.getLogger("intelligent-interrupt-agent")
logger.setLevel(logging.INFO)

# ============================================================================
# OPTIONAL: Customize the interruption filter
# ============================================================================
# You can customize the filter words here or via environment variables

# Example: Add custom words to the default sets
custom_ignore_words = DEFAULT_IGNORE_WORDS | {"absolutely", "totally", "definitely"}
custom_interrupt_words = DEFAULT_INTERRUPT_WORDS | {"help", "restart"}

# Set the custom filter (optional - framework uses defaults if not set)
set_interruption_filter(InterruptionFilter(
    ignore_words=custom_ignore_words,
    interrupt_words=custom_interrupt_words,
))


class IntelligentInterruptAgent(Agent):
    """
    Agent with intelligent interruption handling.
    
    The interruption filtering is handled at the framework level automatically.
    This agent just needs to enable the resume_false_interruption feature.
    """
    
    def __init__(self) -> None:
        super().__init__(
            instructions="""Your name is Aria. You are a helpful AI assistant.
            You interact with users via voice, so keep responses concise and natural.
            Do not use emojis, asterisks, markdown, or special characters.
            You are friendly, patient, and articulate.
            When explaining things, speak in complete sentences and paragraphs.
            If interrupted with a command like 'stop' or 'wait', acknowledge it.
            When users say things like 'yeah', 'ok', or 'hmm' while you're talking,
            those are just acknowledgements - you should continue speaking.""",
        )
    
    async def on_enter(self):
        """Called when agent joins the session."""
        await self.session.generate_reply()
    
    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str = "", longitude: str = ""
    ):
        """Get weather information for a location.
        
        Args:
            location: The city or region to get weather for
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
        """
        logger.info(f"Looking up weather for {location}")
        return f"The weather in {location} is sunny with a temperature of 72 degrees Fahrenheit."
    
    @function_tool
    async def tell_story(self, context: RunContext, topic: str = "history"):
        """Tell a detailed story about a topic. Use this to test interruption handling.
        
        Args:
            topic: The topic to tell a story about
        """
        stories = {
            "history": """Let me tell you about the fascinating history of computing. 
            In the early 1800s, Charles Babbage conceived the idea of a programmable computer. 
            His Analytical Engine, though never completed, contained many features of modern computers.
            Ada Lovelace, working with Babbage, wrote what is considered the first computer algorithm.
            Fast forward to the 1940s, and we see the first electronic computers being built.
            ENIAC, completed in 1945, was one of the first general-purpose electronic computers.
            It weighed about 30 tons and occupied about 1,800 square feet of space.
            The transistor, invented in 1947 at Bell Labs, revolutionized electronics.
            This led to smaller, faster, and more reliable computers in the decades that followed.
            The integrated circuit, developed in the late 1950s, further miniaturized computing.
            By the 1970s, personal computers began to emerge, making computing accessible to everyone.""",
            
            "space": """Space exploration is one of humanity's greatest achievements.
            In 1957, the Soviet Union launched Sputnik, the first artificial satellite.
            This sparked the space race between the US and Soviet Union.
            In 1961, Yuri Gagarin became the first human in space.
            Then in 1969, Neil Armstrong and Buzz Aldrin walked on the Moon.
            The Space Shuttle program ran from 1981 to 2011, launching 135 missions.
            Today, the International Space Station has been continuously occupied since 2000.
            Private companies like SpaceX are now leading the charge to Mars.
            We're living in an exciting time for space exploration.""",
            
            "default": """Let me share an interesting story with you.
            Once upon a time, in a world not too different from ours, 
            there lived curious minds who sought to understand everything around them.
            They built tools, developed languages, and created art.
            They looked up at the stars and wondered what lay beyond.
            This curiosity drove them to explore, discover, and invent.
            And that spirit of curiosity continues to drive us forward today."""
        }
        
        return stories.get(topic.lower(), stories["default"])
    
    @function_tool
    async def count_numbers(self, context: RunContext, start: int = 1, end: int = 20):
        """Count numbers slowly. Use this to test interruption handling with 'stop'.
        
        Args:
            start: Number to start counting from
            end: Number to count up to
        """
        numbers = ", ".join(str(i) for i in range(start, end + 1))
        return f"I'll count from {start} to {end} for you. Here we go: {numbers}."


# Create the server
server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm the VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent session."""
    
    ctx.log_context_fields = {"room": ctx.room.name}
    
    # Initialize models
    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )
    
    deepgram_stt = deepgram.STT()
    deepgram_tts = deepgram.TTS()
    
    # Create agent instance
    agent = IntelligentInterruptAgent()
    
    # Create session with intelligent interruption settings
    # The key settings are:
    # - allow_interruptions=True: Enable interruptions
    # - resume_false_interruption=True: Resume if interruption was just a filler
    # - false_interruption_timeout: Time to wait before resuming
    session = AgentSession(
        stt=deepgram_stt,
        llm=groq_llm,
        tts=deepgram_tts,
        vad=ctx.proc.userdata["vad"],
        # Interruption settings
        allow_interruptions=True,
        min_interruption_duration=0.3,  # Short threshold for quick "stop" commands
        min_interruption_words=0,  # Framework handles word filtering
        # FALSE INTERRUPTION HANDLING - KEY FOR FILLER WORDS
        resume_false_interruption=True,  # Resume after filler words
        false_interruption_timeout=1.0,  # Wait 1s then resume if no real input
        preemptive_generation=True,
    )
    
    # Optional: Log transcripts for debugging
    @session.on("user_input_transcribed")
    def on_transcript(ev: UserInputTranscribedEvent):
        if ev.is_final:
            logger.info(f"📝 Final transcript: '{ev.transcript}'")
    
    @session.on("agent_false_interruption")
    def on_false_interrupt(ev):
        logger.info(f"🔄 False interruption detected - resumed: {ev.resumed}")
    
    # Metrics logging
    usage_collector = metrics.UsageCollector()
    
    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage summary: {summary}")
    
    ctx.add_shutdown_callback(log_usage)
    
    # Start the session
    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
