"""
Intelligent Interruption Handling Agent Example

This example demonstrates the intelligent interruption handling feature that
distinguishes between backchanneling (passive acknowledgements like "yeah", "ok", "hmm")
and real interruptions when the agent is speaking.

Key behaviors:
1. When agent is SPEAKING and user says "yeah/ok/hmm" -> Agent continues speaking (IGNORE)
2. When agent is SPEAKING and user says "wait/stop/no" -> Agent stops (INTERRUPT)
3. When agent is SILENT and user says "yeah/ok" -> Agent responds (RESPOND)
4. Mixed input like "yeah wait a second" -> Agent stops (contains interrupt keyword)

Configuration options:
- intelligent_interruption_enabled: Enable/disable the feature (default: True)
- backchanneling_words: Custom set of words to ignore while speaking
- interrupt_keywords: Words that always trigger interruption
- max_backchanneling_words: Max words to consider as backchanneling (default: 3)
"""

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

logger = logging.getLogger("intelligent-interruption-agent")

load_dotenv()


class IntelligentInterruptionAgent(Agent):
    """
    An agent that demonstrates intelligent interruption handling.

    This agent will give long explanations when asked, making it easy to test
    the backchanneling behavior. Try saying "yeah", "ok", or "hmm" while the
    agent is speaking - it should continue without stopping.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions="""Your name is Alex. You are a helpful assistant that explains things in detail.

When explaining topics, you speak in complete paragraphs and don't stop mid-sentence.
If the user gives feedback like "yeah", "ok", "hmm", "uh-huh" while you're speaking,
you should understand they are just acknowledging they're listening and continue your explanation.

However, if they say "wait", "stop", "hold on", or ask a question, you should pause and address their input.

When asked to explain something, give a thorough explanation with multiple points.
This helps demonstrate the intelligent interruption handling feature.

Do not use emojis, asterisks, markdown, or special characters in your responses.
Keep your tone conversational and friendly.""",
        )

    async def on_enter(self):
        """Called when the agent joins the session."""
        self.session.generate_reply(
            "Hello! I'm Alex, your assistant with intelligent interruption handling. "
            "Try asking me to explain something, and while I'm talking, say 'yeah' or 'ok' - "
            "I'll keep going without stopping. But if you say 'wait' or 'stop', I'll pause. "
            "What would you like to learn about?"
        )

    @function_tool
    async def explain_topic(self, context: RunContext, topic: str):
        """Called when the user asks for an explanation of a topic.

        Args:
            topic: The topic to explain
        """
        logger.info(f"Explaining topic: {topic}")

        # Return a long explanation to give the user time to test backchanneling
        return f"""Let me explain {topic} in detail.

First, it's important to understand the fundamental concepts. {topic.capitalize()} is a fascinating
subject that has many different aspects to consider. The key principles involve understanding
both the theoretical foundations and the practical applications.

Moving on to the second point, we should consider how {topic} relates to real-world scenarios.
In practice, this knowledge is applied in various industries and fields. Understanding these
connections helps us see the bigger picture.

Third, there are some common misconceptions about {topic} that we should address. Many people
assume certain things that aren't quite accurate, so let me clarify those points for you.

Finally, let me share some practical tips for working with {topic}. These insights come from
extensive experience and can help you apply this knowledge effectively.

Would you like me to elaborate on any specific aspect?"""

    @function_tool
    async def tell_long_story(self, context: RunContext, story_type: str = "adventure"):
        """Called when the user asks for a story. Great for testing backchanneling.

        Args:
            story_type: The type of story to tell (adventure, mystery, comedy)
        """
        logger.info(f"Telling a {story_type} story")

        return f"""Let me tell you an {story_type} story.

Once upon a time, in a land far away, there was a curious explorer who set out on a journey.
The explorer traveled through dense forests, across wide rivers, and over tall mountains.
Along the way, they encountered many challenges that tested their courage and wisdom.

The explorer met interesting characters who shared valuable lessons about life and perseverance.
Each encounter brought new insights and strengthened the explorer's resolve to continue.
Through all the difficulties, the explorer never gave up hope.

After many days of travel, the explorer finally reached their destination. What they found
there exceeded all expectations and made the entire journey worthwhile. The experience
changed them forever and gave them stories to share for years to come.

And that's the story! Would you like to hear another one, or shall we discuss something else?"""


server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm function to load the VAD model."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent session."""
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Custom backchanneling words (optional - uses defaults if not specified)
    custom_backchanneling = frozenset([
        "yeah", "yea", "yep", "yes", "yup", "ya",
        "ok", "okay", "k",
        "hmm", "hm", "mm", "mmhmm", "mhm", "uh-huh", "uhuh",
        "right", "alright", "sure",
        "i see", "got it", "gotcha",
        "ah", "aha", "oh", "ooh",
        "nice", "cool", "great", "good", "fine",
        "uh", "um", "er", "like",
        # Add any custom words here
        "understood", "go on", "continue",
    ])

    # Custom interrupt keywords (optional - uses defaults if not specified)
    custom_interrupt_keywords = frozenset([
        "wait", "stop", "hold on", "hold", "pause", "no",
        "actually", "but", "however", "excuse me",
        "question", "what", "why", "how", "when", "where", "who",
        "can you", "could you", "would you",
        "i have", "i need", "i want",
        "let me", "hang on", "one second", "one moment",
        "sorry", "pardon",
        # Add any custom keywords here
        "repeat", "slow down",
    ])

    session = AgentSession(
        # Speech-to-text - required for intelligent interruption handling
        stt="deepgram/nova-3",
        # LLM for processing user input
        llm="openai/gpt-4.1-mini",
        # Text-to-speech
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Enable preemptive generation for lower latency
        preemptive_generation=True,
        # === INTELLIGENT INTERRUPTION HANDLING CONFIG ===
        # Enable the intelligent interruption filter
        intelligent_interruption_enabled=True,
        # Custom backchanneling words (optional)
        backchanneling_words=custom_backchanneling,
        # Custom interrupt keywords (optional)
        interrupt_keywords=custom_interrupt_keywords,
        # Max words to consider as backchanneling
        max_backchanneling_words=3,
        # These work alongside intelligent interruption:
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    # Log metrics
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    @session.on("user_input_transcribed")
    def _on_user_input(ev):
        """Log user input for debugging."""
        logger.info(f"User said: '{ev.transcript}' (final={ev.is_final})")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        """Log agent state changes for debugging."""
        logger.info(f"Agent state: {ev.old_state} -> {ev.new_state}")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=IntelligentInterruptionAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
