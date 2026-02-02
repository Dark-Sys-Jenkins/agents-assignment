"""
Simple test that doesn't require full package installation.
Tests just the interruption handler logic directly.
"""

import sys
import os

# Add path to find the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'livekit-agents', 'livekit', 'agents', 'voice'))

# Import directly
from interruption_handler import InterruptionHandler

def main():
    print("=" * 60)
    print("Testing Interruption Handler Logic")
    print("=" * 60)
    
    handler = InterruptionHandler()
    
    tests = [
        ("Agent speaking + 'yeah'", True, "yeah", True),
        ("Agent speaking + 'stop'", True, "stop", False),
        ("Agent silent + 'yeah'", False, "yeah", False),
        ("Agent speaking + 'yeah but wait'", True, "yeah but wait", False),
        ("Agent speaking + 'ok yeah hmm'", True, "ok yeah hmm", True),
    ]
    
    passed = 0
    failed = 0
    
    for name, agent_speaking, transcript, expected_ignore in tests:
        result, reason = handler.should_ignore_interruption(
            agent_is_speaking=agent_speaking,
            transcript=transcript,
            wait_for_transcript=False
        )
        
        if result == expected_ignore:
            print(f"✅ {name}")
            print(f"   Expected: {expected_ignore}, Got: {result}, Reason: {reason}")
            passed += 1
        else:
            print(f"❌ {name}")
            print(f"   Expected: {expected_ignore}, Got: {result}, Reason: {reason}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All logic tests passed!")
        print("Next: Test with actual agent using:")
        print("   cd examples/voice_agents")
        print("   python basic_agent.py console")
    else:
        print("\n❌ Some tests failed. Check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
