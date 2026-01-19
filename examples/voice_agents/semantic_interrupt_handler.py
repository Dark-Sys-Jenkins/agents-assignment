class SemanticInterruptHandler:
    def __init__(self, ignore_words=None, interrupt_words=None):
        self.ignore_words = ignore_words or set()
        self.interrupt_words = interrupt_words or set()
        self.agent_is_speaking = False
        self.pending_interrupt = False

    def on_agent_start_speaking(self):
        self.agent_is_speaking = True
        self.pending_interrupt = False

    def on_agent_stop_speaking(self):
        self.agent_is_speaking = False
        self.pending_interrupt = False

    def on_vad_detected(self):
        if self.agent_is_speaking:
            self.pending_interrupt = True

    def on_transcription(self, text: str):
        text = text.lower().strip()

        if self.agent_is_speaking and self.pending_interrupt:
            if any(word in text for word in self.interrupt_words):
                self.on_agent_stop_speaking()
                return "INTERRUPT"
            else:
                self.pending_interrupt = False
                return "IGNORE"

        return "RESPOND"


if __name__ == "__main__":
    handler = SemanticInterruptHandler(
        ignore_words={"yeah", "ok", "hmm"},
        interrupt_words={"stop", "wait"}
    )

    handler.on_agent_start_speaking()
    handler.on_vad_detected()
    print("RESPONSE ON SAYING ~YEAH~, WHILE SPEAKING:")
    print(handler.on_transcription("yeah"))

    handler.on_agent_start_speaking()
    handler.on_vad_detected()
    print("RESPONSE ON SAYING ~STOP~, WHILE SPEAKING:")
    print(handler.on_transcription("stop"))

    print("RESPONSE ON SAYING ~YEAH~, WHEN SILENT:")
    print(handler.on_transcription("yeah"))

    handler.on_agent_start_speaking()
    handler.on_vad_detected()
    print("RESPONSE ON SAYING ~YEAH WAIT~, WHILE SPEAKING:")
    print(handler.on_transcription("yeah wait"))
