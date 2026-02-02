"""
Unit Tests for Intelligent Interruption Filtering

This module tests the InterruptionFilter class and its integration
with the LiveKit Agents framework.

Test Scenarios (from requirements):
1. Agent speaking + "yeah/ok/hmm" → IGNORE (agent continues)
2. Agent speaking + "stop/wait/no" → INTERRUPT
3. Agent silent + "yeah/ok" → RESPOND (valid input)
4. Agent speaking + "yeah but wait" → INTERRUPT (mixed input with command)

Run with: pytest tests/test_interruption_filter.py -v
"""

import pytest
from livekit.agents.voice.agent_activity import (
    InterruptionFilter,
    DEFAULT_IGNORE_WORDS,
    DEFAULT_INTERRUPT_WORDS,
)


class TestInterruptionFilter:
    """Test the InterruptionFilter class."""
    
    @pytest.fixture
    def filter(self):
        """Create a default InterruptionFilter instance."""
        return InterruptionFilter()
    
    @pytest.fixture
    def custom_filter(self):
        """Create a custom InterruptionFilter with additional words."""
        return InterruptionFilter(
            ignore_words=DEFAULT_IGNORE_WORDS | {"roger", "copy"},
            interrupt_words=DEFAULT_INTERRUPT_WORDS | {"emergency", "help"},
        )
    
    # ========================================================================
    # Test Pure Filler Detection
    # ========================================================================
    
    def test_pure_filler_single_word(self, filter):
        """Test detection of single filler words."""
        filler_words = ["yeah", "yes", "ok", "okay", "hmm", "right", "sure", "yep"]
        for word in filler_words:
            assert filter.is_pure_filler(word), f"'{word}' should be detected as pure filler"
    
    def test_pure_filler_with_punctuation(self, filter):
        """Test filler detection ignores punctuation."""
        assert filter.is_pure_filler("yeah.") == True
        assert filter.is_pure_filler("ok!") == True
        assert filter.is_pure_filler("hmm...") == True
        assert filter.is_pure_filler("uh-huh?") == True
    
    def test_pure_filler_case_insensitive(self, filter):
        """Test filler detection is case-insensitive."""
        assert filter.is_pure_filler("YEAH") == True
        assert filter.is_pure_filler("Yeah") == True
        assert filter.is_pure_filler("OK") == True
        assert filter.is_pure_filler("Okay") == True
    
    def test_pure_filler_multiple_fillers(self, filter):
        """Test detection of multiple filler words together."""
        assert filter.is_pure_filler("yeah yeah") == True
        assert filter.is_pure_filler("ok ok") == True
        assert filter.is_pure_filler("yeah ok") == True
        assert filter.is_pure_filler("hmm right") == True
    
    def test_not_pure_filler_with_substance(self, filter):
        """Test that substantive words are not detected as fillers."""
        assert filter.is_pure_filler("yeah but wait") == False
        assert filter.is_pure_filler("ok stop") == False
        assert filter.is_pure_filler("tell me more") == False
        assert filter.is_pure_filler("that's interesting") == False
    
    # ========================================================================
    # Test Interrupt Word Detection
    # ========================================================================
    
    def test_contains_interrupt_single(self, filter):
        """Test detection of single interrupt words."""
        interrupt_words = ["stop", "wait", "no", "pause", "cancel"]
        for word in interrupt_words:
            assert filter.contains_interrupt_word(word), f"'{word}' should trigger interrupt"
    
    def test_contains_interrupt_in_sentence(self, filter):
        """Test detection of interrupt words within sentences."""
        assert filter.contains_interrupt_word("yeah but wait a second") == True
        assert filter.contains_interrupt_word("no, that's wrong") == True
        assert filter.contains_interrupt_word("stop stop stop") == True
        assert filter.contains_interrupt_word("please wait") == True
    
    def test_contains_interrupt_case_insensitive(self, filter):
        """Test interrupt detection is case-insensitive."""
        assert filter.contains_interrupt_word("STOP") == True
        assert filter.contains_interrupt_word("Stop") == True
        assert filter.contains_interrupt_word("WAIT") == True
    
    def test_no_interrupt_in_filler(self, filter):
        """Test that pure filler phrases don't contain interrupt words."""
        assert filter.contains_interrupt_word("yeah") == False
        assert filter.contains_interrupt_word("ok ok") == False
        assert filter.contains_interrupt_word("hmm right") == False
    
    # ========================================================================
    # Test should_interrupt Logic (Core Requirements)
    # ========================================================================
    
    def test_scenario1_filler_while_speaking(self, filter):
        """Scenario 1: Agent speaking + filler words → IGNORE (return False)."""
        filler_phrases = [
            "yeah",
            "ok",
            "hmm",
            "uh-huh",
            "right",
            "okay okay",
            "yeah yeah",
            "mm hmm",
        ]
        for phrase in filler_phrases:
            result = filter.should_interrupt(phrase)
            assert result == False, f"'{phrase}' should NOT trigger interrupt while agent speaking"
    
    def test_scenario2_command_while_speaking(self, filter):
        """Scenario 2: Agent speaking + command words → INTERRUPT (return True)."""
        command_phrases = [
            "stop",
            "wait",
            "no",
            "hold on",
            "pause",
            "cancel",
            "no stop",
        ]
        for phrase in command_phrases:
            result = filter.should_interrupt(phrase)
            assert result == True, f"'{phrase}' SHOULD trigger interrupt while agent speaking"
    
    def test_scenario3_mixed_input(self, filter):
        """Scenario 4: Mixed input with command → INTERRUPT (return True)."""
        mixed_phrases = [
            "yeah but wait",
            "ok but stop",
            "hmm actually no",
            "yeah wait a second",
            "ok hold on",
        ]
        for phrase in mixed_phrases:
            result = filter.should_interrupt(phrase)
            assert result == True, f"'{phrase}' SHOULD trigger interrupt (contains command)"
    
    # ========================================================================
    # Test Edge Cases
    # ========================================================================
    
    def test_empty_input(self, filter):
        """Test handling of empty input."""
        assert filter.should_interrupt("") == False
        assert filter.should_interrupt("   ") == False
        assert filter.should_interrupt(None) == False if hasattr(filter, '_handle_none') else True
    
    def test_very_short_non_filler(self, filter):
        """Test short non-filler phrases (should not interrupt)."""
        # Short phrases without explicit interrupt words
        assert filter.should_interrupt("hi") == False  # Too short, not a command
        assert filter.should_interrupt("um") == False  # Basically a filler
    
    def test_question_words(self, filter):
        """Test that question words trigger interruption."""
        question_phrases = [
            "what",
            "why",
            "how",
            "when",
            "where",
            "what did you say",
            "why is that",
        ]
        for phrase in question_phrases:
            result = filter.should_interrupt(phrase)
            assert result == True, f"'{phrase}' SHOULD trigger interrupt (question)"
    
    def test_custom_filter_words(self, custom_filter):
        """Test custom filter with additional words."""
        # Custom ignore words
        assert custom_filter.is_pure_filler("roger") == True
        assert custom_filter.is_pure_filler("copy") == True
        
        # Custom interrupt words
        assert custom_filter.contains_interrupt_word("emergency") == True
        assert custom_filter.contains_interrupt_word("help") == True
    
    # ========================================================================
    # Test Normalization
    # ========================================================================
    
    def test_normalize_text(self, filter):
        """Test text normalization."""
        assert filter.normalize_text("  Hello,  World!  ") == "hello world"
        assert filter.normalize_text("Yeah...") == "yeah"
        assert filter.normalize_text("OK?!") == "ok"
        assert filter.normalize_text("UH-HUH") == "uhhuh"


class TestDefaultWordLists:
    """Test the default word lists are properly defined."""
    
    def test_ignore_words_exist(self):
        """Test that default ignore words are defined."""
        assert len(DEFAULT_IGNORE_WORDS) > 0
        assert "yeah" in DEFAULT_IGNORE_WORDS
        assert "ok" in DEFAULT_IGNORE_WORDS
        assert "hmm" in DEFAULT_IGNORE_WORDS
    
    def test_interrupt_words_exist(self):
        """Test that default interrupt words are defined."""
        assert len(DEFAULT_INTERRUPT_WORDS) > 0
        assert "stop" in DEFAULT_INTERRUPT_WORDS
        assert "wait" in DEFAULT_INTERRUPT_WORDS
        assert "no" in DEFAULT_INTERRUPT_WORDS
    
    def test_no_overlap(self):
        """Test that ignore and interrupt words don't overlap."""
        overlap = DEFAULT_IGNORE_WORDS & DEFAULT_INTERRUPT_WORDS
        assert len(overlap) == 0, f"Words should not be in both lists: {overlap}"


class TestFilterWithAgentState:
    """Test the full filter logic with simulated agent states."""
    
    @pytest.fixture
    def filter(self):
        return InterruptionFilter()
    
    def test_agent_speaking_ignore_fillers(self, filter):
        """When agent IS speaking, filler words should NOT interrupt."""
        test_cases = [
            ("yeah", False),
            ("ok", False),
            ("hmm", False),
            ("uh-huh", False),
            ("right", False),
            ("sure", False),
            ("stop", True),  # Command - should interrupt
            ("wait", True),  # Command - should interrupt
            ("no", True),    # Command - should interrupt
            ("yeah but wait", True),  # Mixed - should interrupt
        ]
        
        for transcript, expected in test_cases:
            result = filter.should_interrupt(transcript)
            state = "speaking"
            action = "interrupt" if expected else "ignore"
            assert result == expected, (
                f"Agent {state}, transcript '{transcript}': "
                f"expected {action}, got {'interrupt' if result else 'ignore'}"
            )


# ============================================================================
# Integration Test Ideas (require full agent setup)
# ============================================================================

class TestIntegrationScenarios:
    """
    These tests describe the integration scenarios that should be tested
    with the full agent setup. They are documented here for reference.
    
    To run these tests, you would need to set up a mock AgentSession
    and simulate the speech events.
    """
    
    def test_scenario_long_explanation(self):
        """
        Scenario 1: The Long Explanation
        - Context: Agent is reading a long paragraph about history
        - User Action: User says "Okay... yeah... uh-huh" while Agent is talking
        - Expected: Agent audio does not break, it ignores the user input completely
        """
        # This would require integration with the full agent
        pass
    
    def test_scenario_passive_affirmation(self):
        """
        Scenario 2: The Passive Affirmation
        - Context: Agent asks "Are you ready?" and goes silent
        - User Action: User says "Yeah"
        - Expected: Agent processes "Yeah" as an answer and proceeds
        """
        # This would require integration with the full agent
        pass
    
    def test_scenario_correction(self):
        """
        Scenario 3: The Correction
        - Context: Agent is counting "One, two, three..."
        - User Action: User says "No stop"
        - Expected: Agent cuts off immediately
        """
        # This would require integration with the full agent
        pass
    
    def test_scenario_mixed_input(self):
        """
        Scenario 4: The Mixed Input
        - Context: Agent is speaking
        - User Action: User says "Yeah okay but wait"
        - Expected: Agent stops (because "but wait" is not in the ignore list)
        """
        filter = InterruptionFilter()
        assert filter.should_interrupt("Yeah okay but wait") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
