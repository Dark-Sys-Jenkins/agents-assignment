import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentServer, AgentSession, JobContext, JobProcess,
    cli, room_io,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()
logger = logging.getLogger("interrupt-agent")
logger.setLevel(logging.INFO)

def get_env_list(key, default):
    val = os.getenv(key)
    if val:
        return set(val.lower().split(','))
    return default

# Words that indicate a definite command to stop
INTERRUPT_WORDS = get_env_list("INTERRUPT_WORDS", {
    "stop", "wait", "no", "cancel", "pause", "hold on", "shut up", "hey"
})

class KellyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. Be concise, friendly, and efficient.",
        )

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-2",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        allow_interruptions=True,
        resume_false_interruption=True,
        
    )

    state = {
        "is_speaking": False
    }
    
    _original_interrupt = session.interrupt

    async def smart_interrupt():
        """
        STRICT NO-DELAY LOGIC:
        If the agent is speaking, we IGNORE the VAD signal completely.
        We return immediately without stopping audio or waiting.
        """
        if not state["is_speaking"]:
            # If agent is silent, standard interruption logic applies (e.g., user answers)
            await _original_interrupt()
            return

        # If agent IS speaking, we do NOTHING. 
        # The audio continues seamlessly. We rely on 'on_transcription' to stop us.
        logger.info("🎤 VAD detected while speaking -> BYPASSING (No Stop/No Delay)")

    # Override the interrupt handler
    session.interrupt = smart_interrupt

    @session.on("conversation_item_added")
    def on_conv_item(event):
        """Track speaking state."""
        if hasattr(event, 'item'):
            if event.item.role == 'assistant':
                state["is_speaking"] = True
            elif event.item.role == 'user':
                state["is_speaking"] = False

    @session.on("transcription")
    def on_transcription(text: str):
        """
        The Master Logic Layer.
        """
        clean_text = text.lower().strip(".,!?;:\"()")
        if not clean_text:
            return

        words = clean_text.split()
        
        # Check if ANY word is in the interrupt list
        is_hard_stop = any(w in INTERRUPT_WORDS for w in words)
        
        logger.info(f"📝 Text: '{clean_text}' | Speaking: {state['is_speaking']} | Stop Command: {is_hard_stop}")

        # --- SCENARIO 1: AGENT IS SPEAKING ---
        if state["is_speaking"]:
            if is_hard_stop:
                # User said "Stop" (or "Wait", "Cancel")
                # NOW we interrupt retroactively.
                logger.info("🛑 INTERRUPT WORD DETECTED. Stopping now.")
                asyncio.create_task(_original_interrupt())
                asyncio.create_task(session.generate_reply(user_input=text))
            else:
                # User said "Yeah", "Okay", "Banana", "Random Noise".
                # IGNORE IT. Do not stop. Do not respond.
                logger.info(f"🔇 Ignoring '{clean_text}' (Not a stop command)")
                return

        # --- SCENARIO 2: AGENT IS SILENT ---
        else:
            # Normal conversation. Respond to everything.
            asyncio.create_task(session.generate_reply(user_input=text))

    await session.start(
        agent=KellyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions()
    )

if __name__ == "__main__":
    cli.run_app(server)