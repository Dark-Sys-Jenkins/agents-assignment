# Smart Interruption Agent Configuration

# Soft acknowledgments - Agent will IGNORE these and continue speaking
SOFT_ACKNOWLEDGMENTS = [
    "yeah",
    "yep",
    "yes",
    "uh-huh",
    "mm-hmm",
    "mhmm",
    "okay",
    "ok",
    "right",
    "sure",
    "got it",
    "i see",
    "makes sense",
    "understood",
    "alright",
    "cool",
    "nice",
    "go on",
    "continue",
    "keep going",
    "interesting",
    "really",
    "wow",
    "oh",
    "ah",
    "hmm",
]

# Hard interruptions - Agent will STOP and give control to user
HARD_INTERRUPTIONS = [
    "wait",
    "hold on",
    "stop",
    "hang on",
    "but",
    "however",
    "actually",
    "excuse me",
    "sorry",
    "one sec",
    "one second",
    "no",
    "what",
    "huh",
    "pardon",
]

# Polite interruptions - Agent will STOP
POLITE_INTERRUPTIONS = [
    "quick question",
    "can i ask",
    "may i",
    "could you",
    "before you",
    "let me",
    "i want to",
    "i need to",
    "just to clarify",
    "to be clear",
    "one thing",
]

# Timing configuration (in seconds)
MIN_SPEECH_DURATION = 1.0  # Don't interrupt in first 1 second
SHORT_SPEECH_THRESHOLD = 3.0  # Be conservative before 3 seconds
LONG_SPEECH_THRESHOLD = 8.0  # Be more lenient after 8 seconds
BASE_THRESHOLD = 0.7  # Base confidence threshold for interruption
