"""
Standalone test script for BackchannelFilter.
This script tests the filter logic without requiring LiveKit dependencies.
"""

import re


def simple_split_words(text, ignore_punctuation=True):
    """Simple word splitting for testing."""
    if not text:
        return []
    # Remove punctuation if requested
    if ignore_punctuation:
        text = re.sub(r'[^\w\s-]', '', text)
    # Split on whitespace and hyphens
    words = re.split(r'[\s-]+', text.lower())
    return [w.strip() for w in words if w.strip()]


class BackchannelFilter:
    """Standalone version of BackchannelFilter for testing."""

    DEFAULT_IGNORE_WORDS = [
        "yeah", "ok", "okay", "hmm", "right", "uh-huh", "uh", "um",
        "yep", "sure", "mhm", "mm-hmm", "mm", "aha", "mhmm",
    ]

    INTERRUPTION_COMMANDS = [
        "wait", "stop", "no", "hold", "pause", "cancel", "nevermind", "never mind",
    ]

    def __init__(self, ignore_words=None):
        if ignore_words is None:
            ignore_words = self.DEFAULT_IGNORE_WORDS
        self._ignore_words = {word.lower().strip() for word in ignore_words}
        self._interruption_commands = {cmd.lower().strip() for cmd in self.INTERRUPTION_COMMANDS}

    def _normalize_text(self, text):
        return text.lower().strip()

    def _extract_words(self, text):
        if not text or not text.strip():
            return []
        words = simple_split_words(text, ignore_punctuation=True)
        return [w.lower().strip() for w in words if w.strip()]

    def should_ignore(self, text):
        if not text or not text.strip():
            return True
        words = self._extract_words(text)
        if not words:
            return True
        return all(word in self._ignore_words for word in words)

    def contains_interruption_command(self, text):
        if not text or not text.strip():
            return False
        normalized_text = self._normalize_text(text)
        for cmd in self._interruption_commands:
            if cmd in normalized_text:
                return True
        return False

    def should_interrupt(self, text, agent_is_speaking):
        if not agent_is_speaking:
            return False
        if self.contains_interruption_command(text):
            return True
        if self.should_ignore(text):
            return False
        return True


def test_backchannel_filter():
    """Test the BackchannelFilter with various scenarios."""
    filter_instance = BackchannelFilter()

    print("=" * 70)
    print("BACKCHANNEL FILTER TEST SUITE")
    print("=" * 70)
    print()

    # Test Case 1: Filler words when agent is speaking (should ignore)
    print("Test Case 1: Agent Speaking + Filler Words")
    print("-" * 70)
    test_cases_ignore = [
        "yeah",
        "ok",
        "okay",
        "hmm",
        "right",
        "uh-huh",
        "yeah okay",
        "yeah right",
        "ok hmm",
    ]

    all_passed = True
    for text in test_cases_ignore:
        should_interrupt = filter_instance.should_interrupt(text, agent_is_speaking=True)
        passed = not should_interrupt
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  Input: '{text}' | Agent: SPEAKING | Result: {status}")

    print(f"\n  Test Case 1: {'[ALL PASSED]' if all_passed else '[SOME FAILED]'}")
    print()

    # Test Case 2: Interruption commands when agent is speaking (should interrupt)
    print("Test Case 2: Agent Speaking + Interruption Commands")
    print("-" * 70)
    test_cases_interrupt = [
        "stop",
        "wait",
        "no",
        "no stop",
        "wait a second",
        "hold on",
    ]

    all_passed = True
    for text in test_cases_interrupt:
        should_interrupt = filter_instance.should_interrupt(text, agent_is_speaking=True)
        passed = should_interrupt
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  Input: '{text}' | Agent: SPEAKING | Result: {status}")

    print(f"\n  Test Case 2: {'[ALL PASSED]' if all_passed else '[SOME FAILED]'}")
    print()

    # Test Case 3: Mixed input (filler words + interruption command)
    print("Test Case 3: Agent Speaking + Mixed Input")
    print("-" * 70)
    test_cases_mixed = [
        ("yeah okay but wait", True),
        ("yeah right stop", True),
        ("ok hmm yeah", False),
        ("yeah no", True),
    ]

    all_passed = True
    for text, expected_interrupt in test_cases_mixed:
        should_interrupt = filter_instance.should_interrupt(text, agent_is_speaking=True)
        passed = should_interrupt == expected_interrupt
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        expected_str = "INTERRUPT" if expected_interrupt else "IGNORE"
        actual_str = "INTERRUPT" if should_interrupt else "IGNORE"
        print(f"  Input: '{text}' | Expected: {expected_str} | Actual: {actual_str} | {status}")

    print(f"\n  Test Case 3: {'[ALL PASSED]' if all_passed else '[SOME FAILED]'}")
    print()


def demonstrate_scenarios():
    """Demonstrate the key scenarios for video/log proof."""
    filter_instance = BackchannelFilter()

    print("\n" + "=" * 70)
    print("DEMONSTRATION SCENARIOS FOR PROOF")
    print("=" * 70)
    print()

    scenarios = [
        {
            "name": "Scenario 1: Agent Speaking + User says 'yeah'",
            "text": "yeah",
            "agent_speaking": True,
            "expected": False,
            "behavior": "Agent continues speaking without pausing"
        },
        {
            "name": "Scenario 2: Agent Silent + User says 'yeah'",
            "text": "yeah",
            "agent_speaking": False,
            "expected": False,
            "behavior": "Agent processes 'yeah' as valid input and responds"
        },
        {
            "name": "Scenario 3: Agent Speaking + User says 'stop'",
            "text": "stop",
            "agent_speaking": True,
            "expected": True,
            "behavior": "Agent stops immediately"
        },
        {
            "name": "Scenario 4: Agent Speaking + User says 'yeah okay but wait'",
            "text": "yeah okay but wait",
            "agent_speaking": True,
            "expected": True,
            "behavior": "Agent stops (contains 'wait' command)"
        },
    ]

    for scenario in scenarios:
        print(scenario["name"])
        print("-" * 70)
        result = filter_instance.should_interrupt(
            scenario["text"], 
            scenario["agent_speaking"]
        )
        passed = result == scenario["expected"]
        status = "[PASS]" if passed else "[FAIL]"

        print(f"User Input: '{scenario['text']}'")
        print(f"Agent State: {'SPEAKING' if scenario['agent_speaking'] else 'SILENT'}")
        print(f"Filter Decision: {'INTERRUPT' if result else 'IGNORE'}")
        print(f"Expected Behavior: {scenario['behavior']}")
        print(f"Result: {status}")
        print()


if __name__ == "__main__":
    # Run comprehensive tests
    test_backchannel_filter()

    # Run demonstration scenarios
    demonstrate_scenarios()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nTo create video proof:")
    print("1. Run a LiveKit agent session")
    print("2. While agent is speaking, say 'yeah' or 'ok' - agent should continue")
    print("3. When agent is silent, say 'yeah' - agent should respond")
    print("4. While agent is speaking, say 'stop' - agent should stop immediately")
    print("=" * 70)