import logging
import re
import os
from dotenv import load_dotenv

from livekit.agents import (
    Agent, AgentServer, AgentSession,
    JobContext, JobProcess, cli, room_io
)
from livekit.plugins import openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel


from key_words import Soft_word,Hard_word

load_dotenv()


log = logging.getLogger("kelly-bot")


def clean_tokens(text):
    return [t for t in re.split(r"[^a-z]+", text.lower()) if t]



class KellyAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Your name is Kelly. Interact via voice. Be concise, friendly, curious, and funny. No emojis. Speak English."
        )

    async def on_enter(self):
        # Kick off the conversation
        self.session.generate_reply()


server = AgentServer()

def load_resources(proc: JobProcess):
    log.info("Loading VAD...")
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = load_resources

@server.rtc_session()
async def start_session(job: JobContext):
    log.info(f"Connecting to room: {job.room.name}")

    sess = AgentSession(
        stt="deepgram/nova-3", 
        llm="openai/gpt-4.1-nano",
        tts="inworld/inworld-tts-1",
        
        turn_detection=MultilingualModel(),
        vad=job.proc.userdata["vad"],
        
        preemptive_generation=True,
        resume_false_interruption=True,
        
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False, 
    )

    
    @sess.on("user_input_transcribed")
    def on_speech(ev):
        txt = (ev.transcript or "").strip()
        if not txt:
            return

        if ev.is_final:
            print(f">> USER SAID (final): {txt}")
        else:
            print(f">> USER SAID (interim): {txt}")

        words = clean_tokens(txt)
        is_soft = bool(words) and all(w in Soft_word for w in words)
        is_hard = any(w in Hard_word for w in words)
        
        # Check current state
        is_speaking = (sess.agent_state == "speaking")
        
        log.info(f"Analysis: '{txt}' | Talking: {is_speaking} | Soft: {is_soft}")

        # 1. If Agent is currently talking...
        if is_speaking:
            # Check for hard stop words ("stop", "wait", etc)
            if is_hard:
                log.info("Hard stop command detected. Stopping audio.")
                sess.interrupt(force=True)
                return
            
            # Check for passive backchannel ("yeah", "uh-huh")
            if is_soft:
                log.info("Passive acknowledgement. Ignoring.")
                return # Do nothing, let agent keep talking

            # If it's neither, it's a real interruption (e.g. "What is the time?")
            log.info("Valid interruption detected. Stopping audio.")
            sess.interrupt(force=True)
            return

        # 2. If Agent is silent
        # Normal behavior applies. The system will auto-generate a reply for the input.
        log.info("Agent silent. Processing input normally.")


    await sess.start(
        agent=KellyAgent(),
        room=job.room,
    )


if __name__ == "__main__":
    import os
    os.makedirs("LOGS", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler("LOGS/logs.txt", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    cli.run_app(server)