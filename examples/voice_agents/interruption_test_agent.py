import logging
import asyncio
import sys
import os
import ssl
import certifi

# ---------- Environment Setup ----------
# 🔒 SSL FIX (macOS compatibility)
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["AIOHTTP_NO_EXTENSIONS"] = "1"
ssl._create_default_https_context = ssl._create_unverified_context

# 🛠️ Force local livekit-agents SDK (contains smart interruption logic)
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../livekit-agents"))
)

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    RunContext,
)
from livekit.agents.voice import UserInputTranscribedEvent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero

# Import Modular Config
try:
    from .agent_config import (
        INTERRUPTION_IGNORE_LIST,
        LLM_MODEL,
        LLM_BASE_URL,
        AGENT_INSTRUCTIONS
    )
except ImportError:
    # Fallback if running from a different context
    from agent_config import (
        INTERRUPTION_IGNORE_LIST,
        LLM_MODEL,
        LLM_BASE_URL,
        AGENT_INSTRUCTIONS
    )

# ------------------------------------

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interruption-test-agent")

# ================= AGENT =================

class InterruptionTestAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTIONS,
            interruption_ignore_list=INTERRUPTION_IGNORE_LIST,
        )

    async def on_enter(self):
        """Called upon successful session entry."""
        # Initial greeting to welcome the user
        await asyncio.sleep(1)
        self.session.say("Hello! I am your interruption test agent. Say 'Read history' to begin.")
        logger.info("AGENT: Initial greeting sent.")

    # ---------- TOOLS ----------

    @function_tool
    async def read_history(self):
        """Reads a detailed history lesson to demonstrate interruption handling."""
        logger.info("TOOL_CALL: read_history")
        return (
            "I will now read a long paragraph about computer history. "
            "In the early days of computing, machines were extremely large and expensive. "
            "They occupied entire rooms and required teams of operators. "
            "Programming was done using punch cards and manual wiring. "
            "The invention of the transistor changed everything. "
            "Computers became smaller, faster, and more reliable. "
            "Integrated circuits made mass production possible. "
            "Personal computers appeared in homes and offices. "
            "The internet connected the world in new ways. "
            "Today, artificial intelligence is shaping the future of computing. "
            "I will continue speaking unless you say stop."
        )

    @function_tool
    async def stop_speech(self, context: RunContext):
        """Forcefully stops the agent's current speech."""
        logger.info("TOOL_CALL: stop_speech")
        await self.session.interrupt(force=True)
        return "Stopped."

# ================= SERVER =================

server = AgentServer()

def prewarm(proc: JobProcess):
    """Load heavy resources before jobs arrive."""
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    logger.info(f"New session in room: {ctx.room.name}")
    
    # Initialize Session with Plugins
    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(
            base_url=LLM_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=LLM_MODEL,
        ),
        tts=deepgram.TTS(),
        vad=ctx.proc.userdata["vad"],
    )

    agent = InterruptionTestAgent()

    @session.on("user_input_transcribed")
    def on_transcript(ev: UserInputTranscribedEvent):
        """Listener for custom fail-safe logic and debugging."""
        if ev.transcript:
            logger.info(f"USER_SAID: '{ev.transcript}' (final={ev.is_final})")
            
            # Fail-safe backup for the 'Read history' command
            clean_text = ev.transcript.lower().strip()
            if "read history" in clean_text and ev.is_final:
                # If agent is silent, we manually trigger the history response
                # to ensure reliability regardless of LLM state.
                if session.agent_state == "listening":
                     logger.info("FAIL-SAFE: Forcing history reply.")
                     session.say(
                        "Sure! I'll read the history for you. "
                        "Early computers were room-sized giants. "
                        "Then transistors made them smaller. "
                        "The PC revolution followed, and then the internet. "
                        "Now, we have AI and incredibly fast phones!"
                    )

    # Start the agent session
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started and worker ready.")

# ================= MAIN ==================

if __name__ == "__main__":
    cli.run_app(server)
