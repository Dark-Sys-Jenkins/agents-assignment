import logging
import asyncio
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
# This import is GUARANTEED to work on v0.8.3
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero

load_dotenv()
logger = logging.getLogger("smart-agent")

IGNORE_WORDS = {"yeah", "ok", "hmm", "uh-huh", "right", "yep", "okay"}
INTERRUPT_WORDS = {"stop", "wait", "no", "cancel", "hold on"}

def prewarm_fnc(proc):
    proc.userdata.update({"vad": silero.VAD.load()})

async def entrypoint(ctx: JobContext):
    # Connect
    print(f"-> Connecting to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print("-> Connected! Waiting for user audio...")

    # Initialize the agent
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(),
    )

    # --- INTERRUPTION LOGIC ---
    @agent.on("user_speech_committed")
    def on_user_speech(msg):
        # 1. Get Text
        if hasattr(msg, "content"):
            user_text = msg.content
        else:
            user_text = str(msg)
        
        user_text = user_text.lower().strip()
        print(f"✅ User said: '{user_text}'")

        # 2. Check State (Is agent speaking?)
        is_speaking = False
        if agent.speech_handle and not agent.speech_handle.interrupted:
            is_speaking = True
            
        if is_speaking:
            # Logic A: Ignore filler
            if user_text in IGNORE_WORDS:
                print(f"   -> 🛡️ IGNORING backchannel (Agent continues)")
                return

            # Logic B: Stop on command
            if any(word in user_text for word in INTERRUPT_WORDS):
                print(f"   -> 🛑 INTERRUPTING (Command detected)")
                asyncio.create_task(agent.interrupt())
                return
            
            # Logic C: New Input
            print(f"   -> 🛑 INTERRUPTING (New input)")
            asyncio.create_task(agent.interrupt())

    agent.start(ctx.room)
    await agent.say("I am online and ready. I am running on the golden version.")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm_fnc, 
        ),
    )