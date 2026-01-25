import os

# Base list of words that are considered "passive acknowledgement"
DEFAULT_IGNORE_WORDS = {
    "yeah", "yes", "yep", "yup", 
    "ok", "okay", "okie", 
    "right", "sure", "cool", "nice", 
    "got it", "i see", "makes sense",
    "um", "uh", "hmm",
    "uh-huh", "uhhuh",   
    "mm-hmm", "mmhmm", 
    "aha",
}

def get_ignore_words():
    env_words = os.getenv("AGENT_IGNORE_WORDS")
    if env_words:
        custom_words = set(w.strip().lower() for w in env_words.split(","))
        return DEFAULT_IGNORE_WORDS.union(custom_words)
    return DEFAULT_IGNORE_WORDS