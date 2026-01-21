"""
Standalone test for the interruption handler
Tests the core logic without importing the full LiveKit agents package
"""

import re
import sys
import os

# Read and execute just the interruption handler code
handler_path = os.path.join(
    os.path.dirname(__file__), 
    'livekit-agents/livekit/agents/voice/interruption_handler.py'
)

# Read the handler file
with open(handler_path, 'r') as f:
    handler_code = f.read()

# Execute it in our namespace
exec(handler_code)

def main():
    print("\n" + "="*70)
    print("INTELLIGENT INTERRUPTION HANDLER - TEST SUITE".center(70))
    print("="*70 + "\n")
    
    # Create handler instance
    handler = IntelligentInterruptionHandler()
    
    # Scenario 1: Backchanneling while agent speaking (should IGNORE)
    print("SCENARIO 1: The Long Explanation")
    print("-" * 70)
    backchannels = ["yeah", "ok", "hmm", "uh-huh", "right", "okay yeah", "mmm"]
    for word in backchannels:
        decision = handler.should_interrupt(word, agent_speaking=True)
        if not decision.should_interrupt:
            print(f"[PASS] '{word}' → IGNORED (agent continues)")
        else:
            print(f"[FAIL] '{word}' → should have been IGNORED")
            sys.exit(1)
    
    # Scenario 2: Same words when agent is silent (should RESPOND)  
    print("\nSCENARIO 2: The Passive Affirmation")
    print("-" * 70)
    responses = ["yeah", "ok", "sure", "yes"]
    for word in responses:
        decision = handler.should_interrupt(word, agent_speaking=False)
        if decision.should_interrupt:
            print(f"[PASS] '{word}' → PROCESSED (valid response)")
        else:
            print(f"[FAIL] '{word}' → should have been PROCESSED")
            sys.exit(1)
    
    # Scenario 3: Interrupt commands (should INTERRUPT)
    print("\nSCENARIO 3: The Correction")
    print("-" * 70)
    interrupts = ["wait", "stop", "no", "hold on", "no stop"]
    for word in interrupts:
        decision = handler.should_interrupt(word, agent_speaking=True)
        if decision.should_interrupt:
            print(f"[PASS] '{word}' → INTERRUPTED (agent stops)")
        else:
            print(f"[FAIL] '{word}' → should have INTERRUPTED")
            sys.exit(1)
    
    # Scenario 4: Mixed input (should INTERRUPT)
    print("\nSCENARIO 4: The Mixed Input")
    print("-" * 70)
    mixed = [
        "yeah okay but wait",
        "ok I have a question", 
        "hmm actually no",
        "yeah but wait"
    ]
    for phrase in mixed:
        decision = handler.should_interrupt(phrase, agent_speaking=True)
        if decision.should_interrupt:
            print(f"[PASS] '{phrase}' → INTERRUPTED (mixed content)")
        else:
            print(f"[FAIL] '{phrase}' → should have INTERRUPTED (mixed)")
            sys.exit(1)
    
    # Edge cases
    print("\nEDGE CASES")
    print("-" * 70)
    
    # Empty input
    decision = handler.should_interrupt("", agent_speaking=True)
    if not decision.should_interrupt:
        print(f"[PASS] Empty input → IGNORED")
    else:
        print(f"[FAIL] Empty input should be IGNORED")
        sys.exit(1)
    
    # Case insensitive
    decision = handler.should_interrupt("YEAH OK", agent_speaking=True)
    if not decision.should_interrupt:
        print(f"[PASS] 'YEAH OK' (uppercase) → IGNORED")
    else:
        print(f"[FAIL] Uppercase should work (case insensitive)")
        sys.exit(1)
    
    # With punctuation
    decision = handler.should_interrupt("yeah!", agent_speaking=True)
    if not decision.should_interrupt:
        print(f"[PASS] 'yeah!' (punctuation) → IGNORED")
    else:
        print(f"[FAIL] Should handle punctuation")
        sys.exit(1)
    
    # Custom configuration test
    print("\nCUSTOM CONFIGURATION")
    print("-" * 70)
    config = InterruptionConfig(
        ignore_words=["yeah", "ok"],
        interrupt_words=["stop"],
        case_sensitive=False
    )
    custom_handler = IntelligentInterruptionHandler(config=config)
    
    decision = custom_handler.should_interrupt("yeah", agent_speaking=True)
    if not decision.should_interrupt:
        print(f"[PASS] Custom config works")
    else:
        print(f"[FAIL] Custom config failed")
        sys.exit(1)
    
    # Add words dynamically
    custom_handler.add_ignore_words(["sure"])
    decision = custom_handler.should_interrupt("sure", agent_speaking=True)
    if not decision.should_interrupt:
        print(f"[PASS] Dynamic word addition works")
    else:
        print(f"[FAIL] Dynamic word addition failed")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED!".center(70))
    print("="*70 + "\n")
    
    print("Test Results Summary:")
    print("  [PASS] Scenario 1: Backchanneling ignored while speaking")
    print("  [PASS] Scenario 2: Backchanneling processed when silent")
    print("  [PASS] Scenario 3: Interrupt commands stop agent")
    print("  [PASS] Scenario 4: Mixed input triggers interrupt")
    print("  [PASS] Edge cases handled correctly")
    print("  [PASS] Custom configuration works")
    print()
    print("The intelligent interruption handler is working correctly!")
    print()


if __name__ == "__main__":
    main()
