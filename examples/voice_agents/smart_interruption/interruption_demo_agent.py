"""
Smart Interruption Agent - Real-Time Demo

This agent showcases intelligent interruption handling that distinguishes between
passive affirmations and command words based on agent speaking state.

Run with: python interruption_demo_agent.py console
Connect via: https://agents-playground.livekit.io
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import azure, deepgram, groq, silero

# Import V2 patch - NO PAUSE, seamless continuation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_session_v2 import patch_agent_activity_v2

logger = logging.getLogger("interruption-demo")
logger.setLevel(logging.INFO)

load_dotenv()

server = AgentServer()

# Long introduction text for testing interruptions
INTRO_TEXT = (
    "Hello! I'm here to help you with anything you need. "
    "Let me tell you about the fascinating history of "
    "artificial intelligence. It all started back in 1950 when "
    "Alan Turing published his groundbreaking paper titled "
    "'Computing Machinery and Intelligence' where he proposed "
    "what we now call the Turing Test. This was a revolutionary "
    "idea at the time because it suggested that machines could "
    "potentially think. The term artificial intelligence itself "
    "was coined in 1956 at the Dartmouth Conference, organized by "
    "John McCarthy, Marvin Minsky, Nathaniel Rochester, and Claude "
    "Shannon. They were incredibly optimistic, predicting that "
    "machines as intelligent as humans would be developed within a "
    "generation. However, the field soon encountered what we call "
    "the first AI winter in the 1970s, when funding dried up "
    "because the early promises hadn't been met. The 1980s saw a "
    "resurgence with expert systems and knowledge-based approaches, "
    "but then another AI winter hit in the late 1980s and early "
    "1990s. The real breakthrough came in the 2010s with deep "
    "learning and neural networks. The key innovation was using "
    "multiple layers of artificial neurons that could learn "
    "hierarchical representations of data. This led to dramatic "
    "improvements in image recognition, speech recognition, and "
    "natural language processing. In 2012, a deep learning system "
    "called AlexNet won the ImageNet competition by a huge margin, "
    "demonstrating the power of convolutional neural networks. "
    "Since then, we've seen transformer architectures revolutionize "
    "natural language processing, with models like BERT, GPT, and "
    "now systems that can engage in conversations like this one. "
    "The applications are endless, from self-driving cars to medical "
    "diagnosis to creative writing. We're now able to generate "
    "realistic images, translate between languages in real-time, and "
    "even predict protein structures which is revolutionizing biology "
    "and medicine. It's truly an exciting time to be working in this "
    "field. What would you like to know more about?"
)


class InterruptionDemoAgent(Agent):
    """Demo agent that showcases smart interruption handling.

    Key behaviors:
    - Passive words (yeah, okay, uh-huh) while agent speaks → IGNORED
    - Command words (wait, stop, hold on) → INTERRUPT immediately
    - Regular speech while silent → PROCESSED normally
    """

    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful, conversational AI assistant. Have a natural "
                "back-and-forth dialogue with the user. Keep your responses "
                "concise (2-4 sentences) unless asked for detailed explanations. "
                "After providing information, ASK A FOLLOW-UP QUESTION to keep "
                "the conversation interactive. For example: 'Would you like to "
                "know more about that?', 'What aspect interests you most?', "
                "'Does that make sense?', or 'What would you like to explore next?' "
                "CRITICAL: If the user says 'stop', 'wait', 'hold on', or any "
                "interruption command, IMMEDIATELY stop speaking and listen to them. "
                "Do NOT continue or finish your sentence. Wait for them to speak "
                "and then respond directly to what they said. When the user gives "
                "passive feedback like 'yeah', 'okay', or 'uh-huh', treat it as "
                "encouragement to continue briefly, but still pause for questions. "
                "Be engaging, friendly, and give the user plenty of opportunities "
                "to participate in the conversation."
            ),
        )

    async def on_enter(self):
        """Called when agent enters the session"""
        logger.info("InterruptionDemoAgent entered")

        # Start with a brief, engaging introduction
        await self.session.say(
            "Hello! I'm your AI assistant. I can help you with questions, "
            "have conversations, or discuss any topic you're interested in. "
            "What would you like to talk about today?",
            allow_interruptions=True
        )


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent"""
    
    # Create session - NO pause/resume, seamless handling
    session = AgentSession(
        vad=silero.VAD.load(
            min_speech_duration=0.15,  # Faster detection for commands
            min_silence_duration=0.15,
        ),
        stt=deepgram.STT(
            model="nova-3",
            interim_results=True,  # Get interim results for faster detection
        ),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),  # Using Groq
        tts=azure.TTS(),  # Azure TTS (FREE - 500k chars/month)
        # Interruption settings - VERY LOW threshold for instant response
        min_interruption_words=0,  # Allow even single-word interruptions
        min_interruption_duration=0.05,  # Very low - instant response
        # DISABLE pause/resume - we handle this ourselves with NO PAUSE
        resume_false_interruption=False,
    )

    # Store handler reference
    handler_ref = None

    # Log events
    @session.on("user_started_speaking")
    def on_user_started_speaking(ev):
        logger.info("User started speaking")

    @session.on("agent_started_speaking")
    def on_agent_started_speaking(ev):
        if handler_ref:
            handler_ref.on_agent_speaking_started()
        logger.info("Agent started speaking")

    @session.on("agent_stopped_speaking")
    def on_agent_stopped_speaking(ev):
        if handler_ref:
            handler_ref.on_agent_speaking_stopped()
        logger.info("Agent stopped speaking")

    # Patch after session starts
    async def patch_after_start():
        nonlocal handler_ref
        await asyncio.sleep(0.5)
        if session._activity:
            logger.info(
                "Patching with V2 - NO PAUSE, seamless continuation"
            )
            handler_ref = patch_agent_activity_v2(session._activity)
        else:
            logger.warning("Could not patch - activity not found")
    
    asyncio.create_task(patch_after_start())
    
    await session.start(
        agent=InterruptionDemoAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
