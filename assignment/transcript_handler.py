# transcript_handler.py

import asyncio
import time
from interrupt_handler import classify_input


def handle_transcript(session, state_manager, text):
    user_text = text.lower().strip()
    print("User said:", user_text)

    # delay to avoid VAD issue
    time.sleep(0.2)

    decision = classify_input(user_text, state_manager.is_agent_speaking)
    print("Decision:", decision)

    if decision == "IGNORE":
        return

    elif decision == "INTERRUPT":
        print(" Interrupting agent!")
        session.interrupt()

    else:
        return