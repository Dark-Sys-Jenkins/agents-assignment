"""
Standalone test script for InterruptionHandler
Tests the logic without running the full LiveKit agent

Usage:
    python test_interruption_handler.py
"""

import logging
import sys
import io

# Fix Windows encoding issue
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("test-script")


class InterruptionHandler:
    """Copy of your InterruptionHandler class for testing"""
    
    def __init__(self):
        self.ignore_phrases = {
            "yeah", "ok", "okay", "hmm", "uh-huh", 
            "right", "aha", "mhm", "sure", "yep",
            "got it", "i see", "alright", "uh huh",
            "mm-hmm", "yeah yeah"
        }
        
        self.agent_is_speaking = False
        
        self.interrupt_keywords = {
            "stop", "wait", "no", "hold", "pause", 
            "hold on", "wait a second", "stop that",
            "hang on", "one second"
        }
        
        logger.info(f"InterruptionHandler initialized")
    
    def set_agent_speaking(self, is_speaking: bool):
        self.agent_is_speaking = is_speaking
        state = "SPEAKING" if is_speaking else "SILENT"
        logger.debug(f"Agent state: {state}")
    
    def should_ignore_interruption(self, transcribed_text: str) -> bool:
        if not transcribed_text:
            return True
        
        text_lower = transcribed_text.lower().strip()
        
        # RULE 1: If agent is NOT speaking, NEVER ignore
        if not self.agent_is_speaking:
            logger.info(f"Agent silent -> Processing: '{text_lower}'")
            return False
        
        # RULE 2: Check for interrupt keywords
        for keyword in self.interrupt_keywords:
            if keyword in text_lower:
                logger.info(f"Interrupt keyword '{keyword}' detected -> Stopping agent")
                return False
        
        # RULE 3: Check if ONLY filler words
        words = text_lower.split()
        
        if len(words) == 1 and words[0] in self.ignore_phrases:
            logger.info(f"Ignoring filler word while speaking: '{text_lower}'")
            return True
        
        all_filler = all(word in self.ignore_phrases for word in words)
        
        if all_filler:
            logger.info(f"Ignoring all-filler phrase while speaking: '{text_lower}'")
            return True
        
        logger.info(f"Processing real/mixed input: '{text_lower}'")
        return False


def run_test(handler, test_name, user_input, agent_speaking, expected_ignore):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"User says: '{user_input}'")
    print(f"Agent state: {'SPEAKING' if agent_speaking else 'SILENT'}")
    print(f"Expected: {'IGNORE (continue)' if expected_ignore else 'PROCESS (interrupt)'}")
    print(f"-" * 60)
    
    # Set agent state
    handler.set_agent_speaking(agent_speaking)
    
    # Test the logic
    result = handler.should_ignore_interruption(user_input)
    
    # Check result
    passed = result == expected_ignore
    status = "[PASS]" if passed else "[FAIL]"
    actual = "IGNORE" if result else "PROCESS"
    
    print(f"Actual: {actual}")
    print(f"Result: {status}")
    
    return passed


def main():
    """Run all test cases"""
    print("\n" + "="*60)
    print("INTERRUPTION HANDLER TEST SUITE")
    print("="*60)
    
    handler = InterruptionHandler()
    results = []
    
    # Test Suite
    tests = [
        # (name, user_input, agent_speaking, expected_ignore)
        
        # Core Test Cases (Required)
        ("Scenario 1: Agent speaking + 'yeah'", "yeah", True, True),
        ("Scenario 2: Agent silent + 'yeah'", "yeah", False, False),
        ("Scenario 3: Agent speaking + 'stop'", "stop", True, False),
        ("Scenario 4: Agent speaking + 'yeah wait'", "yeah wait", True, False),
        
        # Edge Cases
        ("Multiple fillers", "yeah yeah", True, True),
        ("Multiple fillers (different)", "ok sure", True, True),
        ("Filler when silent", "hmm", False, False),
        ("Interrupt when silent", "stop", False, False),
        ("Mixed with real word", "yeah I disagree", True, False),
        ("Case insensitive - upper", "YEAH", True, True),
        ("Case insensitive - mixed", "Yeah", True, True),
        ("Interrupt keyword - no", "no", True, False),
        ("Interrupt keyword - wait", "wait", True, False),
        ("Interrupt keyword - hold on", "hold on", True, False),
        ("Long filler phrase", "yeah ok sure", True, True),
        ("Command in middle", "ok but stop", True, False),
        ("Empty string", "", True, True),
        ("Whitespace only", "   ", True, True),
    ]
    
    # Run all tests
    for test_name, user_input, agent_speaking, expected in tests:
        passed = run_test(handler, test_name, user_input, agent_speaking, expected)
        results.append((test_name, passed))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    print(f"{'='*60}\n")
    
    if passed_count == total_count:
        print("SUCCESS! ALL TESTS PASSED! Your implementation is correct!")
        return 0
    else:
        print("WARNING: Some tests failed. Review the logic above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)