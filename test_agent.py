# test_agent.py
import re
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.plugins import deepgram, silero, openai
from livekit.agents.llm.tool_context import StopResponse

load_dotenv()

# ==============================
# CONFIGURABLE WORD LISTS
# ==============================

SOFT_ACKS = {
    "yeah",
    "yes",
    "ok",
    "okay",
    "hmm",
    "uh",
    "uhh",
    "uhhuh",
    "alright",
    "right",
    "oh",
}

HARD_COMMANDS = {
    "stop",
    "wait",
    "cancel",
    "pause",
    "no",
}

# ==============================
# TEXT NORMALIZATION (CRITICAL)
# ==============================

def normalize(text: str) -> list[str]:
    """
    Lowercase, remove punctuation, split into tokens.
    Fixes: 'Stop.' -> 'stop'
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()

def classify_user_text(text: str) -> str:
    """
    Returns:
    - 'interrupt' → hard stop command
    - 'ignore'    → passive acknowledgement
    - 'respond'   → valid user input
    """
    words = set(normalize(text))

    if words & HARD_COMMANDS:
        return "interrupt"

    if words and words.issubset(SOFT_ACKS):
        return "ignore"

    return "respond"

# ==============================
# AGENT IMPLEMENTATION
# ==============================

class IntelligentInterruptAgent(Agent):
    """
    Context-aware interruption handling agent.
    """

    async def on_user_turn_completed(self, chat_ctx, new_message):
        text = new_message.text_content.strip()
        decision = classify_user_text(text)

        print(f"[USER] '{text}' → {decision}")

        if decision == "interrupt":
            raise StopResponse()

        # PASSIVE ACK (ignore ONLY if speaking)
        if decision == "ignore":
            return

        # NORMAL INPUT
        await self.session.generate_reply()

# ==============================
# ENTRYPOINT
# ==============================

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    agent = IntelligentInterruptAgent(
        instructions=(
            "You are a helpful voice assistant. "
            "Ignore acknowledgements like yeah or hmm while speaking. "
            "Immediately stop if the user says stop, wait, or no."
        )
    )

    session = AgentSession(
        # 🔊 Audio pipeline
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),

        # CRITICAL SETTINGS
        allow_interruptions=True,
        resume_false_interruption=True,
        false_interruption_timeout=0.3,
        min_interruption_words=2
    )

    await session.start(room=ctx.room, agent=agent)

    # Initial prompt (agent is silent after this)
    await session.generate_reply(
        instructions=(
            "Explain machine learning"
        )
    )

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )
