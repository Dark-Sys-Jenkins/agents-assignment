"""
Standalone test cases for the Context-Aware Interruption Handler.

This module tests the intelligent handling of backchannel utterances
without requiring the full LiveKit dependencies.
"""

import sys
import re
from datetime import datetime
from typing import List, Tuple


class InterruptionHandlerStandalone:
    """Standalone implementation for testing."""
    
    def __init__(self, ignore_list=None):
        if ignore_list is None:
            ignore_list = ["yeah", "ok", "okay", "hmm", "right", "uh-huh", "huh", "uh"]
        self._ignore_list_lower = {word.lower().strip() for word in ignore_list}
    
    def should_ignore_interrupt(self, transcript, agent_is_speaking):
        """Determine if an interrupt should be ignored."""
        if not transcript:
            return False
        
        words = self._extract_words(transcript)
        
        if not words:
            return False
        
        has_non_filler_words = self._has_non_filler_words(words)
        
        if has_non_filler_words:
            return False
        
        if agent_is_speaking:
            return True
        else:
            return False
    
    def _extract_words(self, text):
        """Extract and normalize words from text."""
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _has_non_filler_words(self, words):
        """Check if word list contains non-filler words."""
        for word in words:
            if word not in self._ignore_list_lower:
                return True
        return False
    
    def get_interrupt_reason(self, transcript, agent_is_speaking):
        """Get reason for interrupt decision."""
        words = self._extract_words(transcript)
        
        if not words:
            return "empty_transcript"
        
        if self._has_non_filler_words(words):
            return "contains_semantic_content"
        
        if agent_is_speaking:
            return "passive_acknowledgement_ignored_agent_speaking"
        else:
            return "passive_acknowledgement_agent_silent"


class TestLogger:
    """Custom logger for test output."""
    
    def __init__(self):
        self.logs: List[str] = []
        self.test_results: List[Tuple[str, bool, str]] = []
        
    def log(self, level, message):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f"[{timestamp}] {level:12s} {message}"
        self.logs.append(formatted_msg)
        print(formatted_msg)
    
    def test_pass(self, test_name, details):
        """Record passing test."""
        self.log("PASS", f"✓ {test_name}")
        self.log("INFO", f"  └─ {details}")
        self.test_results.append((test_name, True, details))
    
    def test_fail(self, test_name, expected, actual):
        """Record failing test."""
        self.log("FAIL", f"✗ {test_name}")
        self.log("ERROR", f"  ├─ Expected: {expected}")
        self.log("ERROR", f"  └─ Actual: {actual}")
        self.test_results.append((test_name, False, f"Expected {expected}, got {actual}"))
    
    def section(self, title):
        """Log section header."""
        self.log("", "")
        self.log("", "=" * 80)
        self.log("", f"  {title}")
        self.log("", "=" * 80)
    
    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        self.log("", "")
        self.log("", "=" * 80)
        self.log("", f"TEST SUMMARY: {passed}/{total} passed ({100*passed//max(1,total)//1}%)")
        self.log("", "=" * 80)
        
        if passed < total:
            self.log("", "Failed tests:")
            for name, result, details in self.test_results:
                if not result:
                    self.log("", f"  • {name}: {details}")


test_log = TestLogger()


def test_scenario_1_long_explanation():
    """Scenario: Agent is speaking, user says backchannel utterances."""
    test_log.section("SCENARIO 1: The Long Explanation (Backchannel During Speaking)")
    
    handler = InterruptionHandlerStandalone()
    
    test_cases = [
        ("yeah", True, "single filler word while speaking"),
        ("okay", True, "single filler word variant while speaking"),
        ("yeah okay", True, "multiple filler words while speaking"),
        ("uh-huh", True, "backchannel token while speaking"),
        ("okay yeah uh-huh", True, "multiple backchannel utterances while speaking"),
        ("hmm right", True, "common filler combinations while speaking"),
    ]
    
    test_log.log("INFO", "Agent State: SPEAKING")
    test_log.log("INFO", "Expectation: All backchannel utterances should be IGNORED")
    test_log.log("", "")
    
    all_pass = True
    for transcript, _, description in test_cases:
        should_ignore = handler.should_ignore_interrupt(
            transcript=transcript,
            agent_is_speaking=True
        )
        reason = handler.get_interrupt_reason(transcript, True)
        
        if should_ignore:
            test_log.test_pass(
                f"Backchannel ignored: '{transcript}'",
                f"{description} - Reason: {reason}"
            )
        else:
            test_log.test_fail(
                f"Backchannel ignored: '{transcript}'",
                "IGNORE (should_ignore=True)",
                f"INTERRUPT (should_ignore=False)"
            )
            all_pass = False
    
    return all_pass


def test_scenario_2_passive_affirmation():
    """Scenario: Agent is silent, user says backchannel."""
    test_log.section("SCENARIO 2: The Passive Affirmation (Response While Silent)")
    
    handler = InterruptionHandlerStandalone()
    
    test_cases = [
        ("yeah", False, "single affirmation while silent"),
        ("ok", False, "single ok while silent"),
        ("hmm", False, "hmm while silent"),
        ("right", False, "right while silent"),
        ("uh-huh", False, "uh-huh while silent"),
    ]
    
    test_log.log("INFO", "Agent State: LISTENING/SILENT")
    test_log.log("INFO", "Expectation: All backchannel utterances should RESPOND (not ignore)")
    test_log.log("", "")
    
    all_pass = True
    for transcript, _, description in test_cases:
        should_ignore = handler.should_ignore_interrupt(
            transcript=transcript,
            agent_is_speaking=False
        )
        reason = handler.get_interrupt_reason(transcript, False)
        
        if not should_ignore:
            test_log.test_pass(
                f"Passive affirmation responded: '{transcript}'",
                f"{description} - Reason: {reason}"
            )
        else:
            test_log.test_fail(
                f"Passive affirmation responded: '{transcript}'",
                "INTERRUPT (should_ignore=False)",
                f"IGNORE (should_ignore=True)"
            )
            all_pass = False
    
    return all_pass


def test_scenario_3_correction():
    """Scenario: Agent is speaking, user says words with semantic content."""
    test_log.section("SCENARIO 3: The Correction (Semantic Interruption)")
    
    handler = InterruptionHandlerStandalone()
    
    test_cases = [
        ("no stop", True, "contains command word 'stop'"),
        ("wait", True, "contains command word 'wait'"),
        ("stop", True, "single command word"),
        ("no", True, "explicit negation"),
        ("stop please", True, "command with politeness marker"),
    ]
    
    test_log.log("INFO", "Agent State: SPEAKING")
    test_log.log("INFO", "Expectation: All utterances with semantic content should INTERRUPT")
    test_log.log("", "")
    
    all_pass = True
    for transcript, _, description in test_cases:
        should_ignore = handler.should_ignore_interrupt(
            transcript=transcript,
            agent_is_speaking=True
        )
        reason = handler.get_interrupt_reason(transcript, True)
        
        if not should_ignore:
            test_log.test_pass(
                f"Semantic content interrupts: '{transcript}'",
                f"{description} - Reason: {reason}"
            )
        else:
            test_log.test_fail(
                f"Semantic content interrupts: '{transcript}'",
                "INTERRUPT (should_ignore=False)",
                f"IGNORE (should_ignore=True)"
            )
            all_pass = False
    
    return all_pass


def test_scenario_4_mixed_input():
    """Scenario: Agent is speaking, user says filler + semantic words."""
    test_log.section("SCENARIO 4: The Mixed Input (Filler + Semantic)")
    
    handler = InterruptionHandlerStandalone()
    
    test_cases = [
        ("yeah okay but wait", True, "filler words + semantic content"),
        ("yeah wait a second", True, "backchannel + command"),
        ("ok so stop", True, "ok (filler) + stop (semantic)"),
        ("yeah hmm no", True, "multiple fillers + negation"),
    ]
    
    test_log.log("INFO", "Agent State: SPEAKING")
    test_log.log("INFO", "Expectation: Mixed inputs with ANY semantic content should INTERRUPT")
    test_log.log("", "")
    
    all_pass = True
    for transcript, _, description in test_cases:
        should_ignore = handler.should_ignore_interrupt(
            transcript=transcript,
            agent_is_speaking=True
        )
        reason = handler.get_interrupt_reason(transcript, True)
        
        if not should_ignore:
            test_log.test_pass(
                f"Mixed content interrupts: '{transcript}'",
                f"{description} - Reason: {reason}"
            )
        else:
            test_log.test_fail(
                f"Mixed content interrupts: '{transcript}'",
                "INTERRUPT (should_ignore=False)",
                f"IGNORE (should_ignore=True)"
            )
            all_pass = False
    
    return all_pass


def test_scenario_5_edge_cases():
    """Test edge cases and boundary conditions."""
    test_log.section("SCENARIO 5: Edge Cases and Boundary Conditions")
    
    handler = InterruptionHandlerStandalone()
    
    all_pass = True
    
    # Empty transcript
    should_ignore = handler.should_ignore_interrupt("", True)
    if not should_ignore:
        test_log.test_pass("Empty transcript", "Empty text does not trigger ignore")
    else:
        test_log.test_fail("Empty transcript", "False", "True")
        all_pass = False
    
    # Only punctuation
    should_ignore = handler.should_ignore_interrupt("...", True)
    if not should_ignore:
        test_log.test_pass("Punctuation only", "Punctuation-only text does not trigger ignore")
    else:
        test_log.test_fail("Punctuation only", "False", "True")
        all_pass = False
    
    # Case insensitivity
    should_ignore = handler.should_ignore_interrupt("YEAH OK HMM", True)
    if should_ignore:
        test_log.test_pass("Case insensitivity", "Uppercase filler words are recognized")
    else:
        test_log.test_fail("Case insensitivity", "True", "False")
        all_pass = False
    
    # Mixed case
    should_ignore = handler.should_ignore_interrupt("Yeah Ok Hmm", True)
    if should_ignore:
        test_log.test_pass("Mixed case", "Mixed-case filler words are recognized")
    else:
        test_log.test_fail("Mixed case", "True", "False")
        all_pass = False
    
    # Words with punctuation
    should_ignore = handler.should_ignore_interrupt("Yeah, okay! Hmm?", True)
    if should_ignore:
        test_log.test_pass(
            "Words with punctuation",
            "Filler words with punctuation are recognized"
        )
    else:
        test_log.test_fail("Words with punctuation", "True", "False")
        all_pass = False
    
    return all_pass


def test_scenario_6_state_transitions():
    """Test behavior during state transitions."""
    test_log.section("SCENARIO 6: State Transitions")
    
    handler = InterruptionHandlerStandalone()
    
    all_pass = True
    
    test_log.log("INFO", "User says 'yeah' while agent transitions listening -> speaking")
    
    should_ignore_listening = handler.should_ignore_interrupt(
        "yeah", agent_is_speaking=False
    )
    should_ignore_speaking = handler.should_ignore_interrupt(
        "yeah", agent_is_speaking=True
    )
    
    if not should_ignore_listening and should_ignore_speaking:
        test_log.test_pass(
            "State-dependent behavior",
            "Same word behaves differently based on agent state"
        )
    else:
        test_log.test_fail(
            "State-dependent behavior",
            "Different behavior for listening vs speaking",
            f"Got: listening={should_ignore_listening}, speaking={should_ignore_speaking}"
        )
        all_pass = False
    
    return all_pass


def main():
    """Run all test scenarios."""
    test_log.log("", "")
    test_log.log("", "╔" + "=" * 78 + "╗")
    test_log.log("", "║" + " " * 78 + "║")
    test_log.log("", "║" + "  LiveKit Interruption Handler - Test Suite".center(78) + "║")
    test_log.log("", "║" + "  Context-Aware Backchannel Handling".center(78) + "║")
    test_log.log("", "║" + " " * 78 + "║")
    test_log.log("", "╚" + "=" * 78 + "╝")
    
    results = []
    
    results.append(("Scenario 1: Long Explanation", test_scenario_1_long_explanation()))
    results.append(("Scenario 2: Passive Affirmation", test_scenario_2_passive_affirmation()))
    results.append(("Scenario 3: Correction", test_scenario_3_correction()))
    results.append(("Scenario 4: Mixed Input", test_scenario_4_mixed_input()))
    results.append(("Scenario 5: Edge Cases", test_scenario_5_edge_cases()))
    results.append(("Scenario 6: State Transitions", test_scenario_6_state_transitions()))
    
    # Print scenario results
    test_log.section("SCENARIO RESULTS")
    for scenario_name, passed in results:
        status = "PASSED ✓" if passed else "FAILED ✗"
        test_log.log("", f"  {scenario_name}: {status}")
    
    test_log.print_summary()
    
    # Save logs to file
    with open("/Users/mrinankjitsingh/Desktop/GenAI submission/agents-assignment/test_output.log", "w") as f:
        for log_line in test_log.logs:
            f.write(log_line + "\n")
    
    test_log.log("INFO", "Test logs saved to test_output.log")
    
    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
