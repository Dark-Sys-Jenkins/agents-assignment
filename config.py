"""
Configuration for interruption handling
Easily modify these lists to change behavior
"""

# Words to IGNORE when agent is speaking (backchanneling)
IGNORE_LIST = {
    "yeah",
    "ok",
    "okay",
    "sure",
    "hmm",
    "mhmm",
    "mm-hmm",
    "uh-huh",
    "yes",
    "yep",
    "yup",
    "got it",
    "right",
    "i see",
    "alright",
    "gotcha",
    "aha",
    "understood",
}

# Words to NEVER IGNORE - always interrupt
DONT_IGNORE_LIST = {
    "stop",
    "wait",
    "no",
    "hold on",
    "pause",
    "hold up",
    "hang on",
}