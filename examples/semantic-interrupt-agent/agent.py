import logging
import asyncio
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    llm,
    AgentSession,
)
from livekit.plugins import openai, deepgram, silero, cartesia
from filter import SemanticFilter

load_dotenv()

logger = logging.getLogger("semantic-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    #  Initialize Plugins
    vad_plugin = silero.VAD.load()
    stt_plugin = deepgram.STT(model="nova-2-general")
    llm_plugin = openai.LLM(model="gpt-4o-mini")
    tts_plugin = cartesia.TTS(
        model="sonic-english", 
        voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
    )

    #  Logic Layer Init
    semantic_filter = SemanticFilter()
    
    ctx.is_agent_speaking = False

    session = AgentSession(
        vad=vad_plugin,
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin,
        chat_ctx=llm.ChatContext().append(
            role="system",
            text=(
                "Your name is Kelly. You are curious, friendly, and have a sense of humor. "
                "Keep responses concise. Do not use emojis."
            )
        )
    )

    @session.on("agent_speech_started")
    def on_agent_speech_started(ev):
        ctx.is_agent_speaking = True
        logger.info("🗣️ Agent STARTED speaking (State: SPEAKING)")

    @session.on("agent_speech_stopped")
    def on_agent_speech_stopped(ev):
        ctx.is_agent_speaking = False
        logger.info("🤫 Agent STOPPED speaking (State: LISTENING)")


    @session.on("user_speech_committed")
    def on_user_speech_committed(msg):
        user_text = msg.content
        
        # Check 1
        if not ctx.is_agent_speaking:
            return

        # Check 2
        if semantic_filter.should_ignore_input(user_text):
            logger.info(f"🔇 SEMANTIC GATE: Ignoring backchannel '{user_text}' - Audio continues.")
        else:
            logger.info(f"🛑 SEMANTIC GATE: Valid interruption '{user_text}' - Stopping audio.")
            asyncio.create_task(session.interrupt())

    #  Start the Agent
    await session.start(ctx.room)
    
    #  Simulation Sequence
    await session.say("Hello, I'm Kelly. I'm going to read a long story. Feel free to say 'yeah' while I talk.", allow_interruptions=True)
    
    long_text = (
        "The history of computing is fascinating. It started with mechanical gears in the 19th century. "
        "Charles Babbage designed the Difference Engine, which was arguably the first computer. "
        "Then came the vacuum tubes of the 1940s, which were huge and hot. "
        "Eventually, we moved to transistors, which changed everything."
    )
    await session.say(long_text)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))