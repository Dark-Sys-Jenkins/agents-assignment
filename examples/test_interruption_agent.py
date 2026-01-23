import logging
import asyncio
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    JobContext,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import deepgram, groq, cartesia, silero

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-agent")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful voice AI assistant. Keep your answers short, conversational, and punchy. If interrupted, stop immediately.",
            stt=deepgram.STT(),
            llm=groq.LLM(model="llama-3.3-70b-versatile"),
            tts=cartesia.TTS(),
            vad=silero.VAD.load(),
            allow_interruptions=True,
            min_endpointing_delay=0.5,
        )

    async def on_enter(self) -> None:
        logger.info("🤖 AGENT ENTERED PIPELINE")
        # Send initial greeting using the pipeline's say() method
        # This registers it as a trackable speech handle
        await self.say("Hello! I am online and running on the standard voice pipeline. We can have a real-time conversation now.")

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    logger.info(f"⚡ ENTRYPOINT CALLED | Room: {ctx.room.name} ⚡")
    await ctx.connect()
    
    # We don't need to pass components to session if the Agent has them
    session = AgentSession()

    logger.info("🚀 STARTING PIPELINE SESSION...")
    # This triggers the AgentActivity logic in the background
    await session.start(agent=Assistant(), room=ctx.room)

    # Note: We do NOT need a manual loop here. 
    # The 'Agent' class (via AgentActivity) automates STT -> LLM -> TTS.

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🟢 AGENT STARTED! DO NOT CLOSE THIS TERMINAL.")
    print("  👉 GO TO: https://agents-playground.livekit.io/")
    print("  👉 CONNECT TO: wss://liveskit-zw23ully.livekit.cloud")
    print("  👉 ROOM: test-room")
    print("  (Waiting for you...)\n" + "="*60 + "\n")
    cli.run_app(server)
