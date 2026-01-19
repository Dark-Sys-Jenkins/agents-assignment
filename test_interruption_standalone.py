"""
Standalone test for intelligent interruption handling.

This test file demonstrates the behavior of the interruption handler
across all four test scenarios specified in the requirements.

NOTE: This is a standalone version that directly imports from the source files.
"""

import logging
import sys
from datetime import datetime

# Setup logging to capture detailed test output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_interruption_handler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import directly from the module we created
sys.path.insert(0, r'c:\Users\DELL\agents-assignment\livekit-agents')
from livekit.agents.voice.interruption_handler import InterruptionAnalyzer, BackchannelingConfig


def test_scenario_1_long_explanation():
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Result: Agent audio does not break. It ignores the user input completely.
    """
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 1: The Long Explanation")
    logger.info("=" * 80)
    logger.info("Context: Agent is reading a long paragraph about history")
    logger.info("User Action: User says 'Okay... yeah... uh-huh' while Agent is talking")
    logger.info("Expected Result: Agent audio does not break, interruption is IGNORED")
    logger.info("-" * 80)
    
    config = BackchannelingConfig()
    analyzer = InterruptionAnalyzer(config)
    
    # Scenario: Agent is speaking, user provides backchanneling
    transcript = "Okay yeah uh-huh"
    agent_is_speaking = True
    
    should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
    analysis = analyzer.get_analysis(transcript, agent_is_speaking)
    
    logger.info(f"Transcript: '{transcript}'")
    logger.info(f"Agent is speaking: {agent_is_speaking}")
    logger.info(f"Analysis:")
    logger.info(f"  - Words detected: {analysis['words']}")
    logger.info(f"  - Backchanneling words: {analysis['backchanneling_words']}")
    logger.info(f"  - Command words: {analysis['command_words']}")
    logger.info(f"  - Unknown words: {analysis['unknown_words']}")
    logger.info(f"Should ignore interruption: {should_ignore}")
    
    if should_ignore:
        logger.info("✓ TEST PASSED: Backchanneling was correctly filtered")
        logger.info("✓ Agent continues speaking without interruption")
        return True
    else:
        logger.error("✗ TEST FAILED: Backchanneling was not filtered")
        logger.error("✗ Agent would have stopped speaking")
        return False


def test_scenario_2_passive_affirmation():
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Result: Agent processes "Yeah" as an answer and proceeds.
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 2: The Passive Affirmation")
    logger.info("=" * 80)
    logger.info("Context: Agent asks 'Are you ready?' and goes silent")
    logger.info("User Action: User says 'Yeah.'")
    logger.info("Expected Result: Agent processes 'Yeah' as answer, interruption NOT IGNORED")
    logger.info("-" * 80)
    
    config = BackchannelingConfig()
    analyzer = InterruptionAnalyzer(config)
    
    # Scenario: Agent is NOT speaking, user provides simple affirmation
    transcript = "Yeah"
    agent_is_speaking = False
    
    should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
    analysis = analyzer.get_analysis(transcript, agent_is_speaking)
    
    logger.info(f"Transcript: '{transcript}'")
    logger.info(f"Agent is speaking: {agent_is_speaking}")
    logger.info(f"Analysis:")
    logger.info(f"  - Words detected: {analysis['words']}")
    logger.info(f"  - Backchanneling words: {analysis['backchanneling_words']}")
    logger.info(f"Should ignore interruption: {should_ignore}")
    
    if not should_ignore:
        logger.info("✓ TEST PASSED: Interruption was not filtered")
        logger.info("✓ Agent processes 'Yeah' as valid user input")
        return True
    else:
        logger.error("✗ TEST FAILED: Interruption was filtered when it shouldn't be")
        logger.error("✗ Agent ignored valid user input")
        return False


def test_scenario_3_correction():
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Result: Agent cuts off immediately.
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 3: The Correction")
    logger.info("=" * 80)
    logger.info("Context: Agent is counting 'One, two, three...'")
    logger.info("User Action: User says 'No stop.'")
    logger.info("Expected Result: Agent cuts off immediately, interruption NOT IGNORED")
    logger.info("-" * 80)
    
    config = BackchannelingConfig()
    analyzer = InterruptionAnalyzer(config)
    
    # Scenario: Agent is speaking, user provides command
    transcript = "No stop"
    agent_is_speaking = True
    
    should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
    analysis = analyzer.get_analysis(transcript, agent_is_speaking)
    
    logger.info(f"Transcript: '{transcript}'")
    logger.info(f"Agent is speaking: {agent_is_speaking}")
    logger.info(f"Analysis:")
    logger.info(f"  - Words detected: {analysis['words']}")
    logger.info(f"  - Command words: {analysis['command_words']}")
    logger.info(f"Should ignore interruption: {should_ignore}")
    
    if not should_ignore:
        logger.info("✓ TEST PASSED: Command was recognized and not filtered")
        logger.info("✓ Agent will interrupt and listen to the new command")
        return True
    else:
        logger.error("✗ TEST FAILED: Command was incorrectly filtered")
        logger.error("✗ Agent would continue speaking instead of stopping")
        return False


def test_scenario_4_mixed_input():
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Result: Agent stops (because "but wait" contains command word).
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SCENARIO 4: The Mixed Input")
    logger.info("=" * 80)
    logger.info("Context: Agent is speaking")
    logger.info("User Action: User says 'Yeah okay but wait.'")
    logger.info("Expected Result: Agent stops (contains command word), interruption NOT IGNORED")
    logger.info("-" * 80)
    
    config = BackchannelingConfig()
    analyzer = InterruptionAnalyzer(config)
    
    # Scenario: Agent is speaking, user provides mixed input with command
    transcript = "Yeah okay but wait"
    agent_is_speaking = True
    
    should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
    analysis = analyzer.get_analysis(transcript, agent_is_speaking)
    
    logger.info(f"Transcript: '{transcript}'")
    logger.info(f"Agent is speaking: {agent_is_speaking}")
    logger.info(f"Analysis:")
    logger.info(f"  - Words detected: {analysis['words']}")
    logger.info(f"  - Backchanneling words: {analysis['backchanneling_words']}")
    logger.info(f"  - Command words: {analysis['command_words']}")
    logger.info(f"Should ignore interruption: {should_ignore}")
    
    if not should_ignore:
        logger.info("✓ TEST PASSED: Mixed input with command was recognized")
        logger.info("✓ Agent will interrupt and listen to the new command")
        return True
    else:
        logger.error("✗ TEST FAILED: Mixed input was incorrectly filtered")
        logger.error("✗ Agent would continue speaking instead of stopping")
        return False


def test_edge_cases():
    """Test additional edge cases and variations."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST: Edge Cases and Variations")
    logger.info("=" * 80)
    logger.info("-" * 80)
    
    config = BackchannelingConfig()
    analyzer = InterruptionAnalyzer(config)
    
    test_cases = [
        # (transcript, agent_is_speaking, expected_ignore, description)
        ("uh", True, True, "Single filler word while agent speaking"),
        ("umm hmm", True, True, "Multiple filler words while agent speaking"),
        ("wait", True, False, "Single command word while agent speaking"),
        ("hold on", True, False, "Command phrase while agent speaking"),
        ("okay", False, False, "Backchanneling while agent silent (should NOT ignore)"),
        ("right", True, True, "Right as backchanneling"),
        ("wrong", True, False, "Wrong as unknown word (conservative - allow interruption)"),
        ("yeah I need help", True, False, "Mixed backchanneling + unknown words"),
        ("mm hmm sure", True, True, "All backchanneling words"),
        ("stop the music", True, False, "Command with extra words"),
    ]
    
    passed = 0
    failed = 0
    
    for transcript, agent_is_speaking, expected_ignore, description in test_cases:
        should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
        status = "✓ PASS" if should_ignore == expected_ignore else "✗ FAIL"
        
        if should_ignore == expected_ignore:
            passed += 1
        else:
            failed += 1
        
        logger.info(f"{status}: {description}")
        logger.info(f"  Transcript: '{transcript}' | Agent speaking: {agent_is_speaking}")
        logger.info(f"  Expected: {expected_ignore}, Got: {should_ignore}")
    
    logger.info("-" * 80)
    logger.info(f"Edge cases: {passed} passed, {failed} failed")
    
    return failed == 0


def test_configuration_customization():
    """Test that configuration can be customized."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST: Configuration Customization")
    logger.info("=" * 80)
    logger.info("-" * 80)
    
    # Create a custom configuration
    custom_config = BackchannelingConfig(
        backchanneling_words={"yep", "gotcha", "cool"},
        command_words={"stop", "cancel"},
        enabled=True
    )
    
    analyzer = InterruptionAnalyzer(custom_config)
    
    logger.info("Custom configuration created:")
    logger.info(f"  Backchanneling words: {custom_config.backchanneling_words}")
    logger.info(f"  Command words: {custom_config.command_words}")
    logger.info(f"  Enabled: {custom_config.enabled}")
    logger.info("")
    
    # Test with custom words
    test_cases = [
        ("yep", True, True, "Custom backchanneling word"),
        ("cool", True, True, "Custom backchanneling word"),
        ("stop", True, False, "Custom command word"),
        ("cancel", True, False, "Custom command word"),
    ]
    
    passed = 0
    
    for transcript, agent_is_speaking, expected_ignore, description in test_cases:
        should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
        status = "✓ PASS" if should_ignore == expected_ignore else "✗ FAIL"
        
        if should_ignore == expected_ignore:
            passed += 1
        
        logger.info(f"{status}: {description}")
        logger.info(f"  Transcript: '{transcript}' | Result: {should_ignore}")
    
    logger.info("-" * 80)
    logger.info(f"Configuration customization: {passed}/{len(test_cases)} passed")
    
    return passed == len(test_cases)


def main():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "LiveKit Intelligent Interruption Handling - Test Suite".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    logger.info(f"Test run started at: {datetime.now()}")
    logger.info("")
    
    results = []
    
    # Run main scenarios
    results.append(("Scenario 1: Long Explanation", test_scenario_1_long_explanation()))
    results.append(("Scenario 2: Passive Affirmation", test_scenario_2_passive_affirmation()))
    results.append(("Scenario 3: Correction", test_scenario_3_correction()))
    results.append(("Scenario 4: Mixed Input", test_scenario_4_mixed_input()))
    
    # Run additional tests
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Configuration Customization", test_configuration_customization()))
    
    # Print final report
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " TEST SUMMARY ".center(78, "=") + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("")
    logger.info(f"Total: {passed_count}/{total_count} test suites passed")
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    logger.info(f"Pass Rate: {pass_rate:.1f}%")
    logger.info("")
    logger.info(f"Test run completed at: {datetime.now()}")
    
    if passed_count == total_count:
        logger.info("╔" + "=" * 78 + "╗")
        logger.info("║" + " ✓ ALL TESTS PASSED ".center(78) + "║")
        logger.info("╚" + "=" * 78 + "╝")
        logger.info("")
        return 0
    else:
        logger.error("╔" + "=" * 78 + "╗")
        logger.error("║" + f" ✗ {total_count - passed_count} TEST(S) FAILED ".center(78) + "║")
        logger.error("╚" + "=" * 78 + "╝")
        logger.error("")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
