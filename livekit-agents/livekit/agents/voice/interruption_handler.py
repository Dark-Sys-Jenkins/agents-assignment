"""Intelligent interruption handling for LiveKit agents.

this module provides utilities to distinguish between passive acknowledgements
(backchanneling) and active interruptions based on the spoken content and
agent state.
"""

# backchanneling words that indicate passive listening acknowledgement
BACKCHANNELING_WORDS = {
    # English
    "yeah",
    "ok",
    "okay",
    "hmm",
    "uh-huh",
    "uh huh",
    "right",
    "yes",
    "yep",
    "uh",
    "mm",
    "mm-hmm",
    "mhmm",
    "mhmmm",
    "mhm",
    "ah",
    "aha",
    "i see",
    "got it",
}

# command words that should always trigger an interrupt
INTERRUPTION_COMMANDS = {
    "stop",
    "wait",
    "pause",
    "hold on",
    "hold",
    "no",
    "no stop",
    "nope",
    "don't",
    "dont",
    "hang on",
}


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()


def _split_words(text: str) -> list[str]:
    """Split text into words and clean punctuation."""
    import re
    # split on whitespace but preserve hyphenated words like "uh-huh"
    # remove leading/trailing punctuation from each word
    text_lower = text.lower()
    parts = text_lower.split()
    words = []
    for part in parts:
        # remove trailing punctuation but keep hyphens
        word = part.rstrip('.,!?;:\'"()')
        if word:
            words.append(word)
    return words


def is_backchanneling_only(text: str) -> bool:
    """
    Check if the text contains only backchanneling words (passive acknowledgement).
    
    Examples:
        - "yeah" -> True
        - "ok" -> True
        - "yeah okay" -> True
        - "yeah wait" -> False (contains "wait")
        - "stop" -> False (is a command)
    
    Args:
        text: The spoken text to analyze
        
    Returns:
        True if the text contains only backchanneling words, False otherwise
    """
    if not text or not text.strip():
        return False
    
    words = _split_words(text)
    
    if not words:
        return False
    
    # check if all words are in the backchanneling list
    return all(word in BACKCHANNELING_WORDS for word in words)


def contains_interruption_command(text: str) -> bool:
    """
    Check if the text contains explicit interruption commands.
    
    This is used for "mixed input" scenarios like "yeah wait a second"
    where the user clearly wants to interrupt despite saying a backchanneling word.
    
    Examples:
        - "stop" -> True
        - "wait a second" -> True
        - "yeah" -> False
        - "ok" -> False
    
    Args:
        text: The spoken text to analyze
        
    Returns:
        True if the text contains any interruption command, False otherwise
    """
    if not text or not text.strip():
        return False
    
    text_lower = _normalize_text(text)
    
    # check for multi-word commands first (longer matches)
    for cmd in sorted(INTERRUPTION_COMMANDS, key=len, reverse=True):
        if cmd in text_lower:
            return True
    
    return False


def should_ignore_as_backchanneling(text: str) -> bool:
    """
    Determine if the user input should be ignored as backchanneling.
    
    This returns True only when:
    1. The text contains ONLY backchanneling words
    2. The text does NOT contain any interruption commands
    
    Args:
        text: The spoken text to analyze
        
    Returns:
        True if the input should be ignored as backchanneling, False otherwise
    """
    # if it contains an explicit command, it's not just backchanneling
    if contains_interruption_command(text):
        return False
    
    # otherwise, check if it's purely backchanneling
    return is_backchanneling_only(text)
