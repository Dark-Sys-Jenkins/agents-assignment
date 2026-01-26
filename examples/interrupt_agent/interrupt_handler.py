import re
from config import IGNORE_WORDS, INTERRUPT_WORDS


class InterruptHandler:
    def __init__(self):
        self.agent_state = "SILENT"
        self.interrupted = False

    # Called when agent audio STARTS
    def on_agent_speaking_start(self):
        self.agent_state = "SPEAKING"
        self.interrupted = False
        print("[STATE] Agent is SPEAKING")

    # Called when agent audio STOPS
    def on_agent_speaking_end(self):
        self.agent_state = "SILENT"
        self.interrupted = False
        print("[STATE] Agent is SILENT")

    # VAD hook (intentionally unused)
    def on_user_speech_start(self):
        pass

    # STT transcript hook
    def on_user_transcript(self, text, stop_audio, respond):
        text = self._normalize(text)
        print(f"[STT] User said: {text}")

        # 🔒 STRICT RULE (PDF):
        # Agent SPEAKING + filler → IGNORE COMPLETELY
        if self.agent_state == "SPEAKING" and self._is_ignore_only(text):
            print("[ACTION] Ignoring filler words")
            return  # ABSOLUTELY NO RESPONSE

        if self.agent_state == "SPEAKING":

            # Explicit interrupt words
            if self._contains_interrupt(text) and not self.interrupted:
                print("[ACTION] Interrupting agent")
                stop_audio()
                self.interrupted = True
                return

            # Any other mixed speech → interrupt once
            if not self.interrupted:
                print("[ACTION] Interrupting agent")
                stop_audio()
                self.interrupted = True
                return

        # Agent SILENT → normal response
        print("[ACTION] Agent responding normally")
        respond(text)

    # ---------------- HELPERS ---------------- #

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = text.replace("-", " ")
        text = re.sub(r"[^a-z\s]", "", text)
        return text.strip()

    def _is_ignore_only(self, text: str) -> bool:
        words = text.split()
        return len(words) > 0 and all(word in IGNORE_WORDS for word in words)

    def _contains_interrupt(self, text: str) -> bool:
        words = text.split()
        return any(word in INTERRUPT_WORDS for word in words)
