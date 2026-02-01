import logging
import re
from livekit.agents.voice import agent_activity
try:
    import basic_agent
except ImportError:
    from examples.voice_agents import basic_agent
from livekit.agents import cli

import os

logger = logging.getLogger("intelligent-agent")

# Configurable ignore list via environment variable (comma-separated), or default
env_ignore = os.getenv("LIVEKIT_IGNORE_WORDS")
if env_ignore:
    IGNORE_WORDS = {w.strip().lower() for w in env_ignore.split(",") if w.strip()}
else:
    IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "hm", "right", "sure", "uh-huh"}

def split_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[\w'-]+\b", text)]

def _should_ignore_interruption(text: str) -> bool:
    if not text:
        return False
    words = split_words(text)
    if not words:
        return False
    if all(word in IGNORE_WORDS for word in words):
        logger.info(f"Ignoring interruption: '{text}' matches ignore list")
        return True
    return False

# Patch _interrupt_by_audio_activity
original_interrupt = agent_activity.AgentActivity._interrupt_by_audio_activity

def patched_interrupt_by_audio_activity(self):
    opt = self._session.options
    
    if (
        self.stt is not None
        and opt.min_interruption_words > 0
        and self._audio_recognition is not None
    ):
        text = self._audio_recognition.current_transcript
        # Check specific ignore words logic
        if _should_ignore_interruption(text):
            return

    return original_interrupt(self)

agent_activity.AgentActivity._interrupt_by_audio_activity = patched_interrupt_by_audio_activity

# Patch on_end_of_turn
original_on_end_of_turn = agent_activity.AgentActivity.on_end_of_turn

def patched_on_end_of_turn(self, info):
    # Check ignore logic before calling original
    # logic matches agent_activity.py:1377-1382 context
    if (
        self._current_speech is not None
        and not self._current_speech.interrupted
        and _should_ignore_interruption(info.new_transcript)
    ):
        logger.info(f"Ignoring interruption (end of turn): '{info.new_transcript}'")
        self._cancel_preemptive_generation()
        return False

    return original_on_end_of_turn(self, info)

agent_activity.AgentActivity.on_end_of_turn = patched_on_end_of_turn

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(basic_agent.server)
