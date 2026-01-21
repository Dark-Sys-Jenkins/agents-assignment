"""
Test Script for Intelligent Interruption Handler

This script contains unit tests and demonstrations of the interruption handler
functionality. It tests all scenarios required by the assignment.
"""

import logging
import os

# Read and execute the handler file directly to avoid dependency issues
handler_path = os.path.join(
    os.path.dirname(__file__), 
    'livekit-agents/livekit/agents/voice/interruption_handler.py'
)

with open(handler_path, 'r') as f:
    handler_code = f.read()

exec(handler_code)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_decision(test_name: str, decision, user_input: str, agent_speaking: bool):
    """Pretty print a test decision."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"User Input: '{user_input}'")
    print(f"Agent Speaking: {agent_speaking}")
    print(f"Should Interrupt: {decision.should_interrupt}")
    print(f"Reason: {decision.reason}")
    if decision.matched_words:
        print(f"Matched Words: {decision.matched_words}")
    print(f"{'='*70}\n")


def test_scenario_1_long_explanation():
    """
    Scenario 1: The Long Explanation
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Result: Agent audio does not break. It ignores the user input completely.
    """
    print("\n" + "SCENARIO 1: THE LONG EXPLANATION".center(70))
    
    handler = IntelligentInterruptionHandler()
    
    # Test various backchanneling inputs while agent is speaking
    test_cases = [
        "yeah",
        "ok",
        "okay yeah",
        "hmm",
        "uh-huh",
        "yeah ok hmm",
        "right okay",
        "mmm uh-huh yeah",
    ]
    
    for user_input in test_cases:
        decision = handler.should_interrupt(user_input, agent_speaking=True)
        print_decision(
            f"Backchannel: '{user_input}'",
            decision,
            user_input,
            agent_speaking=True
        )
        
        # Assert that none of these should interrupt
        assert not decision.should_interrupt, \
            f"FAIL: '{user_input}' should NOT interrupt when agent is speaking"
    
    print("[PASS] SCENARIO 1: All backchanneling ignored while agent speaking\n")


def test_scenario_2_passive_affirmation():
    """
    Scenario 2: The Passive Affirmation
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Result: Agent processes "Yeah" as an answer and proceeds.
    """
    print("\n" + "SCENARIO 2: THE PASSIVE AFFIRMATION".center(70))
    
    handler = IntelligentInterruptionHandler()
    
    # Test same words but when agent is NOT speaking
    test_cases = [
        "yeah",
        "ok",
        "sure",
        "yes",
        "yep",
    ]
    
    for user_input in test_cases:
        decision = handler.should_interrupt(user_input, agent_speaking=False)
        print_decision(
            f"Response when silent: '{user_input}'",
            decision,
            user_input,
            agent_speaking=False
        )
        
        # Assert that these SHOULD be processed as valid input
        assert decision.should_interrupt, \
            f"FAIL: '{user_input}' SHOULD be processed when agent is silent"
    
    print("[PASS] SCENARIO 2: All inputs processed when agent is silent\n")


def test_scenario_3_the_correction():
    """
    Scenario 3: The Correction
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Result: Agent cuts off immediately.
    """
    print("\n" + "SCENARIO 3: THE CORRECTION".center(70))
    
    handler = IntelligentInterruptionHandler()
    
    # Test interrupt commands while agent is speaking
    test_cases = [
        "no",
        "stop",
        "wait",
        "no stop",
        "hold on",
        "wait a second",
        "pause",
    ]
    
    for user_input in test_cases:
        decision = handler.should_interrupt(user_input, agent_speaking=True)
        print_decision(
            f"Interrupt command: '{user_input}'",
            decision,
            user_input,
            agent_speaking=True
        )
        
        # Assert that these SHOULD interrupt
        assert decision.should_interrupt, \
            f"FAIL: '{user_input}' SHOULD interrupt when agent is speaking"
    
    print("[PASS] SCENARIO 3: All interrupt commands stop the agent\n")


def test_scenario_4_mixed_input():
    """
    Scenario 4: The Mixed Input
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Result: Agent stops (because "but wait" is not in the ignore list).
    """
    print("\n" + "SCENARIO 4: THE MIXED INPUT".center(70))
    
    handler = IntelligentInterruptionHandler()
    
    # Test mixed inputs (acknowledgement + actual content)
    test_cases = [
        ("yeah okay but wait", True, "contains 'wait'"),
        ("ok but I have a question", True, "contains actual content"),
        ("hmm actually no", True, "contains 'no'"),
        ("yeah I think", True, "contains actual content"),
        ("right but hold on", True, "contains 'hold on'"),
    ]
    
    for user_input, should_interrupt, reason in test_cases:
        decision = handler.should_interrupt(user_input, agent_speaking=True)
        print_decision(
            f"Mixed input: '{user_input}' ({reason})",
            decision,
            user_input,
            agent_speaking=True
        )
        
        # Assert based on expected behavior
        assert decision.should_interrupt == should_interrupt, \
            f"FAIL: '{user_input}' interrupt decision should be {should_interrupt}"
    
    print("[PASS] SCENARIO 4: Mixed inputs handled correctly\n")


def test_edge_cases():
    """Test edge cases and special scenarios."""
    print("\n" + "EDGE CASES".center(70))
    
    handler = IntelligentInterruptionHandler()
    
    # Test empty input
    decision = handler.should_interrupt("", agent_speaking=True)
    print_decision("Empty input", decision, "", True)
    assert not decision.should_interrupt, "Empty input should not interrupt"
    
    # Test whitespace only
    decision = handler.should_interrupt("   ", agent_speaking=True)
    print_decision("Whitespace only", decision, "   ", True)
    assert not decision.should_interrupt, "Whitespace should not interrupt"
    
    # Test with punctuation
    decision = handler.should_interrupt("yeah!", agent_speaking=True)
    print_decision("With punctuation", decision, "yeah!", True)
    assert not decision.should_interrupt, "Should handle punctuation"
    
    # Test case insensitivity
    decision = handler.should_interrupt("YEAH OK", agent_speaking=True)
    print_decision("Uppercase", decision, "YEAH OK", True)
    assert not decision.should_interrupt, "Should be case-insensitive"
    
    print("[PASS] EDGE CASES\n")


def test_custom_configuration():
    """Test custom configuration."""
    print("\n" + "CUSTOM CONFIGURATION".center(70))
    
    # Create custom config
    config = InterruptionConfig(
        ignore_words=["yeah", "ok"],
        interrupt_words=["stop", "wait"],
        case_sensitive=False
    )
    
    handler = IntelligentInterruptionHandler(config=config)
    
    # Test that custom words work
    decision = handler.should_interrupt("yeah", agent_speaking=True)
    assert not decision.should_interrupt, "Custom ignore word should work"
    print_decision("Custom ignore word", decision, "yeah", True)
    
    decision = handler.should_interrupt("stop", agent_speaking=True)
    assert decision.should_interrupt, "Custom interrupt word should work"
    print_decision("Custom interrupt word", decision, "stop", True)
    
    # Test adding words dynamically
    handler.add_ignore_words(["sure", "gotcha"])
    decision = handler.should_interrupt("sure", agent_speaking=True)
    assert not decision.should_interrupt, "Dynamically added word should work"
    print_decision("Dynamically added ignore word", decision, "sure", True)
    
    print("[PASS] CUSTOM CONFIGURATION\n")


def test_disabled_handler():
    """Test handler when disabled."""
    print("\n" + "DISABLED HANDLER".center(70))
    
    handler = IntelligentInterruptionHandler(enabled=False)
    
    # When disabled, everything should interrupt
    decision = handler.should_interrupt("yeah", agent_speaking=True)
    assert decision.should_interrupt, "Disabled handler should always interrupt"
    print_decision("Disabled handler", decision, "yeah", True)
    
    # Enable it
    handler.enabled = True
    decision = handler.should_interrupt("yeah", agent_speaking=True)
    assert not decision.should_interrupt, "Enabled handler should filter"
    print_decision("Re-enabled handler", decision, "yeah", True)
    
    print("[PASS] DISABLED HANDLER\n")


def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*70)
    print("INTELLIGENT INTERRUPTION HANDLER - TEST SUITE".center(70))
    print("="*70 + "\n")
    
    try:
        test_scenario_1_long_explanation()
        test_scenario_2_passive_affirmation()
        test_scenario_3_the_correction()
        test_scenario_4_mixed_input()
        test_edge_cases()
        test_custom_configuration()
        test_disabled_handler()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED!".center(70))
        print("="*70 + "\n")
        
        print("Summary:")
        print("  [PASS] Scenario 1: Long Explanation - PASSED")
        print("  [PASS] Scenario 2: Passive Affirmation - PASSED")
        print("  [PASS] Scenario 3: The Correction - PASSED")
        print("  [PASS] Scenario 4: Mixed Input - PASSED")
        print("  [PASS] Edge Cases - PASSED")
        print("  [PASS] Custom Configuration - PASSED")
        print("  [PASS] Disabled Handler - PASSED")
        print()
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
