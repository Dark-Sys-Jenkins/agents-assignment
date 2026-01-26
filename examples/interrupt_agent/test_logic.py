from interrupt_handler import InterruptHandler


def fake_stop():
    print(">>> AGENT STOPPED")


def fake_respond(text):
    print(">>> AGENT RESPONDED:", text)


handler = InterruptHandler()

print("\n--- TEST 1: Agent SPEAKING, user says 'yeah' ---")
handler.on_agent_speaking_start()
handler.on_user_transcript("yeah", fake_stop, fake_respond)

print("\n--- TEST 2: Agent SPEAKING, user says 'yeah wait' ---")
handler.on_user_transcript("yeah wait", fake_stop, fake_respond)

print("\n--- TEST 3: Agent SILENT, user says 'yeah' ---")
handler.on_agent_speaking_end()
handler.on_user_transcript("yeah", fake_stop, fake_respond)

print("\n--- TEST 4: Agent SPEAKING, user says 'stop' ---")
handler.on_agent_speaking_start()
handler.on_user_transcript("stop", fake_stop, fake_respond)

print("\n--- TEST 5: Agent SPEAKING, user says 'hmm ok yeah' ---")
handler.on_agent_speaking_start()
handler.on_user_transcript("hmm ok yeah", fake_stop, fake_respond)

print("\n--- END OF TESTS ---")
exit(0)