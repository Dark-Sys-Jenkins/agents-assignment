"""
Quick test script to verify the interruption handler is working correctly.
This tests the logic without needing to run the full agent.
"""

import sys
import os

# Add the livekit-agents to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'livekit-agents'))

from livekit.agents.voice.interruption_handler import InterruptionHandler

def test_handler():
    """Test the interruption handler logic."""
    print("=" * 60)
    print("Testing Interruption Handler")
    print("=" * 60)
    
    handler = InterruptionHandler()
    
    # Test 1: Agent speaking + filler word = should ignore
    print("\n[Test 1] Agent speaking + 'yeah' = Should IGNORE")
    result, reason = handler.should_ignore_interruption(
        agent_is_speaking=True,
        transcript="yeah",
        wait_for_transcript=False
    )
    print(f"  Result: {result}, Reason: {reason}")
    assert result == True, "Should ignore 'yeah' when agent is speaking"
    print("  ✅ PASS")
    
    # Test 2: Agent speaking + command = should NOT ignore
    print("\n[Test 2] Agent speaking + 'stop' = Should NOT ignore")
    result, reason = handler.should_ignore_interruption(
        agent_is_speaking=True,
        transcript="stop",
        wait_for_transcript=False
    )
    print(f"  Result: {result}, Reason: {reason}")
    assert result == False, "Should NOT ignore 'stop' command"
    print("  ✅ PASS")
    
    # Test 3: Agent silent + filler word = should NOT ignore
    print("\n[Test 3] Agent silent + 'yeah' = Should NOT ignore")
    result, reason = handler.should_ignore_interruption(
        agent_is_speaking=False,
        transcript="yeah",
        wait_for_transcript=False
    )
    print(f"  Result: {result}, Reason: {reason}")
    assert result == False, "Should NOT ignore 'yeah' when agent is silent"
    print("  ✅ PASS")
    
    # Test 4: Agent speaking + mixed input = should NOT ignore
    print("\n[Test 4] Agent speaking + 'yeah but wait' = Should NOT ignore")
    result, reason = handler.should_ignore_interruption(
        agent_is_speaking=True,
        transcript="yeah but wait",
        wait_for_transcript=False
    )
    print(f"  Result: {result}, Reason: {reason}")
    assert result == False, "Should NOT ignore mixed input with command"
    print("  ✅ PASS")
    
    # Test 5: Multiple filler words
    print("\n[Test 5] Agent speaking + 'ok yeah hmm' = Should IGNORE")
    result, reason = handler.should_ignore_interruption(
        agent_is_speaking=True,
        transcript="ok yeah hmm",
        wait_for_transcript=False
    )
    print(f"  Result: {result}, Reason: {reason}")
    assert result == True, "Should ignore multiple filler words"
    print("  ✅ PASS")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)
    print("\nThe interruption handler logic is working correctly.")
    print("Next step: Test with actual agent using 'python examples/voice_agents/basic_agent.py console'")

if __name__ == "__main__":
    try:
        test_handler()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
