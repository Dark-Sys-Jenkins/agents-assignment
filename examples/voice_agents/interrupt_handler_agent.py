import logging

from dotenv import load_dotenv

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import cartesia, deepgram, openai, silero

agent_is_talking = False

IGNORE_WORDS = ["yeah", "ok", "okay", "hmm"]
STOP_WORDS = ["stop", "wait", "no"]


logger = logging.getLogger("resume-agent")

from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[2] / ".env")



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
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
    )

    # 🔹 ADD YOUR CALLBACK HERE (RIGHT HERE)
    @session.on("user_transcription_final")
    def on_user_text(text: str):
        global agent_is_talking

        text = text.lower()
        logger.info(f"User said: {text}")

        if agent_is_talking:
            for word in STOP_WORDS:
                if word in text:
                    logger.info("Hard interrupt detected")
                    session.interrupt()
                    return

            logger.info("Soft acknowledgement ignored")
            return

        logger.info("Agent is silent, letting normal flow continue")

    # 🔹 DO NOT PUT CODE BELOW THIS LINE
    await session.start(
        agent=Agent(instructions="You are a helpful assistant."),
        room=ctx.room
    )

if __name__ == "__main__":
    cli.run_app(server)
