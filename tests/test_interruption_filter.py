"""
Test Suite for Context-Aware Interruption Filter

This module tests all scenarios defined in the challenge:
1. Scenario 1: The Long Explanation
2. Scenario 2: The Passive Affirmation
3. Scenario 3: The Correction
4. Scenario 4: The Mixed Input

Plus additional edge cases and state management tests.
"""

import asyncio
import logging
import sys
from datetime import datetime
from io import StringIO

from livekit.agents.voice.interruption_filter import (
    ContextAwareInterruptionFilter,
    FilterDecision,
    InterruptionType,
)


# Configure test logging
class TestLogger:
    """Custom logger for test case execution."""
    
    def __init__(self):
        self.records: list[str] = []
        self.start_time = datetime.now()
    
    def log(self, level: str, message: str) -> None:
        """Log a message with timestamp."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = f"[{elapsed:06.2f}s]"
        record = f"{timestamp} [{level:8s}] {message}"
        self.records.append(record)
        print(record)
    
    def info(self, message: str) -> None:
        self.log("INFO", message)
    
    def error(self, message: str) -> None:
        self.log("ERROR", message)
    
    def success(self, message: str) -> None:
        self.log("SUCCESS", message)
    
    def test_start(self, test_name: str) -> None:
        self.log("TEST", f"━━━ START: {test_name} ━━━")
    
    def test_end(self, test_name: str, passed: bool) -> None:
        status = "✓ PASSED" if passed else "✗ FAILED"
        self.log("TEST", f"━━━ END: {test_name} - {status} ━━━\n")
    
    def get_logs(self) -> str:
        return "\n".join(self.records)


test_logger = TestLogger()


class TestResult:
    """Container for test results."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.assertions_made = 0
        self.assertions_passed = 0
        self.error_message = ""
        self.decisions_evaluated: list[FilterDecision] = []
    
    def assert_equal(self, actual, expected, message: str = "") -> bool:
        """Assert that actual equals expected."""
        self.assertions_made += 1
        if actual == expected:
            self.assertions_passed += 1
            test_logger.info(f"✓ Assert passed: {message}")
            return True
        else:
            test_logger.error(
                f"✗ Assert failed: {message} | Expected: {expected}, Got: {actual}"
            )
            self.error_message = (
                f"Expected {expected}, but got {actual}"
            )
            return False
    
    def assert_true(self, condition: bool, message: str = "") -> bool:
        """Assert that condition is true."""
        self.assertions_made += 1
        if condition:
            self.assertions_passed += 1
            test_logger.info(f"✓ Assert passed: {message}")
            return True
        else:
            test_logger.error(f"✗ Assert failed: {message}")
            self.error_message = message
            return False
    
    def finalize(self) -> bool:
        """Finalize the test result."""
        self.passed = (self.assertions_passed == self.assertions_made)
        return self.passed


def scenario_1_long_explanation() -> TestResult:
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uhhhh" while Agent is talking.
    Expected: Agent audio does not break (IGNORE filler words).
    """
    result = TestResult("Scenario 1: The Long Explanation")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # Simulate user providing filler words while agent is speaking
    filler_inputs = [
        "Okay",
        "Yeah",
        "Uhhhh",
        "Okay yeah",
        "Yeah okay uhhhh"
    ]
    
    for filler in filler_inputs:
        decision = filter_obj.evaluate(
            transcript=filler,
            is_agent_speaking=True,
            is_agent_playing_audio=True
        )
        result.decisions_evaluated.append(decision)
        
        test_logger.info(f"Evaluating: '{filler}' → {decision}")
        result.assert_equal(
            decision.decision_type,
            InterruptionType.IGNORE,
            f"Filler word '{filler}' should be ignored"
        )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def scenario_2_passive_affirmation() -> TestResult:
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Expected: Agent processes "Yeah" as valid input (RESPOND).
    """
    result = TestResult("Scenario 2: The Passive Affirmation")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # Agent is silent (not speaking, not playing)
    decision = filter_obj.evaluate(
        transcript="Yeah",
        is_agent_speaking=False,
        is_agent_playing_audio=False
    )
    result.decisions_evaluated.append(decision)
    
    test_logger.info(f"Evaluating: 'Yeah' (agent silent) → {decision}")
    result.assert_equal(
        decision.decision_type,
        InterruptionType.RESPOND,
        "When agent is silent, 'Yeah' should be treated as valid input (RESPOND)"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def scenario_3_the_correction() -> TestResult:
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Expected: Agent cuts off immediately (INTERRUPT).
    """
    result = TestResult("Scenario 3: The Correction")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    decision = filter_obj.evaluate(
        transcript="No stop",
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    result.decisions_evaluated.append(decision)
    
    test_logger.info(f"Evaluating: 'No stop' → {decision}")
    result.assert_equal(
        decision.decision_type,
        InterruptionType.INTERRUPT,
        "'No stop' should trigger immediate interruption"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def scenario_4_mixed_input() -> TestResult:
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Expected: Agent stops because "but wait" contains semantic interruption signal.
    """
    result = TestResult("Scenario 4: The Mixed Input")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    decision = filter_obj.evaluate(
        transcript="Yeah okay but wait",
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    result.decisions_evaluated.append(decision)
    
    test_logger.info(f"Evaluating: 'Yeah okay but wait' → {decision}")
    result.assert_equal(
        decision.decision_type,
        InterruptionType.INTERRUPT,
        "'Yeah okay but wait' contains 'but' which indicates interruption intent"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_configurable_ignore_list() -> TestResult:
    """Test that the ignore list is configurable."""
    result = TestResult("Configurable Ignore List")
    test_logger.test_start(result.test_name)
    
    # Create filter with custom ignore list
    custom_ignore = {"hello", "hi", "hey"}
    filter_obj = ContextAwareInterruptionFilter(ignore_list=custom_ignore)
    
    # Test custom word
    decision = filter_obj.evaluate(
        transcript="Hello",
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    result.decisions_evaluated.append(decision)
    
    test_logger.info(f"Custom ignore list test: 'Hello' → {decision}")
    result.assert_equal(
        decision.decision_type,
        InterruptionType.IGNORE,
        "Custom ignore list should work"
    )
    
    # Test add to ignore list
    filter_obj.add_to_ignore_list(["custom", "word"])
    test_logger.info("Added 'custom' and 'word' to ignore list")
    
    decision2 = filter_obj.evaluate(
        transcript="custom",
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    result.decisions_evaluated.append(decision2)
    
    test_logger.info(f"After adding: 'custom' → {decision2}")
    result.assert_equal(
        decision2.decision_type,
        InterruptionType.IGNORE,
        "Dynamically added word should be ignored"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_state_based_filtering() -> TestResult:
    """Test that filtering only applies when agent is active."""
    result = TestResult("State-Based Filtering")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # Test 1: Agent speaking - should ignore filler
    decision1 = filter_obj.evaluate(
        transcript="Yeah",
        is_agent_speaking=True,
        is_agent_playing_audio=False
    )
    result.decisions_evaluated.append(decision1)
    test_logger.info(f"Agent speaking, input 'Yeah' → {decision1}")
    result.assert_equal(
        decision1.decision_type,
        InterruptionType.IGNORE,
        "Filler should be ignored when agent speaking"
    )
    
    # Test 2: Agent playing audio - should ignore filler
    decision2 = filter_obj.evaluate(
        transcript="Yeah",
        is_agent_speaking=False,
        is_agent_playing_audio=True
    )
    result.decisions_evaluated.append(decision2)
    test_logger.info(f"Agent playing audio, input 'Yeah' → {decision2}")
    result.assert_equal(
        decision2.decision_type,
        InterruptionType.IGNORE,
        "Filler should be ignored when agent playing audio"
    )
    
    # Test 3: Agent silent - should respond to filler
    decision3 = filter_obj.evaluate(
        transcript="Yeah",
        is_agent_speaking=False,
        is_agent_playing_audio=False
    )
    result.decisions_evaluated.append(decision3)
    test_logger.info(f"Agent silent, input 'Yeah' → {decision3}")
    result.assert_equal(
        decision3.decision_type,
        InterruptionType.RESPOND,
        "Filler should be responded to when agent silent"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_semantic_interruption() -> TestResult:
    """Test semantic interruption detection for mixed inputs."""
    result = TestResult("Semantic Interruption Detection")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    semantic_inputs = [
        ("Yeah I have a question", InterruptionType.INTERRUPT),
        ("Yeah but I want to say", InterruptionType.INTERRUPT),
        ("OK actually wait", InterruptionType.INTERRUPT),
        ("Yeah let me tell you", InterruptionType.INTERRUPT),
    ]
    
    for transcript, expected_type in semantic_inputs:
        decision = filter_obj.evaluate(
            transcript=transcript,
            is_agent_speaking=True,
            is_agent_playing_audio=True
        )
        result.decisions_evaluated.append(decision)
        
        test_logger.info(f"Semantic test: '{transcript}' → {decision}")
        result.assert_equal(
            decision.decision_type,
            expected_type,
            f"'{transcript}' should be {expected_type.value}"
        )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_strong_interrupt_words() -> TestResult:
    """Test that strong interrupt commands override ignore list."""
    result = TestResult("Strong Interrupt Words Override")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    strong_commands = [
        "stop",
        "wait",
        "hold on",
        "pause",
        "no wait",
        "hold it",
        "shut up",
    ]
    
    for command in strong_commands:
        decision = filter_obj.evaluate(
            transcript=command,
            is_agent_speaking=True,
            is_agent_playing_audio=True
        )
        result.decisions_evaluated.append(decision)
        
        test_logger.info(f"Strong command test: '{command}' → {decision}")
        result.assert_equal(
            decision.decision_type,
            InterruptionType.INTERRUPT,
            f"Strong command '{command}' should always interrupt"
        )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_decision_history() -> TestResult:
    """Test that decision history is tracked correctly."""
    result = TestResult("Decision History Tracking")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # Make several decisions
    filter_obj.evaluate("Yeah", is_agent_speaking=True, is_agent_playing_audio=True)
    filter_obj.evaluate("Stop", is_agent_speaking=True, is_agent_playing_audio=True)
    filter_obj.evaluate("Okay", is_agent_speaking=False, is_agent_playing_audio=False)
    
    history = filter_obj.get_decision_history()
    test_logger.info(f"Decision history size: {len(history)}")
    
    result.assert_equal(
        len(history),
        3,
        "Should have 3 decisions in history"
    )
    
    # Verify types in order
    result.assert_equal(
        history[0].decision_type,
        InterruptionType.IGNORE,
        "First decision should be IGNORE"
    )
    result.assert_equal(
        history[1].decision_type,
        InterruptionType.INTERRUPT,
        "Second decision should be INTERRUPT"
    )
    result.assert_equal(
        history[2].decision_type,
        InterruptionType.RESPOND,
        "Third decision should be RESPOND"
    )
    
    # Test clearing history
    filter_obj.clear_history()
    new_history = filter_obj.get_decision_history()
    test_logger.info("Cleared history")
    
    result.assert_equal(
        len(new_history),
        0,
        "History should be empty after clear"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_normalization() -> TestResult:
    """Test that text normalization works correctly."""
    result = TestResult("Text Normalization")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # These should all be treated the same (as "Yeah")
    variations = [
        "Yeah",
        "YEAH",
        "Yeah!",
        "Yeah?",
        "Yeah...",
        "  Yeah  ",
    ]
    
    for variation in variations:
        decision = filter_obj.evaluate(
            transcript=variation,
            is_agent_speaking=True,
            is_agent_playing_audio=True
        )
        result.decisions_evaluated.append(decision)
        
        test_logger.info(f"Normalization test: '{variation}' → {decision.decision_type}")
        result.assert_equal(
            decision.decision_type,
            InterruptionType.IGNORE,
            f"Variation '{variation}' should be normalized and ignored"
        )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def test_edge_cases() -> TestResult:
    """Test various edge cases."""
    result = TestResult("Edge Cases")
    test_logger.test_start(result.test_name)
    
    filter_obj = ContextAwareInterruptionFilter()
    
    # Empty string
    decision1 = filter_obj.evaluate(
        transcript="",
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    test_logger.info(f"Empty string test → {decision1}")
    result.assert_true(
        decision1.decision_type in [InterruptionType.IGNORE, InterruptionType.RESPOND],
        "Empty string should not crash"
    )
    
    # Very long filler
    long_filler = "Yeah yeah yeah yeah yeah"
    decision2 = filter_obj.evaluate(
        transcript=long_filler,
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    test_logger.info(f"Long filler test → {decision2}")
    result.assert_equal(
        decision2.decision_type,
        InterruptionType.IGNORE,
        "Repeated filler words should be ignored"
    )
    
    # Mixed case with numbers
    mixed = "Yeah 123 okay"
    decision3 = filter_obj.evaluate(
        transcript=mixed,
        is_agent_speaking=True,
        is_agent_playing_audio=True
    )
    test_logger.info(f"Mixed content test: '{mixed}' → {decision3}")
    result.assert_equal(
        decision3.decision_type,
        InterruptionType.IGNORE,
        "Mixed content with only filler words should be ignored"
    )
    
    test_logger.test_end(result.test_name, result.finalize())
    return result


def run_all_tests() -> dict:
    """Run all tests and return results."""
    test_logger.info("=" * 80)
    test_logger.info("STARTING COMPREHENSIVE TEST SUITE FOR INTERRUPTION FILTER")
    test_logger.info("=" * 80 + "\n")
    
    test_functions = [
        scenario_1_long_explanation,
        scenario_2_passive_affirmation,
        scenario_3_the_correction,
        scenario_4_mixed_input,
        test_configurable_ignore_list,
        test_state_based_filtering,
        test_semantic_interruption,
        test_strong_interrupt_words,
        test_decision_history,
        test_normalization,
        test_edge_cases,
    ]
    
    results: list[TestResult] = []
    for test_func in test_functions:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            test_logger.error(f"Test {test_func.__name__} crashed: {e}")
            result = TestResult(test_func.__name__)
            result.error_message = str(e)
            results.append(result)
    
    # Print summary
    test_logger.info("=" * 80)
    test_logger.info("TEST SUMMARY")
    test_logger.info("=" * 80)
    
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    
    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        test_logger.info(
            f"{status} | {result.test_name} "
            f"({result.assertions_passed}/{result.assertions_made} assertions)"
        )
        if result.error_message:
            test_logger.info(f"      Error: {result.error_message}")
    
    test_logger.info("=" * 80)
    test_logger.success(f"RESULTS: {passed_count}/{total_count} tests passed")
    test_logger.info("=" * 80)
    
    return {
        "passed": passed_count,
        "total": total_count,
        "results": results,
        "logs": test_logger.get_logs(),
    }


if __name__ == "__main__":
    results = run_all_tests()
    
    # Write full logs to file
    log_file = "test_interruption_filter_logs.txt"
    with open(log_file, "w") as f:
        f.write(results["logs"])
    
    print(f"\n✓ Full test logs written to: {log_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results["passed"] == results["total"] else 1)
