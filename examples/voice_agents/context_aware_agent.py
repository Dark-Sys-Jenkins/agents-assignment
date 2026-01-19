import logging
import asyncio
import re
import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.voice.agent_activity import AgentActivity

load_dotenv()

logger = logging.getLogger("context-aware-agent")

# --- Configuration ---
# Load ignore words from environment variable (comma separated) or use default
env_ignore = os.environ.get("IGNORE_WORDS")
if env_ignore:
    IGNORE_WORDS = set(word.strip().lower() for word in env_ignore.split(","))
else:
    IGNORE_WORDS = {
        "yeah", "ok", "hmm", "right", "uh-huh", "yep", "sure", "mhm", "aha",
        "okay", "ok yeah", "yeah ok", "yes", "uhhuh"
    }

# --- Monkey Patching ---
# Save the original method to call it if we decide to interrupt
_original_interrupt_by_audio_activity = AgentActivity._interrupt_by_audio_activity

def _should_ignore(text: str) -> bool:
    """
    Determines if the text should be ignored (passive acknowledgement).
    Returns True if the text consists only of ignore words/phrases.
    """
    if not text:
        return True
    
    # Normalize: lowercase, strip punctuation
    normalized = text.lower().strip()
    # Remove common punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Split into words to check against ignore list
    # Logic: If the ENTIRE input is composed of ignore words, we ignore it.
    # checking for exact match or single words from the list
    
    if normalized in IGNORE_WORDS:
        return True
        
    # Check if compount phrases are all in ignore list (e.g. "yeah ok")
    words = normalized.split()
    all_ignored = all(word in IGNORE_WORDS for word in words)
    
    return all_ignored

def _patched_interrupt_by_audio_activity(self: AgentActivity) -> None:
    """
    Patched version of _interrupt_by_audio_activity that adds context awareness.
    """
    # 1. State-Based Filtering: Check if agent is speaking
    # If agent is NOT speaking, we don't need to filter interruptions (standard behavior handles it)
    # However, standard behavior for 'not speaking' is usually 'start_user_activity' which this function handles too.
    # The original function handles: 
    #   - checking turn detection
    #   - starting user activity (rt_session)
    #   - interrupting current speech
    
    # We only want to prevent the INTERRUPTION of *current speech* for passive words.
    
    # Get current transcript if available
    transcript = ""
    if self._audio_recognition:
        transcript = self._audio_recognition.current_transcript
    
    should_block_interruption = False
    
    # Only block if we have text (STT triggered this) and it matches ignore list
    # AND the agent is currently speaking (otherwise "yeah" should be a valid turn start)
    if self._current_speech and not self._current_speech.done():
         if transcript and _should_ignore(transcript):
             should_block_interruption = True
             logger.info(f"Ignoring passive interruption: '{transcript}'")

    if should_block_interruption:
        # We DO NOT call the original interruption logic.
        # We might still want to signal 'user_activity' to some components if needed, 
        # but avoiding the interruption is the key.
        return

    # Call original method
    return _original_interrupt_by_audio_activity(self)

# Apply the patch
AgentActivity._interrupt_by_audio_activity = _patched_interrupt_by_audio_activity


# --- Agent Implementation ---
class ContextAwareAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful assistant. You are currently participating in a test for interruption recovery. "
                         "You should read long explanations or count to 20 to demonstrate that you are not interrupted by passive words. "
                         "If the user says 'stop' or asks a question, you should stop immediately.",
        )

    async def on_enter(self):
        self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
    session = AgentSession(
        stt=deepgram.STT(), # Using Deepgram for fast STT
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(), # Or cartesia if available/preferred
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # --- Critical Configuration ---
        # 1. Disable VAD-only interruptions to prevent "false start" stops before STT arrives.
        #    We set min_interruption_duration to a very high value.
        #    Note: This means purely non-verbal noise won't stop the agent, 
        #    which is acceptable as we rely on STT for "Stop" commands.
        min_interruption_duration=1000.0, 
        
        # 2. Allow interruptions generally (so we can filter them)
        allow_interruptions=True,
    )

    async def log_usage():
        pass # Optional usage logging

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=ContextAwareAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
