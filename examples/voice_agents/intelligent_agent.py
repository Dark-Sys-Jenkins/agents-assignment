import logging
import re
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation


logger = logging.getLogger("basic-agent")

load_dotenv()

# Words that are considered "filler" if they appear in longer sentences
IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "right", "uh-huh", "yep", "got", "it", "aha"}

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt="deepgram/nova-3",
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="openai/gpt-4.1-mini",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
       
        # STRATEGY: We disable Auto-Interruption entirely.
        # The agent acts "deaf" to VAD noise until our code manually stops it.
        allow_interruptions=False,
    )

    @session.on("user_transcript")
    def on_transcript(transcript):
        # We only act on final, complete sentences
        if not transcript.final:
            return

        text = transcript.text.lower().strip()
        # Remove punctuation for cleaner counting
        clean_text = re.sub(r'[^\w\s]', '', text)
        words = clean_text.split()

        # --- LOGIC RULE 1: IGNORE SINGLE WORDS ---
        # If the user says 1 word ("Yeah", "Stop", "What"), we IGNORE it.
        if len(words) <= 1:
            logger.info(f"Ignored 1-word input: '{text}'")
            return

        # --- LOGIC RULE 2: CHECK FOR FILLERS ---
        # If it is 2+ words, we check if they are ALL in the ignore list.
        # Example: "Yeah okay" -> Ignored.
        # Example: "Stop now" -> 'stop' and 'now' are NOT fillers -> Interrupt.
        is_only_filler = all(word in IGNORE_WORDS for word in words)

        if is_only_filler:
            logger.info(f"Ignored filler phrase: '{text}'")
            return

        # EXECUTION
        # If we passed both rules, it is a valid multi-word command.
        logger.info(f"Valid Interruption (2+ words): '{text}'")
        session.interrupt()

    await session.start(agent=MyAgent(), room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)