"""
Integration test - simulates the filtering logic without needing LiveKit connection
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration-test")

# Configuration
IGNORE_WORDS = {'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 'aha', 'mhm', 'uh', 'um', 'yep', 'yup'}
COMMAND_WORDS = {'stop', 'wait', 'no', 'pause', 'hold', 'halt', 'but'}


class SimulatedAgent:
    def __init__(self):
        self.speaking = False
        self.current_speech = ""
    
    def start_speaking(self, text):
        self.speaking = True
        self.current_speech = text
        logger.info(f"🤖 Agent: '{text}'")
    
    def stop_speaking(self):
        self.speaking = False
        self.current_speech = ""
        logger.info("🤖 Agent: [stopped]")
    
    def should_filter(self, transcript):
        if not self.speaking:
            return False
        
        if not transcript or not transcript.strip():
            return False
        
        words = set(transcript.lower().split())
        has_command = bool(words & COMMAND_WORDS)
        only_ignore = words and words.issubset(IGNORE_WORDS)
        
        return only_ignore and not has_command
    
    def handle_user_input(self, transcript):
        should_filter = self.should_filter(transcript)
        
        if should_filter:
            logger.info(f"👤 User: '{transcript}' → ✅ FILTERED (agent continues)")
            return "continue"
        elif not transcript or not transcript.strip():
            # Empty input - don't interrupt
            logger.info(f"👤 User: '{transcript}' → ✅ FILTERED (empty)")
            return "continue"
        elif self.speaking:
            logger.info(f"👤 User: '{transcript}' → ⛔ INTERRUPT (agent stops)")
            self.stop_speaking()
            return "interrupt"
        else:
            logger.info(f"👤 User: '{transcript}' → 💬 RESPOND")
            return "respond"


def run_test_scenarios():
    agent = SimulatedAgent()
    
    print("\n" + "="*60)
    print("SCENARIO 1: Long Explanation (Agent Speaking + Backchanneling)")
    print("="*60)
    agent.start_speaking("Let me explain how quantum computing works...")
    assert agent.handle_user_input("yeah") == "continue"
    assert agent.handle_user_input("okay") == "continue"
    assert agent.handle_user_input("hmm") == "continue"
    assert agent.handle_user_input("uh-huh") == "continue"
    assert agent.speaking == True  # Agent should still be speaking
    print("✅ PASS: Agent continued through all backchanneling\n")
    agent.stop_speaking()
    
    print("="*60)
    print("SCENARIO 2: Passive Affirmation (Agent Silent + 'Yeah')")
    print("="*60)
    agent.speaking = False
    result = agent.handle_user_input("yeah")
    assert result == "respond"
    print("✅ PASS: Agent processed 'yeah' as valid input\n")
    
    print("="*60)
    print("SCENARIO 3: Command Interruption (Agent Speaking + 'Stop')")
    print("="*60)
    agent.start_speaking("One, two, three, four, five...")
    result = agent.handle_user_input("no stop")
    assert result == "interrupt"
    assert agent.speaking == False
    print("✅ PASS: Agent stopped on command\n")
    
    print("="*60)
    print("SCENARIO 4: Mixed Input (Agent Speaking + 'Yeah but wait')")
    print("="*60)
    agent.start_speaking("Let me continue counting...")
    result = agent.handle_user_input("yeah okay but wait")
    assert result == "interrupt"
    assert agent.speaking == False
    print("✅ PASS: Agent stopped on mixed input with command\n")
    
    print("="*60)
    print("ADDITIONAL TESTS")
    print("="*60)
    
    # Test: Regular sentence while speaking
    agent.start_speaking("Explaining something...")
    result = agent.handle_user_input("what is the weather")
    assert result == "interrupt"
    print("✅ Regular sentence interrupts correctly")
    
    # Test: Multiple ignore words
    agent.start_speaking("Still explaining...")
    result = agent.handle_user_input("yeah yeah okay")
    assert result == "continue"
    print("✅ Multiple ignore words filtered correctly")
    
    # Test: Empty input
    result = agent.handle_user_input("")
    assert result == "continue"  # Empty doesn't interrupt
    print("✅ Empty input handled correctly")
    
    print("\n" + "="*60)
    print("🎉 ALL INTEGRATION TESTS PASSED!")
    print("="*60)


if __name__ == "__main__":
    run_test_scenarios()
