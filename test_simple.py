"""
Simplified test script that imports only the handler module directly
"""

import sys
import os

# Read and execute the handler file directly to avoid dependency issues
handler_path = os.path.join(
    os.path.dirname(__file__), 
    'livekit-agents/livekit/agents/voice/interruption_handler.py'
)

with open(handler_path, 'r') as f:
    handler_code = f.read()

exec(handler_code)


def print_decision(test_name: str, decision, user_input: str, agent_speaking: bool):
    """Pretty print a test decision."""
    status = "[PASS]" if (not decision.should_interrupt if agent_speaking and user_input in ["yeah", "ok", "hmm"] else True) else "[FAIL]"
    print(f"\n{status} | {test_name}")
    print(f"  User: '{user_input}' | Agent Speaking: {agent_speaking}")
    print(f"  Decision: {'INTERRUPT' if decision.should_interrupt else 'IGNORE'}")
    print(f"  Reason: {decision.reason}")


def main():
    print("\n" + "="*70)
    print("INTELLIGENT INTERRUPTION HANDLER - TEST SUITE".center(70))
    print("="*70 + "\n")
    
    handler = IntelligentInterruptionHandler()
    
    # Scenario 1: Backchanneling while agent speaking (should IGNORE)
    print("\nSCENARIO 1: The Long Explanation")
    print("-" * 70)
    for word in ["yeah", "ok", "hmm", "uh-huh", "right"]:
        decision = handler.should_interrupt(word, agent_speaking=True)
        assert not decision.should_interrupt, f"FAIL: '{word}' should not interrupt"
        print(f"[PASS] '{word}' → IGNORED (agent continues)")
    
    # Scenario 2: Same words when agent is silent (should RESPOND)
    print("\nSCENARIO 2: The Passive Affirmation")
    print("-" * 70)
    for word in ["yeah", "ok", "sure"]:
        decision = handler.should_interrupt(word, agent_speaking=False)
        assert decision.should_interrupt, f"FAIL: '{word}' should be processed when silent"
        print(f"[PASS] '{word}' → PROCESSED (valid response)")
    
    # Scenario 3: Interrupt commands (should INTERRUPT)
    print("\nSCENARIO 3: The Correction")
    print("-" * 70)
    for word in ["wait", "stop", "no", "hold on"]:
        decision = handler.should_interrupt(word, agent_speaking=True)
        assert decision.should_interrupt, f"FAIL: '{word}' should interrupt"
        print(f"[PASS] '{word}' → INTERRUPTED (agent stops)")
    
    # Scenario 4: Mixed input (should INTERRUPT)
    print("\nSCENARIO 4: The Mixed Input")
    print("-" * 70)
    for phrase in ["yeah okay but wait", "ok I have a question", "hmm actually no"]:
        decision = handler.should_interrupt(phrase, agent_speaking=True)
        assert decision.should_interrupt, f"FAIL: '{phrase}' should interrupt (mixed)"
        print(f"[PASS] '{phrase}' → INTERRUPTED (mixed content)")
    
    # Edge cases
    print("\nEDGE CASES")
    print("-" * 70)
    
    # Empty input
    decision = handler.should_interrupt("", agent_speaking=True)
    assert not decision.should_interrupt
    print(f"[PASS] Empty input → IGNORED")
    
    # Case insensitive
    decision = handler.should_interrupt("YEAH OK", agent_speaking=True)
    assert not decision.should_interrupt
    print(f"[PASS] 'YEAH OK' (uppercase) → IGNORED")
    
    # With punctuation
    decision = handler.should_interrupt("yeah!", agent_speaking=True)
    assert not decision.should_interrupt
    print(f"[PASS] 'yeah!' (punctuation) → IGNORED")
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED!".center(70))
    print("="*70 + "\n")
    
    print("Summary:")
    print("  [PASS] Scenario 1: Backchanneling ignored while speaking")
    print("  [PASS] Scenario 2: Backchanneling processed when silent")
    print("  [PASS] Scenario 3: Interrupt commands stop agent")
    print("  [PASS] Scenario 4: Mixed input triggers interrupt")
    print("  [PASS] Edge cases handled correctly")
    print()


if __name__ == "__main__":
    main()
