"""
Unit tests for the intelligent interruption handler.

Tests cover all 4 required scenarios from the assignment:
1. Agent speaking + filler words → IGNORE
2. Agent silent + filler words → PROCESS
3. Agent speaking + interrupt words → INTERRUPT
4. Agent speaking + mixed input → INTERRUPT
"""

import pytest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interrupt_handler import (
    InterruptionHandler,
    InterruptionConfig,
    normalize_and_tokenize,
    classify_utterance,
    contains_any_word,
    contains_only_words,
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def config():
    """Create test configuration."""
    return InterruptionConfig(
        filler_words={'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'mhm', 'right', 'aha', 'sure'},
        interrupt_words={'wait', 'stop', 'no', 'hold', 'pause'},
        debug=False,
    )


@pytest.fixture
def handler(config):
    """Create test handler."""
    return InterruptionHandler(config)


# ============================================================
# Utils Tests
# ============================================================

class TestNormalizeAndTokenize:
    """Tests for normalize_and_tokenize function."""
    
    def test_simple_words(self):
        assert normalize_and_tokenize("yeah ok") == ['yeah', 'ok']
    
    def test_with_punctuation(self):
        assert normalize_and_tokenize("Yeah, okay!") == ['yeah', 'okay']
    
    def test_with_ellipsis(self):
        assert normalize_and_tokenize("wait...stop") == ['wait', 'stop']
    
    def test_hyphenated_words(self):
        assert normalize_and_tokenize("uh-huh") == ['uh-huh']
    
    def test_empty_string(self):
        assert normalize_and_tokenize("") == []
    
    def test_whitespace_only(self):
        assert normalize_and_tokenize("   ") == []
    
    def test_mixed_case(self):
        assert normalize_and_tokenize("YEAH OK") == ['yeah', 'ok']
    
    def test_multiple_spaces(self):
        assert normalize_and_tokenize("yeah    ok") == ['yeah', 'ok']


class TestContainsAnyWord:
    """Tests for contains_any_word function."""
    
    def test_word_present(self):
        assert contains_any_word(['yeah', 'but'], {'yeah', 'ok'}) is True
    
    def test_word_absent(self):
        assert contains_any_word(['hello', 'there'], {'yeah', 'ok'}) is False
    
    def test_empty_words(self):
        assert contains_any_word([], {'yeah', 'ok'}) is False
    
    def test_empty_set(self):
        assert contains_any_word(['yeah'], set()) is False


class TestContainsOnlyWords:
    """Tests for contains_only_words function."""
    
    def test_all_in_set(self):
        assert contains_only_words(['yeah', 'ok'], {'yeah', 'ok', 'hmm'}) is True
    
    def test_not_all_in_set(self):
        assert contains_only_words(['yeah', 'but'], {'yeah', 'ok', 'hmm'}) is False
    
    def test_empty_words(self):
        assert contains_only_words([], {'yeah', 'ok'}) is False


class TestClassifyUtterance:
    """Tests for classify_utterance function."""
    
    def test_pure_filler(self):
        result = classify_utterance("yeah ok", {'yeah', 'ok'}, {'wait'})
        assert result == 'FILLER'
    
    def test_pure_interrupt(self):
        result = classify_utterance("wait stop", {'yeah'}, {'wait', 'stop'})
        assert result == 'INTERRUPT'
    
    def test_mixed_with_interrupt(self):
        result = classify_utterance("yeah but wait", {'yeah'}, {'wait'})
        assert result == 'INTERRUPT'
    
    def test_unknown_words(self):
        result = classify_utterance("hello there", {'yeah'}, {'wait'})
        assert result == 'UNKNOWN'
    
    def test_empty(self):
        result = classify_utterance("", {'yeah'}, {'wait'})
        assert result == 'EMPTY'
    
    def test_whitespace(self):
        result = classify_utterance("   ", {'yeah'}, {'wait'})
        assert result == 'EMPTY'


# ============================================================
# Handler Tests - Core Assignment Scenarios
# ============================================================

class TestScenario1LongExplanation:
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Expected Result: Agent audio does not break. It ignores the user input completely.
    """
    
    def test_filler_while_speaking_ignored(self, handler):
        handler.on_agent_speech_started()
        
        # All these should return False (do NOT interrupt)
        assert handler.should_interrupt("yeah") is False
        assert handler.should_interrupt("ok") is False
        assert handler.should_interrupt("okay") is False
        assert handler.should_interrupt("hmm") is False
        assert handler.should_interrupt("uh-huh") is False
        assert handler.should_interrupt("mhm") is False
    
    def test_multiple_fillers_while_speaking(self, handler):
        handler.on_agent_speech_started()
        
        assert handler.should_interrupt("yeah ok") is False
        assert handler.should_interrupt("okay yeah hmm") is False
        assert handler.should_interrupt("uh-huh, mhm") is False
    
    def test_filler_with_punctuation(self, handler):
        handler.on_agent_speech_started()
        
        assert handler.should_interrupt("yeah...") is False
        assert handler.should_interrupt("ok!") is False
        assert handler.should_interrupt("hmm?") is False


class TestScenario2PassiveAffirmation:
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Expected Result: Agent processes "Yeah" as an answer and proceeds.
    """
    
    def test_filler_while_silent_processed(self, handler):
        # Agent is NOT speaking (default state)
        assert handler.is_agent_speaking() is False
        
        # Filler words should be processed when agent is silent
        assert handler.should_interrupt("yeah") is True
        assert handler.should_interrupt("ok") is True
        assert handler.should_interrupt("sure") is True
    
    def test_after_agent_stops_speaking(self, handler):
        # Agent was speaking
        handler.on_agent_speech_started()
        assert handler.should_interrupt("yeah") is False  # Ignored
        
        # Agent stops speaking
        handler.on_agent_speech_ended()
        assert handler.should_interrupt("yeah") is True  # Now processed


class TestScenario3Correction:
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Expected Result: Agent cuts off immediately.
    """
    
    def test_interrupt_words_while_speaking(self, handler):
        handler.on_agent_speech_started()
        
        # Interrupt words should return True (interrupt the agent)
        assert handler.should_interrupt("stop") is True
        assert handler.should_interrupt("wait") is True
        assert handler.should_interrupt("no") is True
        assert handler.should_interrupt("hold") is True
        assert handler.should_interrupt("pause") is True
    
    def test_combined_interrupt_words(self, handler):
        handler.on_agent_speech_started()
        
        assert handler.should_interrupt("no stop") is True
        assert handler.should_interrupt("wait, hold on") is True


class TestScenario4MixedInput:
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Expected Result: Agent stops (because "but wait" is not in the ignore list).
    """
    
    def test_filler_plus_interrupt(self, handler):
        handler.on_agent_speech_started()
        
        assert handler.should_interrupt("yeah but wait") is True
        assert handler.should_interrupt("ok wait a second") is True
        assert handler.should_interrupt("hmm stop please") is True
    
    def test_filler_plus_unknown(self, handler):
        handler.on_agent_speech_started()
        
        # Non-filler content should trigger interrupt
        assert handler.should_interrupt("yeah but can you explain more") is True
        assert handler.should_interrupt("ok, tell me about that") is True


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_input(self, handler):
        handler.on_agent_speech_started()
        assert handler.should_interrupt("") is False
        assert handler.should_interrupt("   ") is False
    
    def test_partial_transcripts_disabled(self, handler):
        handler.on_agent_speech_started()
        # Partial transcripts should be ignored by default
        assert handler.should_interrupt("wait", is_final=False) is False
    
    def test_partial_transcripts_enabled(self, config):
        config.use_partial_transcripts = True
        handler = InterruptionHandler(config)
        handler.on_agent_speech_started()
        assert handler.should_interrupt("wait", is_final=False) is True
    
    def test_case_insensitivity(self, handler):
        handler.on_agent_speech_started()
        
        assert handler.should_interrupt("YEAH") is False
        assert handler.should_interrupt("STOP") is True
        assert handler.should_interrupt("Yeah OK") is False
        assert handler.should_interrupt("Wait STOP") is True
    
    def test_state_tracking(self, handler):
        assert handler.is_agent_speaking() is False
        
        handler.on_agent_speech_started()
        assert handler.is_agent_speaking() is True
        
        handler.on_agent_speech_ended()
        assert handler.is_agent_speaking() is False


# ============================================================
# Statistics Tests
# ============================================================

class TestStatistics:
    """Tests for handler statistics."""
    
    def test_stats_tracking(self, handler):
        handler.on_agent_speech_started()
        
        handler.should_interrupt("yeah")  # Ignored filler
        handler.should_interrupt("stop")  # Processed interrupt
        
        handler.on_agent_speech_ended()
        handler.should_interrupt("hello")  # Normal processing
        
        stats = handler.get_stats()
        assert stats['total_transcripts'] == 3
        assert stats['ignored_fillers'] == 1
        assert stats['processed_interrupts'] == 1
        assert stats['processed_normal'] == 1
    
    def test_stats_reset(self, handler):
        handler.should_interrupt("test")
        handler.reset_stats()
        
        stats = handler.get_stats()
        assert stats['total_transcripts'] == 0


# ============================================================
# Configuration Tests
# ============================================================

class TestConfiguration:
    """Tests for InterruptionConfig."""
    
    def test_default_config(self):
        config = InterruptionConfig()
        assert 'yeah' in config.filler_words
        assert 'ok' in config.filler_words
        assert 'wait' in config.interrupt_words
        assert 'stop' in config.interrupt_words
    
    def test_custom_config(self):
        config = InterruptionConfig(
            filler_words={'custom', 'words'},
            interrupt_words={'halt'},
        )
        assert config.filler_words == {'custom', 'words'}
        assert config.interrupt_words == {'halt'}
    
    def test_case_normalization(self):
        config = InterruptionConfig(
            filler_words={'YEAH', 'OK'},
            interrupt_words={'STOP'},
        )
        assert 'yeah' in config.filler_words
        assert 'ok' in config.filler_words
        assert 'stop' in config.interrupt_words


# ============================================================
# Run tests directly
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
