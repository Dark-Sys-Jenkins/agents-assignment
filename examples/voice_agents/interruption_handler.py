# examples/voice_agents/final_interrupt_agent.py
import asyncio
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
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import ChatContext, ChatMessage, StopResponse
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import UserInputTranscribedEvent

# load .env from repo root (two levels up from examples/voice_agents)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("final-interrupt-agent")

# ---------- Semantic config ----------
DEFAULT_IGNORE_WORDS = {
    "yeah", "yep", "yup", "yes",
    "ok", "okay", "hmm", "mhm", "mm",
    "uh-huh", "uh", "uhh", "uh huh",
    "right", "alright", "got it", "gotcha", "sure",
    "cool", "nice", "ah", "oh", "aha",
}

DEFAULT_STOP_WORDS = {
    "stop", "wait", "hold", "hold on", "cancel", "no",
}
def _load_word_set(env_name: str, default: set[str]) -> set[str]:
    raw = os.getenv(env_name)
    if raw is None:
        raw = ",".join(sorted(default))
    return {w.strip().lower() for w in raw.split(",") if w.strip()}

# Configurable lists (comma-separated)
IGNORE_WORDS = _load_word_set("LK_IGNORE_WORDS", DEFAULT_IGNORE_WORDS)
STOP_WORDS = _load_word_set("LK_STOP_WORDS", DEFAULT_STOP_WORDS)
# -------------------------------------

# runtime flags / state
agent_state = "idle"          # updated via agent_state_changed events by LiveKit
_ignore_next_turn = False     # set for soft backchannel: suppress generation but do NOT stop audio
_suppress_next_reply = False  # set for hard stop while speaking: interrupt + suppress any reply


# Small helpers
def normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace; keep punctuation removed for token checks."""
    if not text:
        return ""
    text = text.lower().strip()
    # replace punctuation with spaces (we only need tokens)
    text = re.sub(r"[^\w\s'-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokens(text: str):
    t = normalize_text(text)
    if not t:
        return []
    return t.split()


def contains_stop_token(text: str) -> bool:
    t = normalize_text(text)
    # check stop words by word-boundary aware tokenization
    for stop in STOP_WORDS:
        # exact token match (stop may contain spaces like "hold on" so check phrase)
        pattern = r"\b" + re.escape(stop) + r"\b"
        if re.search(pattern, t):
            return True
    return False


def all_tokens_are_soft(text: str) -> bool:
    ts = tokens(text)
    if not ts:
        return False
    # every token must be in IGNORE_WORDS (phrase tokens like 'uh-huh' split into 'uh' 'huh' but still fine)
    return all(tok in IGNORE_WORDS for tok in ts)


# ---------- Agent class ----------
class MyAgent(Agent):
    async def on_enter(self):
        # kick off conversation with a short, neutral greeting
        self.session.generate_reply(
            instructions="Greet the user briefly and ask how you can help. Avoid mentioning weather unless asked."
        )

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """
        This runs in the agent lifecycle (generation context).
        Soft backchannel suppression happens here without stopping audio playback.
        """
        global _ignore_next_turn, _suppress_next_reply

        # Soft backchannel: consume the turn without generating a reply (no audio stop)
        if _ignore_next_turn:
            _ignore_next_turn = False
            logger.info("Suppressing generation for backchannel turn (no audio stop)")
            raise StopResponse()

        # Hard stop while speaking: do not acknowledge; just stop and listen
        if _suppress_next_reply:
            _suppress_next_reply = False
            logger.info("Suppressing generation for hard stop turn")
            raise StopResponse()


# ---------------- Server / entrypoint ----------------
server = AgentServer()


def prewarm(proc: JobProcess):
    # load VAD model once for the worker
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """
    Main session entrypoint. We disable LiveKit's automatic interruption behavior
    and implement semantic interruption in the transcript event handler + agent lifecycle.
    """
    global agent_state, _ignore_next_turn, _suppress_next_reply

    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],

        # IMPORTANT: disable automatic VAD-driven interruptions so we can decide semantically
        allow_interruptions=True,
        min_interruption_words=99,        # Prevent auto-interrupt on short words
        min_interruption_duration=10.0,   # Prevent auto-interrupt on short sounds
        false_interruption_timeout=None,  # Wait longer to classify input
        resume_false_interruption=False,  # Resume if it was just a filler
    )

    agent = MyAgent(instructions="You are a helpful assistant. Keep responses concise.")

    # track agent playback state (speaking / idle)
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        # ev.new_state is typically "speaking" or "idle"
        global agent_state
        agent_state = ev.new_state
        logger.info("agent_state -> %s", agent_state)

    # transcript event: we set flags quickly based on partial/final transcripts.
    @session.on("user_input_transcribed")
    def _on_user_transcribed(ev: UserInputTranscribedEvent):
        """
        This handler must be very fast and deterministic:
        - If a stop token appears anywhere in the transcript (partial or final), interrupt immediately.
        - If the transcript is FINAL and agent is speaking and all tokens are soft -> set _ignore_next_turn.
        """
        global _ignore_next_turn, _suppress_next_reply, agent_state

        transcript = getattr(ev, "transcript", "") or ""
        if not transcript:
            return

        text = transcript.lower().strip()
        logger.info("USER_TRANSCRIPT: %r | final=%s | agent_state=%s", text, getattr(ev, "is_final", False), agent_state)

        # Hard interrupts are checked even on partial transcripts (do this ASAP)
        if contains_stop_token(text):
            logger.warning("Hard interrupt detected from transcript: %r", text)
            if agent_state == "speaking":
                _suppress_next_reply = True
            asyncio.ensure_future(session.interrupt())
            return

        # Soft backchannels: only consider final transcripts and only when agent is speaking
        if getattr(ev, "is_final", False) and agent_state == "speaking":
            # If the full final transcript consists only of soft tokens -> ignore next turn
            if all_tokens_are_soft(text):
                logger.info("Backchannel detected (soft words only), will suppress next generation: %r", text)
                _ignore_next_turn = True
                return

    # metrics (optional)
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info("Usage summary: %s", usage_collector.get_summary())

    ctx.add_shutdown_callback(log_usage)

    # start session
    await session.start(agent=agent, room=ctx.room, room_options=room_io.RoomOptions())


if __name__ == "__main__":
    cli.run_app(server)
