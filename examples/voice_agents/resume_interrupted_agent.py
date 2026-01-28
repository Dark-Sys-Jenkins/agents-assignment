import logging

from dotenv import load_dotenv

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import cartesia, deepgram, openai, silero

logger = logging.getLogger("resume-agent")
logging.basicConfig(level=logging.INFO)

load_dotenv()
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "uh huh", "right", "mm"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "cancel", "hold", "pause"
}

# This example shows how to resume an agent from a false interruption.
# If `resume_false_interruption` is True, the agent will first pause the audio output
# while not interrupting the speech before the `false_interruption_timeout` expires.
# If there is not new user input after the pause, the agent will resume the output for the same speech.
# If there is new user input, the agent will interrupt the speech immediately.

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=openai.LLM(model="gpt-4o-mini"),
        stt=deepgram.STT(),
        tts=cartesia.TTS(),
        false_interruption_timeout=None,
        resume_false_interruption=False,
    )
    session.agent_is_speaking = False
    session.pending_interrupt = False

    @session.on("tts_started")
    def on_tts_started():
        session.agent_is_speaking = True

    @session.on("tts_finished")
    def on_tts_finished():
        session.agent_is_speaking = False

    @session.on("user_speech_detected")
    def on_user_speech_detected():
        if session.agent_is_speaking:
            session.pending_interrupt = True
            return

    @session.on("user_transcript")
    def on_user_transcript(transcript: str):
        if not transcript:
            return

        text = transcript.lower().strip()
        tokens = set(text.split())

        if not session.agent_is_speaking:
            return

        if not session.pending_interrupt:
            return

        if tokens & INTERRUPT_WORDS:
            session.interrupt()
            session.pending_interrupt = False
            return

        if tokens and tokens.issubset(IGNORE_WORDS):
            session.pending_interrupt = False
            return

        session.pending_interrupt = False

    await session.start(agent=Agent(instructions="You are a helpful assistant."), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
