# Mock test demonstrating the fix
IGNORE_WORDS = {"yeah", "ok", "hmm"}
INTERRUPT_WORDS = {"stop", "wait", "no"}

def should_ignore(text, agent_speaking):
    words = text.lower().split()
    has_interrupt = any(w in INTERRUPT_WORDS for w in words)
    all_fillers = all(w in IGNORE_WORDS for w in words)
    
    if agent_speaking and all_fillers and not has_interrupt:
        return True
    return False

# Test cases
print("Test 1 - Agent speaking, user says 'yeah':", should_ignore("yeah", True))  # True
print("Test 2 - Agent silent, user says 'yeah':", should_ignore("yeah", False))  # False
print("Test 3 - Agent speaking, user says 'stop':", should_ignore("stop", True))  # False

