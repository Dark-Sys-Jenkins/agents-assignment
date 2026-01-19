import time
from semantic_interrupt_handler import SemanticInterruptHandler

handler = SemanticInterruptHandler(
    ignore_words={"yeah", "ok", "hmm"},
    interrupt_words={"stop", "wait"}
)

print("\n--- AUDIO TIMELINE DEMO ---\n")

# Agent starts speaking
handler.on_agent_start_speaking()
print("[t=0.0s] Agent starts speaking")

# Simulate audio chunks
for t in range(1, 6):
    time.sleep(0.1)
    print(f"[t={t*0.1:.1f}s] 🔊 audio chunk")

    # At t=0.2s user says "yeah"
    if t == 2:
        handler.on_vad_detected()
        decision = handler.on_transcription("yeah")
        print(f"[t=0.2s] User says 'yeah' → {decision}")

    # At t=0.4s user says "stop"
    if t == 4:
        handler.on_vad_detected()
        decision = handler.on_transcription("yeah wait")
        print(f"[t=0.4s] User says 'stop' → {decision}")
        break

print("\n--- END DEMO ---\n")
