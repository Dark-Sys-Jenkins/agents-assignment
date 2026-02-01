# examples/voice_agents/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Challenge Requirement: 
# "Can the list of ignored words be changed easily (e.g., environment variable or config array)?"

# We check for an environment variable first, otherwise default to the list.
# We use a set() for O(1) lookup speed (imperceptible latency).
def get_ignore_words():
    env_words = os.getenv("IGNORE_WORDS")
    if env_words:
        return set(word.strip().lower() for word in env_words.split(","))
    
    return {
        "yeah.",
        "ok.",
        "hmm.",
        "right.",
        "uh-huh.",
        "okay.",
        "yep.",
        "aha."
    }

IGNORE_WORDS = get_ignore_words()
