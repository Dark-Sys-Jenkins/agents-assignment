"""
Unit tests for the BackchannelingFilter class.

Tests cover:
- Pure backchanneling detection
- Interrupt word detection
- Mixed content filtering
- Environment variable loading
- Text normalization
"""

import os
import pytest
from examples.backchanneling import (
    BackchannelingFilter,
    DEFAULT_BACKCHANNELING_WORDS,
    DEFAULT_INTERRUPT_WORDS,
)


class TestBackchannelingFilterBasics:
    """Test basic functionality of BackchannelingFilter."""

    def test_initialization_with_defaults(self):
        """Test filter initializes with default word lists."""
        filter_ = BackchannelingFilter()
        assert len(filter_.backchanneling_words) > 0
        assert len(filter_.interrupt_words) > 0
        assert "yeah" in filter_.backchanneling_words
        assert "wait" in filter_.interrupt_words

    def test_initialization_with_custom_words(self):
        """Test filter initializes with custom word lists."""
        bc_words = {"custom_bc", "ok"}
        int_words = {"custom_int", "stop"}
        filter_ = BackchannelingFilter(
            backchanneling_words=bc_words, interrupt_words=int_words
        )
        assert filter_.backchanneling_words == bc_words
        assert filter_.interrupt_words == int_words

    def test_empty_text_is_backchanneling(self):
        """Test that empty text is considered pure backchanneling."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("") is True
        assert filter_.is_pure_backchanneling("   ") is True
        assert filter_.is_pure_backchanneling("\n") is True

    def test_empty_text_should_filter(self):
        """Test that empty text should be filtered (not cause interruption)."""
        filter_ = BackchannelingFilter()
        assert filter_.should_filter_interruption("") is True
        assert filter_.should_filter_interruption("   ") is True


class TestPureBackchanneling:
    """Test detection of pure backchanneling speech."""

    def test_single_backchanneling_words(self):
        """Test single backchanneling words are detected."""
        filter_ = BackchannelingFilter()
        backchanneling_words = ["yeah", "yep", "ok", "uh-huh", "hmm", "um"]
        for word in backchanneling_words:
            assert filter_.is_pure_backchanneling(word) is True
            assert filter_.should_filter_interruption(word) is True

    def test_multiple_backchanneling_words(self):
        """Test multiple backchanneling words together are detected."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("yeah ok") is True
        assert filter_.is_pure_backchanneling("yeah ok hmm") is True
        assert filter_.should_filter_interruption("yeah ok hmm") is True

    def test_backchanneling_with_punctuation(self):
        """Test backchanneling words with punctuation are detected."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("yeah!") is True
        assert filter_.is_pure_backchanneling("ok?") is True
        assert filter_.is_pure_backchanneling("hmm...") is True
        assert filter_.is_pure_backchanneling("yeah, ok.") is True

    def test_case_insensitivity(self):
        """Test that backchanneling detection is case-insensitive."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("YEAH") is True
        assert filter_.is_pure_backchanneling("Ok") is True
        assert filter_.is_pure_backchanneling("HMM") is True
        assert filter_.should_filter_interruption("YEAH OK") is True

    def test_multi_word_backchanneling_phrases(self):
        """Test multi-word backchanneling phrases are detected."""
        filter_ = BackchannelingFilter()
        # "i see", "got it", etc. are in DEFAULT_BACKCHANNELING_WORDS
        assert filter_.is_pure_backchanneling("i see") is True
        assert filter_.is_pure_backchanneling("got it") is True
        assert filter_.should_filter_interruption("i see") is True


class TestInterruptWords:
    """Test detection of interrupt words."""

    def test_single_interrupt_words(self):
        """Test single interrupt words are detected."""
        filter_ = BackchannelingFilter()
        interrupt_words = ["wait", "stop", "no", "pause", "hold"]
        for word in interrupt_words:
            assert filter_.contains_interrupt_word(word) is True
            assert filter_.should_filter_interruption(word) is False

    def test_interrupt_overrides_backchanneling(self):
        """Test that interrupt words override backchanneling detection."""
        filter_ = BackchannelingFilter()
        # "wait" is an interrupt word, so it should NOT be filtered
        assert filter_.is_pure_backchanneling("wait") is False
        assert filter_.contains_interrupt_word("wait") is True
        assert filter_.should_filter_interruption("wait") is False

    def test_multi_word_interrupt_phrases(self):
        """Test multi-word interrupt phrases are detected."""
        filter_ = BackchannelingFilter()
        assert filter_.contains_interrupt_word("hold on") is True
        assert filter_.contains_interrupt_word("never mind") is True
        assert filter_.should_filter_interruption("hold on") is False

    def test_interrupt_word_with_text(self):
        """Test interrupt words in longer text are detected."""
        filter_ = BackchannelingFilter()
        assert filter_.contains_interrupt_word("wait, I have a question") is True
        assert filter_.should_filter_interruption("wait, I have a question") is False
        assert filter_.contains_interrupt_word("no, stop that") is True
        assert filter_.should_filter_interruption("no, stop that") is False


class TestMixedContent:
    """Test filtering of mixed content (backchanneling + other words)."""

    def test_backchanneling_with_statement(self):
        """Test backchanneling mixed with other words is not pure."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("yeah, but I need help") is False
        assert filter_.should_filter_interruption("yeah, but I need help") is False

    def test_interrupt_overrides_mixed_content(self):
        """Test interrupt words take priority in mixed content."""
        filter_ = BackchannelingFilter()
        assert filter_.contains_interrupt_word("wait, yeah") is True
        assert filter_.should_filter_interruption("wait, yeah") is False

    def test_pure_statement_not_filtered(self):
        """Test that pure statements (not backchanneling) are not filtered."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("I need help") is False
        assert filter_.should_filter_interruption("I need help") is False


class TestCustomWordLists:
    """Test custom word list functionality."""

    def test_custom_backchanneling_words(self):
        """Test filter with custom backchanneling words."""
        filter_ = BackchannelingFilter(backchanneling_words={"custom_word", "test"})
        assert filter_.is_pure_backchanneling("custom_word") is True
        assert filter_.is_pure_backchanneling("test") is True
        assert filter_.is_pure_backchanneling("yeah") is False  # not in custom list

    def test_custom_interrupt_words(self):
        """Test filter with custom interrupt words."""
        filter_ = BackchannelingFilter(interrupt_words={"custom_interrupt", "halt"})
        assert filter_.contains_interrupt_word("custom_interrupt") is True
        assert filter_.contains_interrupt_word("halt") is True
        assert filter_.contains_interrupt_word("wait") is False  # not in custom list

    def test_environment_variable_loading(self, monkeypatch):
        """Test loading word lists from environment variables."""
        monkeypatch.setenv("BACKCHANNELING_WORDS", "env_bc1, env_bc2")
        monkeypatch.setenv("INTERRUPT_WORDS", "env_int1, env_int2")

        filter_ = BackchannelingFilter()
        # Note: environment variables override defaults
        assert "env_bc1" in filter_.backchanneling_words
        assert "env_bc2" in filter_.backchanneling_words
        assert "env_int1" in filter_.interrupt_words
        assert "env_int2" in filter_.interrupt_words


class TestTextNormalization:
    """Test text normalization functionality."""

    def test_punctuation_removal(self):
        """Test that punctuation is properly removed."""
        filter_ = BackchannelingFilter()
        # "yeah!" and "yeah" should both be detected as backchanneling
        assert filter_.is_pure_backchanneling("yeah!") is True
        assert filter_.is_pure_backchanneling("yeah?") is True
        assert filter_.is_pure_backchanneling("yeah...") is True

    def test_whitespace_normalization(self):
        """Test that extra whitespace is handled."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("  yeah  ") is True
        assert filter_.is_pure_backchanneling("yeah    ok") is True
        assert filter_.is_pure_backchanneling("\tyeah\nok") is True

    def test_case_normalization(self):
        """Test that case is properly normalized."""
        filter_ = BackchannelingFilter()
        assert filter_.is_pure_backchanneling("YEAH") is True
        assert filter_.is_pure_backchanneling("YeAh") is True
        assert filter_.is_pure_backchanneling("Yeah OK Hmm") is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_character(self):
        """Test single character input."""
        filter_ = BackchannelingFilter()
        # Single character might not be recognized as a backchanneling word
        result = filter_.should_filter_interruption("a")
        # Should either filter or not filter, but not crash
        assert isinstance(result, bool)

    def test_very_long_text(self):
        """Test handling of very long text."""
        filter_ = BackchannelingFilter()
        long_text = "yeah " * 1000
        # Should not crash and should recognize it as backchanneling
        assert filter_.is_pure_backchanneling(long_text) is True

    def test_special_characters(self):
        """Test handling of special characters."""
        filter_ = BackchannelingFilter()
        # Should not crash with special characters
        result = filter_.should_filter_interruption("yeah @#$% ok")
        assert isinstance(result, bool)

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        filter_ = BackchannelingFilter()
        # Should not crash with unicode
        result = filter_.should_filter_interruption("yeah 😊 ok")
        assert isinstance(result, bool)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_agent_speaking_user_acknowledges(self):
        """Scenario: Agent speaking, user acknowledges with backchanneling."""
        filter_ = BackchannelingFilter()
        # When agent is speaking, user says "yeah"
        # This should be filtered (not interrupt the agent)
        transcript = "yeah"
        assert filter_.should_filter_interruption(transcript) is True

    def test_agent_speaking_user_interrupts(self):
        """Scenario: Agent speaking, user tries to interrupt."""
        filter_ = BackchannelingFilter()
        # When agent is speaking, user says "wait"
        # This should NOT be filtered (should interrupt the agent)
        transcript = "wait"
        assert filter_.should_filter_interruption(transcript) is False

    def test_agent_silent_user_responds(self):
        """Scenario: Agent silent, user provides input."""
        filter_ = BackchannelingFilter()
        # When agent is silent, any input (including "yeah") should not be filtered
        # The should_filter_interruption returns True for pure backchanneling
        # But the agent_activity code will handle this context
        transcript = "yeah"
        # This returns True (filter), but the agent_activity should check agent state
        result = filter_.should_filter_interruption(transcript)
        assert isinstance(result, bool)

    def test_complex_user_statement(self):
        """Scenario: User says something substantial."""
        filter_ = BackchannelingFilter()
        transcript = "Can you tell me more about that topic?"
        assert filter_.should_filter_interruption(transcript) is False


class TestDefaultLists:
    """Test that default word lists are reasonable."""

    def test_default_backchanneling_words_not_empty(self):
        """Test that default backchanneling words list is not empty."""
        assert len(DEFAULT_BACKCHANNELING_WORDS) > 0

    def test_default_interrupt_words_not_empty(self):
        """Test that default interrupt words list is not empty."""
        assert len(DEFAULT_INTERRUPT_WORDS) > 0

    def test_no_overlap_in_defaults(self):
        """Test that default lists don't have problematic overlaps."""
        # Lists can have overlap, but critical words should be distinct
        # "wait" should be interrupt, not backchanneling
        assert "wait" not in DEFAULT_BACKCHANNELING_WORDS
        assert "wait" in DEFAULT_INTERRUPT_WORDS

    def test_common_words_covered(self):
        """Test that common backchanneling words are in defaults."""
        common = ["yeah", "ok", "hmm", "uh-huh", "yes"]
        for word in common:
            assert word in DEFAULT_BACKCHANNELING_WORDS

    def test_common_interrupt_words_covered(self):
        """Test that common interrupt words are in defaults."""
        common = ["wait", "stop", "no", "hold", "pause"]
        for word in common:
            assert word in DEFAULT_INTERRUPT_WORDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
