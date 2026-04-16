import logging
import os

from dotenv import load_dotenv

load_dotenv()

from livekit.agents import Agent, AgentSession, JobContext, RunContext, cli, AgentServer
from livekit.agents.voice.backchannel import DEFAULT_BACKCHANNEL_WORDS
from livekit.plugins import silero

HAS_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
HAS_GROQ = bool(os.getenv("GROQ_API_KEY"))
HAS_DEEPGRAM = bool(os.getenv("DEEPGRAM_API_KEY"))
HAS_CARTESIA = bool(os.getenv("CARTESIA_API_KEY"))

if HAS_DEEPGRAM:
    from livekit.plugins import deepgram
if HAS_OPENAI:
    from livekit.plugins import openai
if HAS_GROQ:
    from livekit.plugins import groq
if HAS_CARTESIA:
    from livekit.plugins import cartesia

logger = logging.getLogger("interrupt-agent")


def get_llm():
    if HAS_OPENAI:
        logger.info("LLM: Using OpenAI gpt-4o-mini")
        return openai.LLM(model="gpt-4o-mini")
    if HAS_GROQ:
        logger.info("LLM: Using Groq llama-3.3-70b-versatile")
        return groq.LLM(model="llama-3.3-70b-versatile")
    raise RuntimeError("No LLM key found. Set OPENAI_API_KEY or GROQ_API_KEY")


def get_stt():
    if HAS_DEEPGRAM:
        logger.info("STT: Using Deepgram nova-3")
        return deepgram.STT(model="nova-3")
    if HAS_OPENAI:
        logger.info("STT: Using OpenAI whisper-1")
        return openai.STT(model="whisper-1")
    if HAS_GROQ:
        logger.info("STT: Using Groq whisper-large-v3-turbo")
        return groq.STT(model="whisper-large-v3-turbo")
    raise RuntimeError("No STT key found. Set DEEPGRAM_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY")


def get_tts():
    if HAS_CARTESIA:
        logger.info("TTS: Using Cartesia")
        return cartesia.TTS()
    if HAS_OPENAI:
        logger.info("TTS: Using OpenAI alloy")
        return openai.TTS(voice="alloy")
    if HAS_GROQ:
        logger.info("TTS: Using Groq PlayAI")
        return groq.TTS(model="playai-tts", voice="Arista-PlayAI")
    raise RuntimeError("No TTS key found. Set CARTESIA_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY")


BACKCHANNEL_WORDS = DEFAULT_BACKCHANNEL_WORDS | frozenset(
    {
        "uh-huh",
        "mm-hmm",
        "gotcha",
        "yea",
        "ya",
        "huh",
    }
)


class InterruptAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. "
                "Keep your responses concise and conversational. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "When the user gives short acknowledgements like 'yeah' or 'ok' "
                "after being silent, treat them as valid responses and continue "
                "the conversation naturally."
            ),
        )

    async def on_enter(self):
        self.session.generate_reply(
            instructions="Greet the user and ask how you can help them today."
        )


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=get_stt(),
        llm=get_llm(),
        tts=get_tts(),
        vad=silero.VAD.load(),
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_interruption_words=0,
        backchannel_words=BACKCHANNEL_WORDS,
    )

    await session.start(agent=InterruptAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
