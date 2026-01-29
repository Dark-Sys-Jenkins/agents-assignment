import os
import re
import logging

logger = logging.getLogger("livekit.agents.voice.interruption_filter")

# Default words to ignore (passive acknowledgements / filler words)
DEFAULT_IGNORE_WORDS = {
    "yeah", "yep", "yup", "yes", "okay", "ok", "alright",
    "uh-huh", "uh huh", "uhuh", "mm-hmm", "mmhmm", "mhmm",
    "hmm", "hm", "um", "uh", "ah", "oh", "i see", "got it",
    "right", "understood", "cool", "sure", "absolutely",
    "definitely",
}

# Words that should always interrupt, even if agent is speaking
FORCE_INTERRUPT_WORDS = {
    "stop", "wait", "hold on", "pause", "hold up", "hang on",
    "no", "nope", "quit", "exit", "cancel", "abort",
    "never mind", "nevermind", "scratch that", "ignore that"
}

def _get_ignore_words() -> set[str]:
    """
    Get the set of words to ignore from environment variable or defaults.
    Environment variable: LIVEKIT_IGNORE_WORDS (comma separated)
    """
    env_words = os.environ.get("LIVEKIT_IGNORE_WORDS")
    if env_words:
        # Split by comma first, then strip whitespace
        words = {w.strip().lower() for w in env_words.split(",") if w.strip()}
        return words
    return DEFAULT_IGNORE_WORDS


# Cache the ignore words initialized from env/defaults
_IGNORE_WORDS = _get_ignore_words()


def _normalize_text(text: str) -> list[str]:
    """
    Normalize text for word matching:
    - Convert to lowercase
    - Remove punctuation (keep alphanumeric and hyphens)
    - Split into words
    """
    if not text or not text.strip():
        return []
    
    # Normalize text: lowercase
    cleaned_text = text.lower().strip()
    
    # Remove punctuation (keep only alphanumeric and spaces/hyphens)
    # This ensures "yeah." or "ok!" are matched as "yeah" and "ok"
    # We allow hyphens for "uh-huh"
    cleaned_text = re.sub(r'[^\w\s-]', '', cleaned_text)
    
    words = cleaned_text.split()
    return words


def should_ignore_interruption(text: str) -> bool:
    """
    Determines if the interruption should be ignored based on the transcript text.
    
    Args:
        text: The STT transcript text (interim or final).
        
    Returns:
        True if the interruption should be ignored (e.g. filler words, empty text).
        False if the interruption is active and should proceed.
        
    Logic:
    1. If text is empty/whitespace, ignore (wait for STT).
    2. If text contains force-interrupt words, DO NOT ignore.
    3. If text consists ONLY of ignore words, ignore.
    4. If text contains other words mixed with ignore words, do NOT ignore.
    """
    words = _normalize_text(text)
    
    if not words:
        # Case: VAD triggered but no STT yet.
        # Guidance: "Delay interruption decision until transcript is available"
        logger.debug(f"Empty or whitespace-only transcript, ignoring interruption")
        return True
    
    # Check for force-interrupt words first (these always interrupt)
    for word in words:
        if word in FORCE_INTERRUPT_WORDS:
            logger.debug(f"Force-interrupt word detected: '{word}' in '{text}'")
            return False
    
    # Check if ALL words are in the ignore list
    all_ignored = True
    for word in words:
        if word not in _IGNORE_WORDS:
            all_ignored = False
            break
    
    if all_ignored:
        # All words are filler words - ignore this interruption
        logger.debug(f"Ignoring interruption for filler words: '{text}' → {words}")
        return True
    
    # Mixed content (filler + real words) or non-filler words
    logger.debug(f"Real interruption detected: '{text}' → {words}")
    return False
