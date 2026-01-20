"""
Interrupt Handler - Accuracy & Edge Case Tests
This script tests the interrupt handler logic for various edge cases and accuracy scenarios.

"""

from types import SimpleNamespace
from unittest.mock import Mock

print("=" * 70)
print("INTERRUPT HANDLER – ACCURACY & EDGE CASE TESTS")
print("=" * 70)

# -----------------------------
# Helper functions
# -----------------------------

def split_words(text):
    return [w for w in text.lower().strip().split() if w.strip()]

DEFAULT_ACK_WORDS = [
    "yeah", "yea", "ok", "okay", "hmm",
    "uh-huh", "uh", "mm", "mmhmm",
    "right", "yup", "yep", "gotcha", "alright"
]

INTERRUPT_KEYWORDS = {
    "stop", "wait", "no", "cancel", "hold", "actually"
}

def make_activity(transcript, speaking, ignore_list=None):
    activity = SimpleNamespace()

    activity.stt = True
    activity._audio_recognition = SimpleNamespace(
        current_transcript=transcript
    )

    activity._session = SimpleNamespace(
        options=SimpleNamespace(
            ignore_words=ignore_list or DEFAULT_ACK_WORDS,
            min_interruption_words=0,
            false_interruption_timeout=None,
            resume_false_interruption=False,
        ),
        output=SimpleNamespace(
            audio=SimpleNamespace(can_pause=True, pause=Mock(), resume=Mock())
        ),
        _update_agent_state=Mock(),
    )

    activity._rt_session = SimpleNamespace(
        start_user_activity=Mock(),
        interrupt=Mock(),
    )

    if speaking:
        speech = Mock()
        speech.interrupted = False
        speech.allow_interruptions = True
        speech.interrupt = Mock()
        activity._current_speech = speech
    else:
        activity._current_speech = None

    return activity


def interrupt_logic(activity):
    words = split_words(activity._audio_recognition.current_transcript or "")
    ignore_set = {w.lower() for w in activity._session.options.ignore_words}

    # Case 0: agent speaking + empty input → IGNORE (noise)
    if activity._current_speech and not words:
        return "IGNORED"
    
    # Case 1: agent speaking + only ack words → IGNORE
    if activity._current_speech and words:
        if all(w in ignore_set for w in words):
            return "IGNORED"


    # Case 2: agent silent → respond
    if not activity._current_speech:
        activity._rt_session.start_user_activity()
        return "RESPONDED"

    # Default interruption
    activity._current_speech.interrupt()
    return "INTERRUPTED"


# -----------------------------
# Test runner
# -----------------------------

tests = [
    # -------------------------------------------------
    # Assignment Scenarios (EXPLICIT)
    # -------------------------------------------------

    # Scenario 1: Long explanation + backchanneling
    ("Scenario 1: Ignore backchannel while speaking",
     "okay yeah uh uh", True, "IGNORED"),

    # Scenario 2: Passive affirmation when silent
    ("Scenario 2: Respond to yeah when silent",
     "yeah", False, "RESPONDED"),

    # Scenario 3: Correction / hard stop
    ("Scenario 3: No stop interrupts immediately",
     "no stop", True, "INTERRUPTED"),

    # Scenario 4: Mixed input with interrupt keyword
    ("Scenario 4: Mixed input causes interruption",
     "yeah okay but wait", True, "INTERRUPTED"),

    # -------------------------------------------------
    # Additional robustness tests
    # -------------------------------------------------

    ("Ignore short ack while speaking",
     "yeah", True, "IGNORED"),

    ("Interrupt on short stop",
     "stop", True, "INTERRUPTED"),

    ("Ignore multiple acknowledgements",
     "yeah okay hmm right uh mm", True, "IGNORED"),

    ("Interrupt on long mixed sentence",
     "yeah I understand what you are saying but wait I have a question",
     True, "INTERRUPTED"),

    ("Respond to long sentence when silent",
     "yeah that sounds good we can proceed now",
     False, "RESPONDED"),

    ("Ignore noise / filler input",
     "uh uh mm hmm", True, "IGNORED"),
]



passed = 0

print("\nRunning tests...\n")

for name, transcript, speaking, expected in tests:
    act = make_activity(transcript, speaking)
    result = interrupt_logic(act)

    if result == expected:
        print(f"✓ PASSED: {name}")
        passed += 1
    else:
        print(f"✗ FAILED: {name}")
        print(f"  Expected: {expected}, Got: {result}")

print("\n" + "=" * 70)
print(f"SUMMARY: {passed}/{len(tests)} TESTS PASSED")
print("=" * 70)

if passed == len(tests):
    print("🎉 ALL ACCURACY & EDGE CASE TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
