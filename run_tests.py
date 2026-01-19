"""
Minimal standalone test for intelligent interruption handling.

This test file directly includes the interruption handler logic to avoid
dependency issues and demonstrates the behavior across all four test scenarios.
"""

import logging
import sys
from datetime import datetime

# Setup logging to capture detailed test output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tests123.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# INLINE INTERRUPTION HANDLER (for testing purposes)
# ============================================================================

from dataclasses import dataclass, field
from typing import Set

@dataclass
class BackchannelingConfig:
    """Configuration for backchanneling (passive acknowledgement) detection."""
    
    backchanneling_words: Set[str] = field(
        default_factory=lambda: {
            "yeah", "yep", "yes", "yea",
            "ok", "okay", "okey",
            "hmm", "hm", "mm", "mmm",
            "aha", "ah", "ohh", "oh",
            "right", "uh-huh", "uhhuh", "uh huh",
            "uh", "um", "umm", "uhh",
            "sure", "exactly", "absolutely",
            "mhm", "mhmm", "mm-hmm", "mmhmm",
            "gotcha", "got it",
        }
    )
    
    command_words: Set[str] = field(
        default_factory=lambda: {
            "stop", "wait", "hold", "hold on",
            "no", "nope", "not", "never",
            "pause", "later", "never mind",
            "wrong", "incorrect", "that's wrong",
            "repeat", "again", "rewind",
            "cancel", "reset", "restart",
            "clear", "skip",
        }
    )
    
    enabled: bool = True


class InterruptionAnalyzer:
    """
    Analyzes user speech to determine if it's a backchanneling or active interruption.
    """
    
    def __init__(self, config: BackchannelingConfig | None = None):
        self.config = config or BackchannelingConfig()
        self._word_cache: dict[str, bool] = {}
    
    def should_ignore_interruption(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> bool:
        """
        Determine if an interruption should be ignored (filtered out).
        """
        if not self.config.enabled or not agent_is_speaking:
            return False
        
        normalized = self._normalize_text(transcript)
        words = self._extract_words(normalized)
        
        if not words:
            return True
        
        has_command = any(word in self.config.command_words for word in words)
        
        if has_command:
            logger.debug(f"Detected command word in transcript: '{transcript}'")
            return False
        
        all_backchanneling = all(word in self.config.backchanneling_words for word in words)
        
        if all_backchanneling:
            logger.debug(f"Detected backchanneling in transcript: '{transcript}'")
            return True
        
        logger.debug(f"Detected mixed/unknown content in transcript: '{transcript}'")
        return False
    
    def _normalize_text(self, text: str) -> str:
        return text.lower().strip()
    
    def _extract_words(self, text: str) -> list[str]:
        import re
        text = text.replace("uh-huh", "uhhuh")
        text = text.replace("uh huh", "uhhuh")
        text = text.replace("hold on", "holdon")
        text = text.replace("never mind", "nevermind")
        text = text.replace("that's wrong", "thatswrong")
        text = text.replace("got it", "gotit")
        text = text.replace("mm-hmm", "mmhmm")
        words = re.findall(r'\b\w+\b', text)
        return words
    
    def get_analysis(self, transcript: str, agent_is_speaking: bool) -> dict:
        normalized = self._normalize_text(transcript)
        words = self._extract_words(normalized)
        
        backchanneling = [w for w in words if w in self.config.backchanneling_words]
        commands = [w for w in words if w in self.config.command_words]
        unknown = [w for w in words if w not in self.config.backchanneling_words
                   and w not in self.config.command_words]
        
        should_ignore = self.should_ignore_interruption(transcript, agent_is_speaking)
        
        return {
            "original_transcript": transcript,
            "normalized": normalized,
            "words": words,
            "backchanneling_words": backchanneling,
            "command_words": commands,
            "unknown_words": unknown,
            "agent_is_speaking": agent_is_speaking,
            "should_ignore": should_ignore,
        }


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

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
        logger.info("[PASS] TEST PASSED: Backchanneling was correctly filtered")
        logger.info("[PASS] Agent continues speaking without interruption")
        return True
    else:
        logger.error("[FAIL] TEST FAILED: Backchanneling was not filtered")
        logger.error("[FAIL] Agent would have stopped speaking")
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
        logger.info("[PASS] TEST PASSED: Interruption was not filtered")
        logger.info("[PASS] Agent processes 'Yeah' as valid user input")
        return True
    else:
        logger.error("[FAIL] TEST FAILED: Interruption was filtered when it shouldn't be")
        logger.error("[FAIL] Agent ignored valid user input")
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
        logger.info("[PASS] TEST PASSED: Command was recognized and not filtered")
        logger.info("[PASS] Agent will interrupt and listen to the new command")
        return True
    else:
        logger.error("[FAIL] TEST FAILED: Command was incorrectly filtered")
        logger.error("[FAIL] Agent would continue speaking instead of stopping")
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
        logger.info("[PASS] TEST PASSED: Mixed input with command was recognized")
        logger.info("[PASS] Agent will interrupt and listen to the new command")
        return True
    else:
        logger.error("[FAIL] TEST FAILED: Mixed input was incorrectly filtered")
        logger.error("[FAIL] Agent would continue speaking instead of stopping")
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
        ("uh", True, True, "Single filler word while agent speaking"),
        ("umm hmm", True, True, "Multiple filler words while agent speaking"),
        ("wait", True, False, "Single command word while agent speaking"),
        ("hold on", True, False, "Command phrase while agent speaking"),
        ("okay", False, False, "Backchanneling while agent silent (should NOT ignore)"),
        ("right", True, True, "Right as backchanneling"),
        ("yeah I need help", True, False, "Mixed backchanneling + unknown words"),
        ("mm hmm sure", True, True, "All backchanneling words"),
        ("stop the music", True, False, "Command with extra words"),
    ]
    
    passed = 0
    failed = 0
    
    for transcript, agent_is_speaking, expected_ignore, description in test_cases:
        should_ignore = analyzer.should_ignore_interruption(transcript, agent_is_speaking)
        status = "[PASS]" if should_ignore == expected_ignore else "[FAIL]"
        
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
        status = "[PASS]" if should_ignore == expected_ignore else "[FAIL]"
        
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
    logger.info("=" * 80)
    logger.info("LiveKit Intelligent Interruption Handling - Test Suite".center(80))
    logger.info("=" * 80)
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
    logger.info("=" * 80)
    logger.info("TEST SUMMARY".center(80))
    logger.info("=" * 80)
    logger.info("")
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"{status} {test_name}")
    
    logger.info("")
    logger.info(f"Total: {passed_count}/{total_count} test suites passed")
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
    logger.info(f"Pass Rate: {pass_rate:.1f}%")
    logger.info("")
    logger.info(f"Test run completed at: {datetime.now()}")
    
    if passed_count == total_count:
        logger.info("=" * 80)
        logger.info("ALL TESTS PASSED".center(80))
        logger.info("=" * 80)
        logger.info("")
        return 0
    else:
        logger.error("=" * 80)
        logger.error(f"{total_count - passed_count} TEST(S) FAILED".center(80))
        logger.error("=" * 80)
        logger.error("")
        return 1


if __name__ == "__main__":
    exit_code = main()
    print("\nLog file generated: tests123.log")
    sys.exit(exit_code)
