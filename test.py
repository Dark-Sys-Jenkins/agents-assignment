import sys
sys.path.insert(0, './livekit-agents')
import sys
import importlib.util

# Load backchannel_aware.py directly without going through the full livekit.agents module
spec = importlib.util.spec_from_file_location(
    "backchannel_aware",
    "./livekit-agents/livekit/agents/voice/backchannel_aware.py"
)
backchannel_aware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backchannel_aware)

InterruptionHandler = backchannel_aware.InterruptionHandler
InterruptionSettings = backchannel_aware.InterruptionSettings

handler = InterruptionHandler()
def run_test(name, result, expected):
    status = "PASS" if result == expected else "FAIL"
    print(f"{status:<6} | {name}")
    print(f"        expected = {expected}, got = {result}\n")
    return status == "PASS"


def main():
    handler = InterruptionHandler(
        InterruptionSettings(debug=False)
    )

    passed = 0
    total = 0

    print("=" * 70)
    print("BACKCHANNEL INTERRUPTION TEST SUITE")
    print("=" * 70)

    # ==================================================
    # Scenario 1: Long Explanation
    # ==================================================
    print("\nScenario 1: Agent speaking + filler words")

    tests = [
        ("yeah while speaking", "yeah", True),
        ("ok while speaking", "ok", True),
        ("okay yeah uh-huh", "okay yeah uh-huh", True),
        ("hmm right", "hmm right", True),
        ("yeah okay hmm", "yeah okay hmm", True),
    ]

    for name, text, expected in tests:
        total += 1
        if run_test(
            name,
            handler.should_ignore_interrupt(text, is_speaking=True),
            expected
        ):
            passed += 1

    # ==================================================
    # Scenario 2: Passive affirmation
    # ==================================================
    print("\nScenario 2: Agent silent + acknowledgement")

    tests = [
        ("yeah while silent", "yeah", False),
        ("ok while silent", "ok", False),
        ("hmm while silent", "hmm", False),
    ]

    for name, text, expected in tests:
        total += 1
        if run_test(
            name,
            handler.should_ignore_interrupt(text, is_speaking=False),
            expected
        ):
            passed += 1

    # ==================================================
    # Scenario 3: Corrections
    # ==================================================
    print("\nScenario 3: Semantic interruption")

    tests = [
        ("stop while speaking", "stop", False),
        ("no while speaking", "no", False),
        ("wait please", "wait please", False),
        ("hold on", "hold on", False),
    ]

    for name, text, expected in tests:
        total += 1
        if run_test(
            name,
            handler.should_ignore_interrupt(text, is_speaking=True),
            expected
        ):
            passed += 1

    # ==================================================
    # Scenario 4: Mixed filler + command
    # ==================================================
    print("\nScenario 4: Mixed filler and semantic content")

    tests = [
        ("yeah but wait", "yeah but wait", False),
        ("ok hmm stop", "ok hmm stop", False),
        ("yeah no", "yeah no", False),
        ("okay so wait", "okay so wait", False),
    ]

    for name, text, expected in tests:
        total += 1
        if run_test(
            name,
            handler.should_ignore_interrupt(text, is_speaking=True),
            expected
        ):
            passed += 1

    # ==================================================
    # Scenario 5: Edge cases
    # ==================================================
    print("\nScenario 5: Edge cases")

    tests = [
        ("empty string", "", False),
        ("punctuation only", "...", False),
        ("uppercase filler", "YEAH OKAY", True),
        ("mixed case filler", "Yeah OkAy", True),
    ]

    for name, text, expected in tests:
        total += 1
        if run_test(
            name,
            handler.should_ignore_interrupt(text, is_speaking=True),
            expected
        ):
            passed += 1

    # ==================================================
    # Final result
    # ==================================================
    print("=" * 70)
    print(f"FINAL RESULT: {passed}/{total} TESTS PASSED")
    print("=" * 70)


def demonstrate_state_awareness():
    """
    Visual demonstration of STATE AWARENESS:
    Shows how the SAME INPUT behaves differently based on is_speaking state
    """
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    
    print("\n" + "=" * 70)
    print("STATE AWARENESS DEMONSTRATION")
    print("=" * 70)
    print("\n🎯 Same Input, Different States:\n")
    
    test_inputs = ["yeah", "okay", "no stop", "wait"]
    
    for text in test_inputs:
        print(f"Input: '{text}'")
        print("-" * 70)
        
        # Test with agent speaking
        result_speaking = handler.should_ignore_interrupt(text, is_speaking=True)
        reason_speaking = handler.explain_decision(text, is_speaking=True)
        print(f"  Agent SPEAKING:  result={result_speaking:5} | reason: {reason_speaking}")
        
        # Test with agent silent
        result_silent = handler.should_ignore_interrupt(text, is_speaking=False)
        reason_silent = handler.explain_decision(text, is_speaking=False)
        print(f"  Agent SILENT:    result={result_silent:5} | reason: {reason_silent}")
        
        
        if result_speaking != result_silent:
            print(f"  STATE DEPENDENT: Result changes based on is_speaking")
        else:
            print(f"  STATE INDEPENDENT: Result is same regardless")
        print()


if __name__ == "__main__":
    main()
    demonstrate_state_awareness()
