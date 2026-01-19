# examples/voice_agents/test_interruption_logic.py
"""
Test script for intelligent interruption handler using fake components.
This allows testing the logic without any API costs.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_interruption_agent import (
    AgentStateTracker,
    InterruptionClassifier,
    IntelligentInterruptionHandler
)
from livekit.agents.voice.events import AgentStateChangedEvent, UserInputTranscribedEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-interruption")

# Mock classes for testing
class MockEvent:
    """Mock event for testing"""
    def __init__(self, state=None, transcript=None):
        self.new_state = state
        self.transcript = transcript

class MockSession:
    """Mock session for testing"""
    def __init__(self):
        self.interrupted = False
        self.committed = False
        self.cleared = False
        self.actions = []
    
    async def interrupt(self):
        self.interrupted = True
        self.actions.append("INTERRUPT")
        logger.info("[STOP] SESSION.INTERRUPT() called")
    
    async def commit_user_turn(self):
        self.committed = True
        self.actions.append("COMMIT")
        logger.info("[COMMIT] SESSION.COMMIT_USER_TURN() called")
    
    async def clear_user_turn(self):
        self.cleared = True
        self.actions.append("CLEAR")
        logger.info("[CLEAR] SESSION.CLEAR_USER_TURN() called")
    
    def reset(self):
        """Reset session state for next test"""
        self.interrupted = False
        self.committed = False
        self.cleared = False
        self.actions = []

# Test scenarios
async def run_test_scenario(name: str, handler: IntelligentInterruptionHandler, 
                           session: MockSession, agent_state: str, 
                           user_input: str, expected_actions: list[str]):
    """Run a single test scenario"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Agent State: {agent_state}")
    print(f"User Input: '{user_input}'")
    print(f"Expected Actions: {expected_actions}")
    print("-" * 80)
    
    # Reset session
    session.reset()
    
    # Set agent state
    await handler.on_agent_state_changed(MockEvent(state=agent_state))
    
    # Process user input
    await handler.handle_user_transcript(MockEvent(transcript=user_input), session)
    
    # Check results
    print("-" * 80)
    print(f"Actual Actions: {session.actions}")
    
    if session.actions == expected_actions:
        print("[PASS] TEST PASSED")
        return True
    else:
        print("[FAIL] TEST FAILED")
        print(f"   Expected: {expected_actions}")
        print(f"   Got: {session.actions}")
        return False

async def main():
    """Run all test scenarios"""
    print("\n" + "="*80)
    print("INTELLIGENT INTERRUPTION HANDLER - TEST SUITE")
    print("="*80)
    
    # Initialize handler
    handler = IntelligentInterruptionHandler()
    session = MockSession()
    
    results = []
    
    # ========================================================================
    # TEST 1: Backchanneling while agent is speaking (MUST NOT INTERRUPT)
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 1: Backchanneling while speaking",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="yeah",
        expected_actions=["CLEAR"]  # Clears the buffer explicitly
    ))
    
    # ========================================================================
    # TEST 2: Multiple backchanneling words while speaking
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 2: Multiple backchanneling while speaking",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="ok hmm yeah",
        expected_actions=["CLEAR"]
    ))
    
    # ========================================================================
    # TEST 3: Real interruption while speaking (MUST INTERRUPT)
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 3: Real interruption while speaking",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="wait stop",
        expected_actions=["INTERRUPT", "COMMIT"]
    ))
    
    # ========================================================================
    # TEST 4: Single interrupt keyword while speaking
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 4: Single interrupt keyword 'stop'",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="stop",
        expected_actions=["INTERRUPT", "COMMIT"]
    ))
    
    # ========================================================================
    # TEST 5: Mixed input (backchanneling + interrupt)
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 5: Mixed input 'yeah but wait'",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="yeah but wait",
        expected_actions=["INTERRUPT", "COMMIT"]  # Should interrupt because of "wait"
    ))
    
    # ========================================================================
    # TEST 6: Backchanneling while agent is SILENT (MUST RESPOND)
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 6: Backchanneling while silent",
        handler=handler,
        session=session,
        agent_state="idle",
        user_input="yeah",
        expected_actions=["COMMIT"]  # Should process as valid input
    ))
    
    # ========================================================================
    # TEST 7: Normal input while silent
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 7: Normal input while silent",
        handler=handler,
        session=session,
        agent_state="idle",
        user_input="tell me about Paris",
        expected_actions=["COMMIT"]
    ))
    
    # ========================================================================
    # TEST 8: Interrupt keyword while silent
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 8: Interrupt keyword while silent",
        handler=handler,
        session=session,
        agent_state="idle",
        user_input="stop",
        expected_actions=["COMMIT"]  # Should still process (agent isn't speaking anyway)
    ))
    
    # ========================================================================
    # TEST 9: Multi-word interrupt phrase
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 9: Multi-word phrase 'hold on'",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="hold on a second",
        expected_actions=["INTERRUPT", "COMMIT"]
    ))
    
    # ========================================================================
    # TEST 10: Unknown/new word while speaking
    # ========================================================================
    results.append(await run_test_scenario(
        name="Test 10: Unknown word while speaking",
        handler=handler,
        session=session,
        agent_state="speaking",
        user_input="actually",
        expected_actions=["INTERRUPT", "COMMIT"]  # Should interrupt (err on safe side)
    ))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} [PASS]")
    print(f"Failed: {failed} [FAIL]")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if failed == 0:
        print("\n [SUCCESS] ALL TESTS PASSED! ")
        print("The intelligent interruption handler is working correctly!")
    else:
        print(f"\n [WARN] {failed} TEST(S) FAILED")
        print("Please review the failed tests above.")
    
    print("="*80 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)