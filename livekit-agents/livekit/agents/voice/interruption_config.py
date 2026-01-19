

"""
Configuration for intelligent interruption handling in LiveKit agents.

These word lists control how the agent distinguishes between passive acknowledgements
(backchanneling) and active interruptions.
"""

# Words that should be ignored when the agent is actively speaking
# These are typically passive acknowledgements and filler words
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "right", "yep", "mmhmm",
    "sure", "understood", "got it", "uh", "um", "ah", "yeah yeah",
    "absolutely", "definitely", "certainly", "sounds good", "i see",
    "i know", "i get it", "makes sense", "got ya", "no kidding",
    "you bet", "for sure", "all right", "alright"
}

# Words that should always trigger an interruption, regardless of context
# These are typically commands or directive interruptions
INTERRUPT_WORDS = {
    "stop", "wait", "no", "hold", "cancel", "pause",
    "hold on", "wait wait", "one second", "one sec", "just a sec",
    "hang on", "slow down", "repeat that", "what", "sorry", "excuse me",
    "never mind", "never", "don't", "don't say that"
}

# Filler words that are okay to appear mixed with ignore words
# These don't trigger interruption by themselves
FILLER_WORDS = {
    "but", "and", "or", "like", "you know", "i mean", "actually",
    "well", "so", "anyway", "basically", "essentially", "practically",
    "kind of", "sort of", "somehow", "somewhat", "quite", "really",
    "very", "pretty", "honestly", "seriously", "literally"
}

MICRO_DEBOUNCE_MS = 150