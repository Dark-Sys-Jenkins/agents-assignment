IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "right", "uh-huh"}
INTERRUPT_WORDS = {"stop", "wait", "no", "hold"}

class InterruptionHandler:
    def __init__(self):
        self.agent_is_speaking = False

    def set_agent_state(self, speaking: bool):
        self.agent_is_speaking = speaking

    def contains_interrupt(self, text: str):
        text = text.lower()
        return any(word in text for word in INTERRUPT_WORDS)

    def check_input(self, text: str):
        text = text.lower().strip()
        words = set(text.split())

        if self.agent_is_speaking:
            if self.contains_interrupt(text):
                return "INTERRUPT"
            if words.issubset(IGNORE_WORDS):
                return "IGNORE"
            return "INTERRUPT"

        return "RESPOND"
