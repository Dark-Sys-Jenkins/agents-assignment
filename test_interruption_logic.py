#!/usr/bin/env python3
"""
Test scenarios for LiveKit Intelligent Interruption Handler.

This script simulates the interruption filter logic to verify it works correctly
across all test cases defined in the challenge.

Run with: python test_interruption_logic.py

Logs are automatically saved to: test_results.log
"""

import logging
import sys
from datetime import datetime

# Global logger instance
logger = None

# Configuration (mirrored from interruption_config.py)
IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "right", "yep", "mmhmm",
    "sure", "understood", "got it", "uh", "um", "ah", "yeah yeah",
    "absolutely", "definitely", "certainly", "sounds good", "i see",
    "i know", "i get it", "makes sense", "got ya", "no kidding",
    "you bet", "for sure", "all right", "alright"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "hold", "cancel", "pause",
    "hold on", "wait wait", "one second", "one sec", "just a sec",
    "hang on", "slow down", "repeat that", "what", "sorry", "excuse me",
    "never mind", "never", "don't", "don't say that"
}

FILLER_WORDS = {
    "but", "and", "or", "like", "you know", "i mean", "actually",
    "well", "so", "anyway", "basically", "essentially", "practically",
    "kind of", "sort of", "somehow", "somewhat", "quite", "really",
    "very", "pretty", "honestly", "seriously", "literally"
}


class MockSpeechHandle:
    """Mock speech handle for testing."""
    def __init__(self, interrupted=False, allow_interruptions=True):
        self.interrupted = interrupted
        self.allow_interruptions = allow_interruptions


def test_filter_logic(transcript: str, agent_speaking: bool) -> tuple[str, str]:
    """
    Simulate the interruption filter logic from agent_activity.py.
    
    Args:
        transcript: User's STT transcript
        agent_speaking: Whether agent._current_speech is not None
        
    Returns:
        (action, reason) - What the agent should do and why
    """
    
    # Step 1: Get tokens
    tokens = [t.strip(".,!?;:()[]\"'") for t in transcript.lower().split() if t.strip()]
    
    # Filter out empty tokens and articles
    tokens = [t for t in tokens if t and t not in {"a", "an", "the", "to", "in", "on", "at"}]
    
    if not tokens:
        return ("SWALLOW", "No tokens (VAD blip)")
    
    # Step 2: If agent is NOT speaking, use normal flow
    if not agent_speaking:
        return ("RESPOND", "Agent is silent - treat as normal input")
    
    # Step 3: If agent IS speaking, apply filter
    # Check for interrupt words (highest priority)
    has_interrupt_words = any(tok in INTERRUPT_WORDS for tok in tokens)
    
    if has_interrupt_words:
        return ("INTERRUPT", f"Contains interrupt words: {[t for t in tokens if t in INTERRUPT_WORDS]}")
    
    # Check if all tokens are acceptable (ignore or filler words)
    acceptable_tokens = IGNORE_WORDS | FILLER_WORDS
    has_only_acceptable = all(tok in acceptable_tokens for tok in tokens)
    
    if has_only_acceptable:
        return ("SWALLOW", f"Only passive/filler words: {tokens}")
    
    # Mixed content (has words not in either list)
    return ("INTERRUPT", f"Mixed content detected: {tokens}")


def run_test_suite():
    """Run all test scenarios."""
    
    test_cases = [
        # Scenario 1: Long Explanation
        {
            "name": "Scenario 1: Agent Speaking + Multiple Filler Words",
            "transcript": "Yeah... okay... uh-huh",
            "agent_speaking": True,
            "expected_action": "SWALLOW",
            "description": "Agent explaining concept, user provides backchannel feedback"
        },
        
        # Scenario 2: Passive Affirmation
        {
            "name": "Scenario 2: Agent Silent + Affirmation",
            "transcript": "Yeah",
            "agent_speaking": False,
            "expected_action": "RESPOND",
            "description": "Agent asks question and waits, user responds"
        },
        
        # Scenario 3: Direct Command
        {
            "name": "Scenario 3: Agent Speaking + Command Word",
            "transcript": "Stop",
            "agent_speaking": True,
            "expected_action": "INTERRUPT",
            "description": "Agent counting, user says stop"
        },
        
        # Scenario 4: Mixed Input
        {
            "name": "Scenario 4: Agent Speaking + Mixed Input",
            "transcript": "Yeah but wait a second",
            "agent_speaking": True,
            "expected_action": "INTERRUPT",
            "description": "Mixed filler + command words"
        },
        
        # Additional test cases
        {
            "name": "Scenario 5: Agent Speaking + Multiple Commands",
            "transcript": "No wait hold on",
            "agent_speaking": True,
            "expected_action": "INTERRUPT",
            "description": "Multiple interrupt words"
        },
        
        {
            "name": "Scenario 6: Agent Speaking + Partial Sentence",
            "transcript": "Right right, okay",
            "agent_speaking": True,
            "expected_action": "SWALLOW",
            "description": "Repetitive filler words"
        },
        
        {
            "name": "Scenario 7: Agent Silent + Command",
            "transcript": "Cancel that",
            "agent_speaking": False,
            "expected_action": "RESPOND",
            "description": "Command while agent is silent"
        },
        
        {
            "name": "Scenario 8: Empty Input (VAD Blip)",
            "transcript": "",
            "agent_speaking": True,
            "expected_action": "SWALLOW",
            "description": "False positive from VAD"
        },
        
        {
            "name": "Scenario 9: Punctuation Only",
            "transcript": "... ... ...",
            "agent_speaking": True,
            "expected_action": "SWALLOW",
            "description": "Only punctuation (noise)"
        },
        
        {
            "name": "Scenario 10: Complex Mixed Sentence",
            "transcript": "Yeah I see, hmm, but wait what about that",
            "agent_speaking": True,
            "expected_action": "INTERRUPT",
            "description": "Complex sentence with mixed content"
        },
    ]
    
    print("=" * 80)
    print("LIVEKT INTELLIGENT INTERRUPTION HANDLER - TEST SUITE")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    logger.info("Starting test execution...")
    logger.info("-" * 80)
    
    for i, test in enumerate(test_cases, 1):
        action, reason = test_filter_logic(test["transcript"], test["agent_speaking"])
        expected = test["expected_action"]
        passed_test = action == expected
        
        if passed_test:
            passed += 1
            status = "✓ PASS"
            logger.info(f"Test {i} PASSED: {test['name']}")
        else:
            failed += 1
            status = "✗ FAIL"
            logger.warning(f"Test {i} FAILED: {test['name']}")
        
        logger.debug(f"  Description: {test['description']}")
        logger.debug(f"  Transcript: '{test['transcript']}'")
        logger.debug(f"  Agent Speaking: {test['agent_speaking']}")
        logger.debug(f"  Expected: {expected}, Got: {action}")
        logger.debug(f"  Reason: {reason}")
        
        print(f"Test {i}: {test['name']}")
        print(f"  Description: {test['description']}")
        print(f"  Transcript: '{test['transcript']}'")
        print(f"  Agent Speaking: {test['agent_speaking']}")
        print(f"  Expected: {expected}")
        print(f"  Got: {action}")
        print(f"  Reason: {reason}")
        print(f"  Result: {status}")
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    print("=" * 80)
    
    logger.info("-" * 80)
    logger.info(f"Test Results Summary:")
    logger.info(f"  Total: {len(test_cases)}")
    logger.info(f"  Passed: {passed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Success Rate: {(passed/len(test_cases)*100):.1f}%")
    
    if failed == 0:
        print("✓ All tests passed!")
        logger.info("[PASS] All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
        logger.error(f"[FAIL] {failed} test(s) failed")
    
    return failed == 0


def show_configuration():
    """Display current configuration."""
    logger.info("Current Configuration:")
    logger.info(f"  IGNORE_WORDS ({len(IGNORE_WORDS)} words): {sorted(IGNORE_WORDS)}")
    logger.info(f"  INTERRUPT_WORDS ({len(INTERRUPT_WORDS)} words): {sorted(INTERRUPT_WORDS)}")
    
    print("\nCURRENT CONFIGURATION:")
    print(f"  IGNORE_WORDS: {sorted(IGNORE_WORDS)}")
    print(f"  INTERRUPT_WORDS: {sorted(INTERRUPT_WORDS)}")
    print()


def setup_logging():
    """Configure logging to both console and file."""
    global logger
    
    # Create logger
    logger = logging.getLogger("InterruptionHandler")
    logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (logs to test_results.log)
    log_filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (logs to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return log_filename


if __name__ == "__main__":
    log_file = setup_logging()
    
    logger.info("=" * 80)
    logger.info("LIVEKIT INTELLIGENT INTERRUPTION HANDLER - TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Test started at: {datetime.now()}")
    logger.info(f"Logs will be saved to: {log_file}")
    logger.info("")
    
    show_configuration()
    success = run_test_suite()
    
    logger.info("")
    logger.info("=" * 80)
    if success:
        logger.info("[SUCCESS] All tests passed - Logs saved successfully")
    else:
        logger.error("[FAILURE] Some tests failed - Check log file for details")
    logger.info("=" * 80)
    logger.info(f"Test completed at: {datetime.now()}")
    
    exit(0 if success else 1)