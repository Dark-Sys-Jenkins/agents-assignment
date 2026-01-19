#!/usr/bin/env python3
"""
Simple test agent to verify LiveKit setup is working
This agent will:
1. Connect to the LiveKit server
2. Listen for user input
3. Respond with OpenAI
"""

import logging
from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli, function_tool, RunContext

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger("test-agent")
logger.setLevel(logging.INFO)

# Create the agent server
server = AgentServer()


@function_tool
async def get_greeting(context: RunContext, name: str):
    """Greet someone by name"""
    return f"Hello, {name}! Nice to meet you!"


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point for the agent"""
    
    logger.info(f"[TEST] Agent session starting...")
    logger.info(f"[TEST] Connecting to room: {ctx.room.name}")
    
    # Connect to the room
    await ctx.connect()
    logger.info(f"[TEST] Successfully connected to room: {ctx.room.name}")
    
    # Import required modules
    from livekit.agents import Agent, AgentSession
    from livekit.plugins import openai, silero
    
    # Create a simple agent
    agent = Agent(
        instructions=(
            "You are a helpful test assistant. "
            "Your purpose is to verify that the LiveKit Agents framework is working correctly. "
            "Be friendly and concise in your responses. "
            "If the user asks what you are, explain that you are a test agent for the LiveKit platform."
        ),
        tools=[get_greeting],
    )
    
    # Create the agent session with Silero VAD (no API key needed)
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
    )
    
    logger.info("[TEST] Agent session created with:")
    logger.info("[TEST]   - STT: OpenAI Whisper")
    logger.info("[TEST]   - LLM: OpenAI GPT-4o-mini")
    logger.info("[TEST]   - TTS: OpenAI (alloy voice)")
    logger.info("[TEST]   - VAD: Silero (local)")
    
    # Start the session
    await session.start(agent=agent, room=ctx.room)
    logger.info("[TEST] Agent session started successfully!")
    
    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and ask them how you can help today. Keep it brief."
    )


if __name__ == "__main__":
    logger.info("[TEST] Starting LiveKit Test Agent...")
    logger.info("[TEST] This will connect to your LiveKit server")
    logger.info("[TEST] and listen for user connections")
    logger.info("[TEST]")
    logger.info("[TEST] To test:")
    logger.info("[TEST] 1. Run this script")
    logger.info("[TEST] 2. Join the room from https://agents-playground.livekit.io")
    logger.info("[TEST] 3. Or use any WebRTC client to connect to the room")
    logger.info("[TEST]")
    
    cli.run_app(server)
