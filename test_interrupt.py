from livekit.agents.voice.audio_recognition import should_interrupt

tests = [
    ("yeah", True),
    ("ok hmm", True),
    ("stop", True),
    ("yeah wait", True),
    ("hello", True),
]

print("AGENT SPEAKING TESTS")
for text, speaking in tests:
    print(text, "=>", should_interrupt(text, speaking))

print("\nAGENT SILENT TESTS")
for text, _ in tests:
    print(text, "=>", should_interrupt(text, False))

