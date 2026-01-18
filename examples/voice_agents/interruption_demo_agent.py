import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.agents.llm import ChatContext, ChatMessage, StopResponse
from livekit.agents.voice.interruption_filter import (
    load_default_backchannel_words,
    load_default_hard_interrupt_words,
)
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins import groq as groq_plugin

logger = logging.getLogger("interrupt-demo")


def _normalize_word_list(items):
    if not items:
        return []
    out = []
    for w in items:
        w = str(w).strip().lower()
        if w:
            out.append(w)
    return out


def load_word_config(config_path: str):
    """
    Loads backchannel + hard-interrupt words from JSON.
    Falls back to repo defaults if missing/bad.

    Supported JSON keys:
      - backchannel_words: [...]
      - hard_interrupt_words: [...]
      - command_words: [...]  (alias for hard interrupts)
    """
    backchannel = set(_normalize_word_list(load_default_backchannel_words()))
    hard_interrupt = set(_normalize_word_list(load_default_hard_interrupt_words()))

    try:
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            bc = _normalize_word_list(data.get("backchannel_words", []))
            hi = _normalize_word_list(data.get("hard_interrupt_words", []))
            cmd = _normalize_word_list(data.get("command_words", []))  # alias

            if bc:
                backchannel = set(bc)
            # allow either key; union if both present
            if hi or cmd:
                hard_interrupt = set(hi).union(set(cmd))

            logger.info(
                "Loaded %d backchannel words and %d hard-interrupt words from %s",
                len(backchannel),
                len(hard_interrupt),
                config_path,
            )
        else:
            logger.warning("Config not found at %s; using defaults.", config_path)
    except Exception as e:
        logger.warning("Failed to load %s (%s); using defaults.", config_path, e)

    return sorted(backchannel), sorted(hard_interrupt)


def _contains_hard_interrupt(msg: str, hard_words: set[str]) -> bool:
    """
    Match whole words for single-word commands; substring match for multi-word phrases.
    """
    for w in hard_words:
        if " " in w:
            if w in msg:
                return True
        else:
            if re.search(rf"\b{re.escape(w)}\b", msg):
                return True
    return False


def _is_pure_backchannel(msg: str, backchannel_words: set[str]) -> bool:
    """
    Treat as "pure backchannel" if message is ONLY a short backchannel phrase
    (e.g., 'yeah', 'ok', 'mmhmm'), optionally with punctuation.
    """
    cleaned = re.sub(r"[^a-zA-Z\s'-]", " ", msg.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned in backchannel_words


class InterruptDemoAgent(Agent):
    def __init__(self, backchannel_words: list[str], hard_interrupt_words: list[str]):
        super().__init__(
            instructions=(
                "You are a helpful, friendly voice assistant. "
                "Keep replies natural and spoken. "
                "If the user says stop/wait/pause/hold, acknowledge briefly and then listen for the next request."
            )
        )
        self._backchannel = set(backchannel_words)
        self._hard = set(hard_interrupt_words)

    async def on_enter(self) -> None:
        # ✅ FIX: use session.say (NOT session.output.say)
        await self.session.say(
            "Hi! I’m live. While I’m speaking, try saying 'yeah' or 'ok' — I should NOT stop. "
            "Say 'stop' to interrupt me immediately."
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """
        Called right before the LLM auto-responds.
        We can cancel auto-response by raising StopResponse().
        """
        text = (new_message.text_content or "").strip()
        if not text:
            # No transcript → don't let LLM respond
            raise StopResponse()

        normalized = re.sub(r"\s+", " ", text.lower()).strip()

        # If the user only says a backchannel (and agent isn't being interrupted mid-speech),
        # don't waste an LLM call / don't speak.
        if _is_pure_backchannel(normalized, self._backchannel):
            raise StopResponse()

        # If user says "stop/wait/hold/pause..." as a standalone turn,
        # acknowledge briefly and do NOT trigger an LLM reply.
        if _contains_hard_interrupt(normalized, self._hard):
            # Interrupt any ongoing speech (safe even if nothing is playing)
            await self.session.interrupt(force=True)
            await self.session.say("Okay.")
            raise StopResponse()

        # Otherwise: do nothing here → framework will generate the normal LLM reply automatically.
        return


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


AGENT_NAME = os.getenv("AGENT_NAME", "interrupt-demo")


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext):
    # Config lives next to this file by default
    default_cfg = str(Path(__file__).with_name("filter_config.json"))
    cfg_path = os.getenv("LK_BACKCHANNEL_CONFIG", default_cfg)
    backchannel_words, hard_interrupt_words = load_word_config(cfg_path)

    # ✅ Groq default updated (llama3-70b-8192 is deprecated)
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],

        # STT/TTS (not Groq)
        stt=deepgram.STT(model="nova-3"),
        tts=cartesia.TTS(),

        # Groq LLM only
        llm=groq_plugin.LLM(model=groq_model),

        # Interruption behavior
        allow_interruptions=True,
        min_interruption_words=1,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,

        # Assignment-specific word lists (your repo supports these)
        backchannel_words=backchannel_words,
        hard_interrupt_words=hard_interrupt_words,
    )

    await session.start(
        agent=InterruptDemoAgent(backchannel_words, hard_interrupt_words),
        room=ctx.room,
    )


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    cli.run_app(server)
