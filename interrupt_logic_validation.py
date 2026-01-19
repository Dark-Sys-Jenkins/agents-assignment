import time

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
        if self.agent_speaking:
            self.pending_interrupt = True
            return True
        return False

    def resolve_transcript(self, text: str):
        if not self.pending_interrupt:
            return None

        words = set(text.lower().split())
        has_command = any(w in INTERRUPT_WORDS for w in words)
        soft_only = all(w in IGNORE_WORDS for w in words)

        self.pending_interrupt = False

        if has_command:
            return "interrupt"
        if soft_only:
            return "ignore"
        return "interrupt"


# ===== TESTS =====

logic = InterruptLogic()

def run(agent_speaking, text):
    if agent_speaking:
        logic.on_agent_speaking_start()
        logic.on_vad_interrupt()
    else:
        logic.on_agent_speaking_end()

    decision = logic.resolve_transcript(text)

    print(
        f"[{time.strftime('%H:%M:%S')}] "
        f"agent_speaking={agent_speaking} | "
        f"text='{text}' | "
        f"decision={decision}"
    )


print("=== INTERRUPTION LOGIC VALIDATION ===")

run(True, "yeah")
run(True, "ok hmm")
run(True, "stop")
run(True, "yeah wait")
run(False, "yeah")
