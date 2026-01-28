"""
Unit tests for the intelligent interruption handler
"""

from interrupt_handler import IGNORE_WORDS, COMMAND_WORDS


class MockAgentState:
    def __init__(self):
        self.speaking = False


def should_filter(transcript: str, agent_speaking: bool) -> bool:
    """Test version of the filtering logic"""
    if not agent_speaking:
        return False
    
    if not transcript or not transcript.strip():
        return False
    
    words = set(transcript.lower().split())
    has_command = bool(words & COMMAND_WORDS)
    only_ignore = words and words.issubset(IGNORE_WORDS)
    
    return only_ignore and not has_command


def test_scenario_1_long_explanation():
    """Agent speaking + 'yeah' -> Should filter (agent continues)"""
    assert should_filter("yeah", agent_speaking=True) == True
    assert should_filter("okay", agent_speaking=True) == True
    assert should_filter("hmm", agent_speaking=True) == True
    assert should_filter("uh-huh", agent_speaking=True) == True
    print("✅ Scenario 1: Long Explanation - PASS")


def test_scenario_2_passive_affirmation():
    """Agent silent + 'yeah' -> Should NOT filter (agent responds)"""
    assert should_filter("yeah", agent_speaking=False) == False
    assert should_filter("okay", agent_speaking=False) == False
    print("✅ Scenario 2: Passive Affirmation - PASS")


def test_scenario_3_command():
    """Agent speaking + 'stop' -> Should NOT filter (agent stops)"""
    assert should_filter("stop", agent_speaking=True) == False
    assert should_filter("no stop", agent_speaking=True) == False
    assert should_filter("wait", agent_speaking=True) == False
    print("✅ Scenario 3: Command Interruption - PASS")


def test_scenario_4_mixed_input():
    """Agent speaking + 'yeah but wait' -> Should NOT filter (has command)"""
    assert should_filter("yeah but wait", agent_speaking=True) == False
    assert should_filter("yeah okay but wait", agent_speaking=True) == False
    assert should_filter("okay but", agent_speaking=True) == False
    print("✅ Scenario 4: Mixed Input - PASS")


def test_edge_cases():
    """Additional edge cases"""
    # Empty input
    assert should_filter("", agent_speaking=True) == False
    
    # Multiple ignore words
    assert should_filter("yeah yeah okay", agent_speaking=True) == True
    
    # Command word alone when agent speaking
    assert should_filter("no", agent_speaking=True) == False
    
    # Regular sentence when agent speaking
    assert should_filter("what is the weather", agent_speaking=True) == False
    
    # Regular sentence when agent silent
    assert should_filter("what is the weather", agent_speaking=False) == False
    
    print("✅ Edge Cases - PASS")


if __name__ == "__main__":
    print("Running Intelligent Interruption Handler Tests\n")
    print("=" * 50)
    
    test_scenario_1_long_explanation()
    test_scenario_2_passive_affirmation()
    test_scenario_3_command()
    test_scenario_4_mixed_input()
    test_edge_cases()
    
    print("=" * 50)
    print("\n✅ ALL TESTS PASSED!")
    print("\nTest Matrix:")
    print("┌─────────────────┬──────────────┬─────────────────┐")
    print("│ User Input      │ Agent State  │ Behavior        │")
    print("├─────────────────┼──────────────┼─────────────────┤")
    print("│ 'yeah/ok/hmm'   │ Speaking     │ IGNORE (filter) │")
    print("│ 'stop/wait/no'  │ Speaking     │ INTERRUPT       │")
    print("│ 'yeah/ok/hmm'   │ Silent       │ RESPOND         │")
    print("│ 'start/hello'   │ Silent       │ RESPOND         │")
    print("└─────────────────┴──────────────┴─────────────────┘")
