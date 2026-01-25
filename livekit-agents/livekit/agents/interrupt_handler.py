import re

IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "right", "uh-huh"}
INTERRUPT_WORDS = {"stop", "wait", "no", "cancel"}

class InterruptionHandler:
    def __init__(self):
        self.agent_is_speaking = False

    def set_agent_state(self, speaking: bool):
        self.agent_is_speaking = speaking

    def contains_interrupt(self, text: str):
        words = set(re.findall(r"\b[\w-]+\b", text.lower()))
        return bool(words & INTERRUPT_WORDS)

    def check_input(self, text: str):
        text = text.lower().strip()
        if not text:
            return "IGNORE"

        words = set(re.findall(r"\b[\w-]+\b", text))

        if self.agent_is_speaking:
            if self.contains_interrupt(text):
                return "INTERRUPT"
            if words.issubset(IGNORE_WORDS):
                return "IGNORE"
            return "INTERRUPT"

        return "RESPOND"
