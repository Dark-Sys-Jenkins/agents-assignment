# interrupt_handler.py
import re

IGNORE_WORDS = ["yeah", "okay", "hmm", "uh-huh", "right"]
COMMAND_WORDS = ["stop", "wait", "no"]


def classify_input(text: str, is_agent_speaking: bool) -> str:
    """
    Decide how agent should react to user input.

    Returns:
        "IGNORE"     -> ignore input (continue speaking)
        "INTERRUPT"  -> stop agent immediately
        "RESPOND"    -> treat as normal input
    """

    if not text:
        return "RESPOND"

    text = text.lower().strip()

    # Priority 1: COMMAND (even inside sentence)
    for cmd in COMMAND_WORDS:
        if cmd in text:
            return "INTERRUPT"

    # Priority 2: Ignore filler words ONLY when agent speaking
    if is_agent_speaking:
        # check exact or repeated fillers
        words = re.findall(r'\b\w+\b', text)

        # if ALL words are filler → ignore
        if all(word in IGNORE_WORDS for word in words):
            return "IGNORE"

    # Default: normal response
    return "RESPOND"