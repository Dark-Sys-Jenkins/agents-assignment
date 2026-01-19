"""
Intelligent Interruption Handling Example

This example demonstrates how the LiveKit Agent Framework handles intelligent interruption
based on user context and agent state. The agent can distinguish between passive
acknowledgements ("yeah", "ok", "hmm") and active interruptions ("stop", "wait").

The logic works as follows:
1. When the agent is SPEAKING:
   - If user says only filler words → IGNORED (agent continues)
   - If user says commands → INTERRUPTED immediately
   
2. When the agent is SILENT:
   - All user input is PROCESSED normally (including filler words)

This prevents the agent from stopping abruptly when users provide passive feedback.
"""

import logging
from typing import Optional

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("intelligent-interruption-agent")

load_dotenv()


class IntelligentInterruptionAgent(Agent):
    """
    An agent that implements intelligent interruption handling.
    
    The agent is configured with a list of "filler words" that should not interrupt
    the agent while it's speaking. These words are typically used for passive
    acknowledgement (e.g., "yeah", "ok", "hmm").
    """
    
    def __init__(self) -> None:
        # Configure the agent with custom ignore list for filler words
        super().__init__(
            instructions="""You are a helpful assistant named Alex. 
            
Your role is to:
1. Provide clear, concise explanations on topics the user asks about
2. Acknowledge user feedback appropriately
3. Continue speaking smoothly when users provide passive feedback like 'yeah' or 'ok'
4. Stop immediately if the user says commands like 'stop', 'wait', or 'hold on'

Keep your responses natural and conversational. When the user says 'yeah' or similar 
acknowledgements while you're speaking, simply continue without pausing.

When explaining concepts, be thorough but keep sentences concise for natural speech.""",
            # Configure the ignore list for passive acknowledgements
            word_ignore_list=[
                "yeah",      # Common affirmation
                "ok",        # Acknowledgement
                "okay",      # Variant of ok
                "hmm",       # Thinking sound
                "right",     # Agreement
                "uh-huh",    # Affirmation
                "uh",        # Filler
                "um",        # Filler
                "sure",      # Agreement
                "yep",       # Yes variant
                "yes",       # Affirmation (short)
                "uh-huh",    # Agreement sound
                "mm-hmm",    # Agreement sound
            ],
        )

    async def on_enter(self) -> None:
        """
        Called when the agent enters a session.
        Generate a greeting to start the conversation.
        """
        self.session.generate_reply()

    @function_tool
    async def get_information(
        self, context: RunContext, topic: str
    ) -> str:
        """
        Retrieves information about a specified topic.
        
        Args:
            topic: The topic to get information about
            
        Returns:
            Information about the requested topic
        """
        logger.info(f"User requested information about: {topic}")
        
        # This is a mock function. In a real scenario, you would query a database or API
        information_map = {
            "weather": "The current weather is sunny with a temperature of 72°F. "
                       "There's a light breeze from the west at 5 mph. "
                       "Humidity is at 65% and there's no chance of rain today.",
            "history": "History is the study of past events. "
                       "It helps us understand how civilizations developed, "
                       "how cultures evolved, and what lessons we can learn from previous generations. "
                       "Many historians argue that understanding history is crucial for making informed decisions today.",
            "science": "Science is a systematic way of understanding the natural world. "
                       "It uses observation, experimentation, and logical reasoning to discover laws and principles. "
                       "Science encompasses many fields including physics, chemistry, biology, and astronomy.",
            "technology": "Technology refers to tools and systems created by humans to solve problems "
                          "and improve daily life. From simple tools to computers and artificial intelligence, "
                          "technology has dramatically shaped human civilization and continues to evolve rapidly.",
        }
        
        return information_map.get(
            topic.lower(),
            f"I found some interesting information about {topic}. "
            "It's a fascinating subject with many applications and historical significance. "
            "Would you like me to go into more detail about any specific aspect?"
        )


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """
    Pre-warm the server by loading the VAD model.
    This is called before any agent sessions are created.
    """
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """
    Main entry point for the agent session.
    
    This function is called when a user connects to the agent.
    """
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Create the agent session with intelligent interruption handling enabled
    session = AgentSession(
        stt="deepgram/nova-3",  # Speech-to-Text model
        llm="openai/gpt-4o-mini",  # Language Model
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",  # Text-to-Speech
        turn_detection=MultilingualModel(),  # Turn detection for natural conversation
        vad=ctx.proc.userdata["vad"],  # Voice Activity Detection
        preemptive_generation=True,  # Generate response while user is still speaking
    )
    
    # Create and run the agent
    agent = IntelligentInterruptionAgent()
    await session.run(ctx, agent)


if __name__ == "__main__":
    cli.run(server)
