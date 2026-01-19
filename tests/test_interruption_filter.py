"""
Unit tests for intelligent interruption filtering.

Tests the semantic classification logic for distinguishing:
- Soft acknowledgments (should be ignored when agent speaking)
- Hard interrupt commands (should immediately stop agent)
- Mixed inputs (should trigger interruption)
"""

import pytest

from livekit.agents.voice.interruption_filter import (
    HARD_INTERRUPT_WORDS,
    SOFT_ACKNOWLEDGMENT_WORDS,
    should_ignore_as_soft_acknowledgment,
)


class TestSoftAcknowledgmentDetection:
    """Test detection of soft acknowledgment words."""

    def test_single_soft_word_when_agent_speaking(self):
        """Single soft acknowledgment while agent speaking should be ignored."""
        assert should_ignore_as_soft_acknowledgment("yeah", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("ok", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("hmm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("uh-huh", agent_speaking=True) is True

    def test_multiple_soft_words_when_agent_speaking(self):
        """Multiple soft words while agent speaking should be ignored."""
        assert should_ignore_as_soft_acknowledgment("yeah ok", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("mm-hmm right", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("ok okay sure", agent_speaking=True) is True

    def test_soft_words_when_agent_silent(self):
        """Soft words when agent is silent should NOT be ignored (processed normally)."""
        assert should_ignore_as_soft_acknowledgment("yeah", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("ok", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("hmm", agent_speaking=False) is False

    def test_soft_words_with_punctuation(self):
        """Soft words with punctuation should still be recognized."""
        assert should_ignore_as_soft_acknowledgment("yeah!", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("ok.", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("hmm...", agent_speaking=True) is True

    def test_soft_words_with_whitespace(self):
        """Soft words with extra whitespace should be handled."""
        assert should_ignore_as_soft_acknowledgment("  yeah  ", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("\\tok\\n", agent_speaking=True) is True


class TestHardInterruptDetection:
    """Test detection of hard interrupt commands."""

    def test_single_interrupt_word_when_agent_speaking(self):
        """Single interrupt word while agent speaking should NOT be ignored."""
        assert should_ignore_as_soft_acknowledgment("stop", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("wait", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("no", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("pause", agent_speaking=True) is False

    def test_interrupt_words_case_insensitive(self):
        """Interrupt words should work case-insensitively."""
        assert should_ignore_as_soft_acknowledgment("STOP", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("Wait", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("NO", agent_speaking=True) is False

    def test_interrupt_contractions(self):
        """Contractions like don't should be recognized."""
        assert should_ignore_as_soft_acknowledgment("don't", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("dont", agent_speaking=True) is False


class TestMixedInputDetection:
    """Test detection of mixed inputs (soft + other content)."""

    def test_soft_plus_interrupt_word(self):
        """Soft word + interrupt word should NOT be ignored."""
        assert should_ignore_as_soft_acknowledgment("yeah but stop", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("ok wait", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("hmm no", agent_speaking=True) is False

    def test_soft_plus_other_content(self):
        """Soft word + other content should NOT be ignored."""
        assert should_ignore_as_soft_acknowledgment("yeah tell me more", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("ok what about", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("hmm interesting", agent_speaking=True) is False

    def test_interrupt_plus_soft_word(self):
        """Interrupt word + soft word should NOT be ignored (interrupt takes precedence)."""
        assert should_ignore_as_soft_acknowledgment("stop yeah", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("wait ok", agent_speaking=True) is False


class TestPhoneticUtteranceDetection:
    """Test detection of phonetic utterances (mmhm fragments)."""

    def test_single_phoneme_fragments(self):
        """Single phoneme fragments like 'mm', 'hm' should be ignored."""
        assert should_ignore_as_soft_acknowledgment("mm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("hm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("uh", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("um", agent_speaking=True) is True

    def test_repeated_phonemes(self):
        """Repeated phonemes like 'mmm', 'hhh' should be ignored."""
        assert should_ignore_as_soft_acknowledgment("mmm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("mmmm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("hh", agent_speaking=True) is True

    def test_spaced_phonemes(self):
        """Space-separated phonemes like 'mm hm' should be ignored."""
        assert should_ignore_as_soft_acknowledgment("mm hm", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("uh um", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("m h m", agent_speaking=True) is True

    def test_phonemes_with_punctuation(self):
        """Phonemes with punctuation should still be recognized."""
        assert should_ignore_as_soft_acknowledgment("mm.", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("hm!", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("mm-hm", agent_speaking=True) is True

    def test_phonemes_when_agent_silent(self):
        """Phonemes when agent is silent should NOT be ignored."""
        assert should_ignore_as_soft_acknowledgment("mm", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("hm", agent_speaking=False) is False

    def test_non_phonetic_words(self):
        """Non-phonetic words should NOT be treated as phonetic utterances."""
        assert should_ignore_as_soft_acknowledgment("hello", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("yes", agent_speaking=True) is True  # soft word
        assert should_ignore_as_soft_acknowledgment("home", agent_speaking=True) is False



class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_transcript(self):
        """Empty transcript should be ignored."""
        assert should_ignore_as_soft_acknowledgment("", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("   ", agent_speaking=True) is True

    def test_punctuation_only(self):
        """Punctuation-only transcript should be ignored."""
        assert should_ignore_as_soft_acknowledgment("...", agent_speaking=True) is True
        assert should_ignore_as_soft_acknowledgment("!!!", agent_speaking=True) is True

    def test_numbers_when_agent_speaking(self):
        """Numbers should NOT be ignored (not soft acknowledgment)."""
        assert should_ignore_as_soft_acknowledgment("5", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("123", agent_speaking=True) is False

    def test_unknown_words_when_agent_speaking(self):
        """Unknown words should NOT be ignored."""
        assert should_ignore_as_soft_acknowledgment("hello", agent_speaking=True) is False
        assert should_ignore_as_soft_acknowledgment("world", agent_speaking=True) is False

    def test_agent_silent_processes_everything(self):
        """When agent is silent, ALL inputs should be processed (not ignored)."""
        assert should_ignore_as_soft_acknowledgment("yeah", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("stop", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("hello", agent_speaking=False) is False
        assert should_ignore_as_soft_acknowledgment("", agent_speaking=False) is False


class TestWordLists:
    """Test that word lists are properly configured."""

    def test_soft_words_not_empty(self):
        """SOFT_ACKNOWLEDGMENT_WORDS should have default values."""
        assert len(SOFT_ACKNOWLEDGMENT_WORDS) > 0
        assert "yeah" in SOFT_ACKNOWLEDGMENT_WORDS
        assert "ok" in SOFT_ACKNOWLEDGMENT_WORDS

    def test_interrupt_words_not_empty(self):
        """HARD_INTERRUPT_WORDS should have default values."""
        assert len(HARD_INTERRUPT_WORDS) > 0
        assert "stop" in HARD_INTERRUPT_WORDS
        assert "wait" in HARD_INTERRUPT_WORDS

    def test_no_overlap_between_lists(self):
        """Soft and hard word lists should not overlap."""
        overlap = SOFT_ACKNOWLEDGMENT_WORDS.intersection(HARD_INTERRUPT_WORDS)
        assert len(overlap) == 0, f"Found overlap: {overlap}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
