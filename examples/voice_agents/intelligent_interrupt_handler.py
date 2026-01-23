import string

class IntelligentInterruptionHandler:
    def __init__(self, session):
        self.session = session
        self.agent_speaking = False

        self.ignore_words = {
            "yeah", "ok", "okay", "hmm", "uh-huh", "right"
        }

        self.interrupt_words = {
            "stop", "wait", "no"
        }

        session.on("agent_state_changed", self.on_agent_state_changed)
        session.on("user_input_transcribed", self.on_user_input_transcribed)

    def on_agent_state_changed(self, event):
        self.agent_speaking = event.new_state == "speaking"

    def on_user_input_transcribed(self, event):
        if not event.is_final:
            return

        text = event.transcript.lower().strip()
        words = [
            w.strip(string.punctuation)
            for w in text.split()
            if w.strip(string.punctuation)
        ]

        if not words:
            return

        if self.agent_speaking:
            if any(w in self.interrupt_words for w in words):
                print("[INTERRUPT] Hard interrupt detected")
                self.session.interrupt()
                return

            if all(w in self.ignore_words for w in words):
                print("[IGNORE] Backchannel detected")
                self.session.clear_user_turn()
                return
