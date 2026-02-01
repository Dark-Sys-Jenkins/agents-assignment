import logging
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentServer, AgentSession, JobContext, JobProcess, cli
)
from livekit.plugins import silero, groq, deepgram
from logic import InterruptionHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intelligent-interruption")
load_dotenv()

class IntelligentAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are Kelly. Do not stop for 'yeah' or 'ok'. Only stop for commands or questions."
        )

    async def on_enter(self):
        # Long text to test interruptions
        self.session.say(
            "The Solar System consists of the Sun and the objects that orbit it. "
            "It formed approximately 4.6 billion years ago from the gravitational "
            "collapse of a giant interstellar molecular cloud. Jupiter is a gas "
            "giant and the largest planet in our system, containing more than "
            "twice the mass of all the other planets combined."
        )

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server = AgentServer()
server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    handler = InterruptionHandler()

    session = AgentSession(
        stt=deepgram.STT(),
        llm=groq.LLM(model="llama-3.3-70b-versatile"), 
        tts=deepgram.TTS(), 
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
        resume_false_interruption=False,
    )

    @session.on("user_input_transcribed")
    def on_user_input(ev):
        if not ev.transcript: return
        
        is_active = session.agent_state in ("speaking", "thinking")
        
        if is_active:
            if handler.should_interrupt(ev.transcript):
                if session.current_speech:
                    session.current_speech.allow_interruptions = True
                    session.current_speech.interrupt(force=True)
        else:
            logger.info(f"SILENT: User said '{ev.transcript}'")

    await session.start(agent=IntelligentAssistant(), room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)
