IGNORE_WORDS={"yeah", "ok", "okay", "hmm", "uh-huh", "right", "aha", "yep", "got it"}
INTERRUPT_WORDS={"stop", "wait", "no", "cancel", "pause", "hold on"}
class InterruptFilter:
    def __init__(self):
        self.agent_speaking = False

    def on_audio_start(self):
        self.agent_speaking = True

    def on_audio_end(self):
        self.agent_speaking = False

    def should_interrupt(self, text: str) -> bool:
        clean = text.lower().strip()
        words = clean.split()

        if any(w in words for w in INTERRUPT_WORDS):
            return True

        if self.agent_speaking and all(w in IGNORE_WORDS for w in words):
            return False

        return True
