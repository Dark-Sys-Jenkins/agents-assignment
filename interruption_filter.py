import os
import re
from typing import Set


def _parse_env_list(env_var: str, default: Set[str]) -> Set[str]:
    """Parse comma-separated env var into set, fallback to default."""
    value = os.getenv(env_var)
    if not value:
        return default
    return {word.strip() for word in value.split(",") if word.strip()}


# Load from env with defaults
IGNORE_WORDS = _parse_env_list("IGNORE_WORDS", {
    "yeah", "yep", "yes", "yup", "ok", "okay", "alright",
    "uh-huh", "uh huh", "uhuh", "mm-hmm", "mmhmm", "mhmm",
    "hmm", "hm", "um", "uh", "ah", "oh", "right", "got it",
    "gotcha", "sure", "fine", "cool", "good", "great", "mhm", "aha"
})

FORCE_INTERRUPT_WORDS = _parse_env_list("FORCE_INTERRUPT_WORDS", {
    "stop", "wait", "hold on", "pause", "hold up", "hang on",
    "no", "nope", "quit", "exit", "cancel", "abort",
    "never mind", "scratch that"
})


def should_ignore_interruption(text: str) -> bool:
    """
    Determine if an interruption should be ignored.
    """
    # Debug: show exactly what we receive
    print(f"[DEBUG should_ignore] raw: '{text}'")

    # Normalize aggressively
    text = text.lower().strip()
    text = re.sub(r"[^a-z\s]", "", text)  # remove everything except letters + spaces

    print(f"[DEBUG should_ignore] normalized: '{text}'")

    words = text.split()
    print(f"[DEBUG should_ignore] words: {words}")

    if not words:
        return True

    # Any force word → do NOT ignore (interrupt)
    for word in words:
        if word in FORCE_INTERRUPT_WORDS:
            print(f"[DEBUG] FORCE word found: '{word}' → interrupt")
            return False

    # All ignore words → ignore
    if all(word in IGNORE_WORDS for word in words):
        print(f"[DEBUG] All ignore words → ignore")
        return True

    print("[DEBUG] Mixed/unknown → interrupt")
    return False
