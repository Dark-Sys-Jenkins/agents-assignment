# interrupt_logic.py

IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh", "uh-huh", "right", "aha"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "pause", "cancel", "hold"
}


class InterruptLogic:
    def __init__(self):
        self.agent_speaking = False
        self.pending_interrupt = False

    def on_agent_speaking_start(self):
        self.agent_speaking = True

    def on_agent_speaking_end(self):
        self.agent_speaking = False
        self.pending_interrupt = False

    def on_vad_interrupt(self) -> bool:
        """
        Called when VAD detects speech.
        Returns True if interruption should be blocked for now.
        """
        if self.agent_speaking:
            self.pending_interrupt = True
            return True
        return False

    def resolve_transcript(self, text: str) -> str | None:
        """
        Returns:
        - "ignore"
        - "interrupt"
        - None
        """
        if not self.pending_interrupt:
            return None

        words = set(text.lower().strip().split())
        has_command = any(w in INTERRUPT_WORDS for w in words)
        soft_only = all(w in IGNORE_WORDS for w in words)

        self.pending_interrupt = False

        if has_command:
            return "interrupt"
        if soft_only:
            return "ignore"
        return "interrupt"


interrupt_logic = InterruptLogic()
# Loading an instance for testing purposes 