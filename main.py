"""
Production-Ready Voice Agent with Intelligent Interruption Handling

This is the main file to run. It integrates all components:
- Intelligent Interruption Handler
- LiveKit Agent Framework
- STT/TTS/LLM integration
"""

import logging
import os
from typing import Optional
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, openai, silero

from intelligent_interrupt_handler import IntelligentInterruptionHandler, InterruptionConfig
from livekit_interruption_integration import wrap_session_with_interruption_filter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MyVoiceAgent(Agent):
    """
    Voice Agent with intelligent interruption handling
    """
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful and friendly voice assistant. "
                "When explaining concepts, provide detailed information naturally. "
                "If you hear acknowledgments like 'yeah', 'ok', or 'hmm' while you're speaking, "
                "continue your explanation without stopping. "
                "Only stop if the user explicitly asks you to with words like 'wait', 'stop', or 'no'."
            )
        )
    
    async def on_enter(self):
        """Called when the agent enters the session"""
        logger.info("🤖 Agent entering session")
        await self.session.generate_reply(
            instructions="Greet the user warmly and introduce yourself as their helpful voice assistant."
        )


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the LiveKit agent worker
    """
    logger.info("🚀 Starting agent worker")
    
    # Connect to the room
    await ctx.connect()
    logger.info(f"✅ Connected to room: {ctx.room.name}")
    
    # Configure the interruption handler
    interrupt_config = InterruptionConfig(
        ignore_words={
            'yeah', 'ok', 'okay', 'hmm', 'mhmm', 'uh-huh', 
            'right', 'sure', 'got it', 'i see', 'alright',
            'uh', 'um', 'ah'
        },
        interrupt_words={
            'wait', 'stop', 'no', 'hold on', 'pause', 
            'hang on', 'excuse me'
        },
        confidence_threshold=0.6  # Lower threshold for faster response
    )
    
    # Create the interruption handler
    interrupt_handler = IntelligentInterruptionHandler(config=interrupt_config)
    logger.info(f"📋 Configured interruption handler")
    logger.info(f"   - Ignore words: {interrupt_config.ignore_words}")
    logger.info(f"   - Interrupt words: {interrupt_config.interrupt_words}")
    
    # Create the agent session
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
    )
    
    # Wrap the session with interruption filtering
    wrap_session_with_interruption_filter(session, interrupt_handler)
    logger.info("✅ Session wrapped with intelligent interruption handling")
    
    # Create the agent
    agent = MyVoiceAgent()
    
    # Start the session
    logger.info("▶️ Starting agent session...")
    await session.start(agent=agent, room=ctx.room)
    
    logger.info("✅ Agent session running successfully")


if __name__ == "__main__":
    """
    Run the agent using the LiveKit CLI
    
    Usage:
        # Development mode (with hot reload)
        python main_agent.py dev
        
        # Production mode
        python main_agent.py start
        
        # Console testing mode
        python main_agent.py console
    """
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))