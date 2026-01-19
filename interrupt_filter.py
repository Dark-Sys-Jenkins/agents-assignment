from config import IGNORE_WORDS, INTERRUPT_KEYWORDS

class InterruptFilter:
    def __init__(self):
        self.agent_speaking = False

    def on_agent_start_speaking(self):
        self.agent_speaking = True

    def on_agent_stop_speaking(self):
        self.agent_speaking = False

    def on_vad_trigger(self):
        """
        Called when VAD detects user speech.
        If agent is speaking, temporarily block interruption
        until STT result arrives.
        """
        if self.agent_speaking:
            return False
        return True

    def on_stt_result(self, text: str):
        """
        Decide what to do once final STT text arrives.
        """
        text = text.lower().strip()

        has_interrupt = any(word in text for word in INTERRUPT_KEYWORDS)
        is_filler_only = all(word in IGNORE_WORDS for word in text.split())

        # Case 1: Agent speaking + real command → INTERRUPT
        if self.agent_speaking and has_interrupt:
            return "INTERRUPT"

        # Case 2: Agent speaking + filler → IGNORE
        if self.agent_speaking and is_filler_only:
            return "IGNORE"

        # Case 3: Normal input
        return "PROCESS"
