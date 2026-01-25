import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from filter import SemanticFilter

class AgentState:
    SPEAKING = "SPEAKING"
    LISTENING = "LISTENING"

def run_test():
    print("Running Logic Verification...")
    print("-" * 50)
    
    semantic_filter = SemanticFilter()
    
    # Format: (Input Text, Agent State, Expected Action)
    test_cases = [
        ("yeah", AgentState.SPEAKING, "IGNORE"),
        ("uh-huh", AgentState.SPEAKING, "IGNORE"),
        
        ("yeah", AgentState.LISTENING, "RESPOND"),
        
        ("stop", AgentState.SPEAKING, "INTERRUPT"),
        ("yeah wait", AgentState.SPEAKING, "INTERRUPT"),
    ]

    all_passed = True

    for text, state, expected in test_cases:
        if state != AgentState.SPEAKING:
            actual = "RESPOND"
        elif semantic_filter.should_ignore_input(text):
            actual = "IGNORE"
        else:
            actual = "INTERRUPT"

        if actual == expected:
            print(f"[PASS] Input: '{text.ljust(10)}' | State: {state.ljust(9)} -> Result: {actual}")
        else:
            print(f"[FAIL] Input: '{text.ljust(10)}' | State: {state.ljust(9)} -> Result: {actual} (Expected: {expected})")
            all_passed = False

    print("-" * 50)
    if all_passed:
        print("Success: All logic requirements met.")
    else:
        print("Failed: Logic errors detected.")

if __name__ == "__main__":
    run_test()