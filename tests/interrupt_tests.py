"""
Comprehensive test suite for LiveKit intelligent interruption handling.

Tests cover:
- Basic backchannel detection
- State awareness (speaking vs silent)
- Command detection
- Mixed input handling
- Edge cases
- Performance benchmarks
"""

import sys
import time
from typing import List, Tuple
sys.path.insert(0, '../livekit-agents')

import importlib.util
# Import the interruption handler
# Load the file directly using the CORRECT spelling (single 't')
spec = importlib.util.spec_from_file_location(
    "intterrupt_audio_backend",
    "../livekit-agents/livekit/agents/voice/intterrupt_audio_backend.py"
)
interrupt_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interrupt_module)

InterruptionHandler = interrupt_module.InterruptionHandler
InterruptionSettings = interrupt_module.InterruptionSettings
InterruptionReason = interrupt_module.InterruptionReason


class TestResult:
    """Track test execution results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.failures: List[Tuple[str, bool, bool]] = []
    
    def record(self, name: str, result: bool, expected: bool) -> bool:
        """Record a test result."""
        self.total += 1
        success = result == expected
        
        if success:
            self.passed += 1
            status = "✓ PASS"
        else:
            self.failed += 1
            status = "✗ FAIL"
            self.failures.append((name, result, expected))
        
        print(f"{status:<8} | {name}")
        print(f"          expected={expected}, got={result}\n")
        
        return success
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print(f"TEST SUMMARY: {self.passed}/{self.total} PASSED")
        
        if self.failed > 0:
            print(f"\n{self.failed} FAILURES:")
            for name, result, expected in self.failures:
                print(f"  • {name}: got {result}, expected {expected}")
        
        print("=" * 70)
        
        return self.failed == 0


def test_basic_backchannels():
    """Test basic backchannel word detection while speaking."""
    print("\n" + "=" * 70)
    print("TEST SUITE 1: Basic Backchannels (Agent Speaking)")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    test_cases = [
        ("Single 'yeah'", "yeah", True),
        ("Single 'ok'", "ok", True),
        ("Single 'okay'", "okay", True),
        ("Single 'hmm'", "hmm", True),
        ("Single 'mhm'", "mhm", True),
        ("Single 'uh-huh'", "uh-huh", True),
        ("Single 'right'", "right", True),
        ("Single 'sure'", "sure", True),
        ("Single 'exactly'", "exactly", True),
        ("Single 'totally'", "totally", True),
        ("Multiple backchannels", "yeah okay hmm", True),
        ("Repeated backchannel", "yeah yeah yeah", True),
        ("Mixed backchannels", "ok right uh-huh", True),
        ("Backchannel phrase", "i see", True),
        ("Backchannel phrase 2", "got it", True),
        ("Backchannel phrase 3", "makes sense", True),
    ]
    
    for name, text, expected in test_cases:
        result = handler.should_ignore_interrupt(text, is_speaking=True)
        results.record(name, result, expected)
    
    return results


def test_state_awareness():
    """Test that same input behaves differently based on agent state."""
    print("\n" + "=" * 70)
    print("TEST SUITE 2: State Awareness (Speaking vs Silent)")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    # These should be ignored while speaking, processed while silent
    test_inputs = ["yeah", "ok", "hmm", "right", "got it", "i see"]
    
    for text in test_inputs:
        # While speaking: should ignore (True)
        name_speaking = f"'{text}' while SPEAKING"
        result_speaking = handler.should_ignore_interrupt(text, is_speaking=True)
        results.record(name_speaking, result_speaking, True)
        
        # While silent: should NOT ignore (False)
        name_silent = f"'{text}' while SILENT"
        result_silent = handler.should_ignore_interrupt(text, is_speaking=False)
        results.record(name_silent, result_silent, False)
    
    return results


def test_explicit_commands():
    """Test that explicit commands always interrupt."""
    print("\n" + "=" * 70)
    print("TEST SUITE 3: Explicit Commands (Always Interrupt)")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    # These should NEVER be ignored, regardless of agent state
    commands = [
        "stop", "wait", "no", "pause", "hold on",
        "hold up", "hang on", "wait a minute",
        "actually", "but", "however", "listen",
        "what", "why", "how", "when", "where",
        "can you", "could you", "i want", "i need",
        "let me", "question", "excuse me"
    ]
    
    for cmd in commands:
        # While speaking: should NOT ignore (False)
        name_speaking = f"'{cmd}' while SPEAKING"
        result_speaking = handler.should_ignore_interrupt(cmd, is_speaking=True)
        results.record(name_speaking, result_speaking, False)
        
        # While silent: should NOT ignore (False)
        name_silent = f"'{cmd}' while SILENT"
        result_silent = handler.should_ignore_interrupt(cmd, is_speaking=False)
        results.record(name_silent, result_silent, False)
    
    return results


def test_mixed_inputs():
    """Test inputs containing both backchannels and commands."""
    print("\n" + "=" * 70)
    print("TEST SUITE 4: Mixed Backchannel + Command")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    # Command present → should interrupt (False)
    test_cases = [
        ("yeah but wait", "yeah but wait", False),
        ("ok hmm stop", "ok hmm stop", False),
        ("yeah no", "yeah no", False),
        ("okay so wait", "okay so wait", False),
        ("hmm actually", "hmm actually", False),
        ("right but", "right but", False),
        ("ok what", "ok what", False),
        ("yeah i want", "yeah i want", False),
        ("got it but hold on", "got it but hold on", False),
    ]
    
    for name, text, expected in test_cases:
        result = handler.should_ignore_interrupt(text, is_speaking=True)
        results.record(name, result, expected)
    
    return results


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n" + "=" * 70)
    print("TEST SUITE 5: Edge Cases")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    test_cases = [
        ("Empty string", "", False),
        ("Whitespace only", "   ", False),
        ("Punctuation only", "...", False),
        ("Single character", "a", False),
        ("Numbers", "123", False),
        ("Uppercase backchannel", "YEAH", True),  # Should be normalized
        ("Mixed case", "YeAh OkAy", True),
        ("Extra whitespace", "  yeah   ok  ", True),
        ("With punctuation", "yeah!", True),
        ("With commas", "yeah, ok, hmm", True),
        ("Trailing punctuation", "got it.", True),
        ("Question mark", "really?", True),  # 'really' is backchannel
        ("Multiple spaces", "yeah  ok", True),
        ("Newlines", "yeah\nok", True),
        ("Tabs", "yeah\tok", True),
    ]
    
    for name, text, expected in test_cases:
        result = handler.should_ignore_interrupt(text, is_speaking=True)
        results.record(name, result, expected)
    
    return results


def test_real_world_scenarios():
    """Test realistic conversation scenarios."""
    print("\n" + "=" * 70)
    print("TEST SUITE 6: Real-World Scenarios")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    results = TestResult()
    
    scenarios = [
        # Scenario 1: Long explanation with backchannels
        ("Long explanation context",
         [("Okay", True), ("yeah", True), ("uh-huh", True), ("right", True)]),
        
        # Scenario 2: Correction attempt
        ("Correction attempt",
         [("wait", False), ("no stop", False), ("actually", False)]),
        
        # Scenario 3: Mixed acknowledgment with question
        ("Question during explanation",
         [("yeah", True), ("hmm", True), ("but what about", False)]),
        
        # Scenario 4: Genuine interest signals
        ("Interest signals",
         [("oh really", True), ("interesting", True), ("wow", True)]),
        
        # Scenario 5: Topic redirect
        ("Topic change",
         [("anyway", False), ("by the way", False), ("speaking of", False)]),
    ]
    
    for scenario_name, test_cases in scenarios:
        print(f"\n  Scenario: {scenario_name}")
        for text, expected in test_cases:
            result = handler.should_ignore_interrupt(text, is_speaking=True)
            results.record(f"  {text}", result, expected)
    
    return results


def test_performance():
    """Benchmark performance for real-time requirements."""
    print("\n" + "=" * 70)
    print("TEST SUITE 7: Performance Benchmarks")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    
    test_inputs = [
        "yeah",
        "ok hmm right",
        "wait a minute",
        "yeah but actually i want to ask something",
    ]
    
    iterations = 10000
    
    for text in test_inputs:
        start = time.perf_counter()
        
        for _ in range(iterations):
            handler.should_ignore_interrupt(text, is_speaking=True)
        
        end = time.perf_counter()
        avg_time_ms = ((end - start) / iterations) * 1000
        
        print(f"Input: '{text}'")
        print(f"  Average time: {avg_time_ms:.4f}ms per call")
        print(f"  {'✓ PASS' if avg_time_ms < 1.0 else '✗ FAIL'} (<1ms requirement)")
        print()
    
    print("Real-time requirement: <1ms per decision")


def test_explain_decision():
    """Test the explain_decision method for debugging."""
    print("\n" + "=" * 70)
    print("TEST SUITE 8: Decision Explanations")
    print("=" * 70)
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    
    test_cases = [
        ("yeah", True),
        ("stop", True),
        ("yeah but wait", True),
        ("", True),
    ]
    
    for text, is_speaking in test_cases:
        should_ignore, reason, explanation = handler.explain_decision(text, is_speaking)
        print(f"\nInput: '{text}' | Agent speaking: {is_speaking}")
        print(f"  Decision: {'IGNORE' if should_ignore else 'INTERRUPT'}")
        print(f"  Reason: {reason.value}")
        print(f"  Explanation: {explanation}")


def demonstrate_state_awareness():
    """Visual demonstration of state-dependent behavior."""
    print("\n" + "=" * 70)
    print("STATE AWARENESS DEMONSTRATION")
    print("=" * 70)
    print("\n🎯 Same Input, Different States:\n")
    
    handler = InterruptionHandler(InterruptionSettings(debug=False))
    
    test_inputs = ["yeah", "okay", "no stop", "wait", "got it"]
    
    for text in test_inputs:
        print(f"Input: '{text}'")
        print("-" * 70)
        
        # Agent speaking
        result_speaking = handler.should_ignore_interrupt(text, is_speaking=True)
        _, reason_speaking, _ = handler.explain_decision(text, is_speaking=True)
        print(f"  Agent SPEAKING: {'IGNORE' if result_speaking else 'INTERRUPT':10} | {reason_speaking.value}")
        
        # Agent silent
        result_silent = handler.should_ignore_interrupt(text, is_speaking=False)
        _, reason_silent, _ = handler.explain_decision(text, is_speaking=False)
        print(f"  Agent SILENT:   {'IGNORE' if result_silent else 'INTERRUPT':10} | {reason_silent.value}")
        
        # Highlight state dependency
        if result_speaking != result_silent:
            print(f"  ⚠️  STATE-DEPENDENT: Behavior changes based on agent state")
        else:
            print(f"  ✓  STATE-INDEPENDENT: Consistent behavior")
        print()


def main():
    """Run all test suites."""
    print("\n" + "=" * 70)
    print("LIVEKIT INTELLIGENT INTERRUPTION HANDLING - TEST SUITE")
    print("=" * 70)
    
    all_results = TestResult()
    
    # Run all test suites
    suites = [
        test_basic_backchannels,
        test_state_awareness,
        test_explicit_commands,
        test_mixed_inputs,
        test_edge_cases,
        test_real_world_scenarios,
    ]
    
    for suite in suites:
        suite_result = suite()
        all_results.passed += suite_result.passed
        all_results.failed += suite_result.failed
        all_results.total += suite_result.total
        all_results.failures.extend(suite_result.failures)
    
    # Performance tests
    test_performance()
    
    # Explanation tests
    test_explain_decision()
    
    # State awareness demo
    demonstrate_state_awareness()
    
    # Final summary
    all_passed = all_results.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())