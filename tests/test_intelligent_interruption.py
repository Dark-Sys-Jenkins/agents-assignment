"""
Tests for the intelligent interruption handling feature.

This module tests the backchannel word filtering logic that prevents
short acknowledgement words from interrupting the agent while speaking.
"""

import pytest

from livekit.agents.voice.agent_session import DEFAULT_IGNORED_WORDS


class TestSoftInputDetection:
    """Tests for the _is_soft_input method logic."""

    def test_default_ignored_words_contains_common_backchannels(self):
        """Verify default ignored words list contains common backchannel words."""
        expected_words = ["yeah", "ok", "hmm", "right", "uh-huh"]
        for word in expected_words:
            assert word in DEFAULT_IGNORED_WORDS, f"Expected '{word}' in DEFAULT_IGNORED_WORDS"

    def test_ignored_words_list_is_not_empty(self):
        """Verify the default ignored words list is not empty."""
        assert len(DEFAULT_IGNORED_WORDS) > 0

    def test_ignored_words_are_lowercase(self):
        """Verify all default ignored words are lowercase for consistent matching."""
        for word in DEFAULT_IGNORED_WORDS:
            assert word == word.lower(), f"Expected '{word}' to be lowercase"


class TestBackchannelWordMatching:
    """Tests for backchannel word matching logic."""

    @pytest.fixture
    def ignored_words_set(self):
        """Create a set of ignored words for testing."""
        return set(w.lower() for w in DEFAULT_IGNORED_WORDS)

    def _is_soft_input(self, text: str, ignored_words: set) -> bool:
        """
        Simplified version of the _is_soft_input logic for testing.
        Mirrors the implementation in AgentActivity.
        """
        import re

        if not text:
            return True

        if not ignored_words:
            return False

        normalized = text.lower().strip()
        words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", normalized)

        if not words:
            return True

        return all(word in ignored_words for word in words)

    def test_single_backchannel_word_is_soft(self, ignored_words_set):
        """Test that single backchannel words are detected as soft input."""
        soft_inputs = ["yeah", "ok", "hmm", "right", "uh-huh", "mhm", "sure"]
        for word in soft_inputs:
            if word.replace("-", "") in ignored_words_set or word in ignored_words_set:
                # Handle hyphenated words like "uh-huh"
                assert self._is_soft_input(word, ignored_words_set), f"'{word}' should be soft input"

    def test_multiple_backchannel_words_is_soft(self, ignored_words_set):
        """Test that multiple backchannel words together are still soft input."""
        # "yeah ok" - both are backchannel words
        assert self._is_soft_input("yeah ok", ignored_words_set)
        assert self._is_soft_input("ok sure", ignored_words_set)
        assert self._is_soft_input("hmm yeah", ignored_words_set)

    def test_command_word_is_not_soft(self, ignored_words_set):
        """Test that command words are NOT detected as soft input."""
        command_inputs = ["stop", "wait", "no", "hello", "start", "help"]
        for word in command_inputs:
            assert not self._is_soft_input(word, ignored_words_set), f"'{word}' should NOT be soft input"

    def test_mixed_input_is_not_soft(self, ignored_words_set):
        """Test that mixed input (backchannel + command) is NOT soft input."""
        mixed_inputs = [
            "yeah wait",
            "ok stop",
            "hmm but wait",
            "yeah okay but wait a second",
            "sure but no",
        ]
        for text in mixed_inputs:
            assert not self._is_soft_input(text, ignored_words_set), f"'{text}' should NOT be soft input"

    def test_empty_input_is_soft(self, ignored_words_set):
        """Test that empty input is treated as soft."""
        assert self._is_soft_input("", ignored_words_set)
        assert self._is_soft_input("   ", ignored_words_set)

    def test_case_insensitive_matching(self, ignored_words_set):
        """Test that matching is case-insensitive."""
        assert self._is_soft_input("YEAH", ignored_words_set)
        assert self._is_soft_input("Yeah", ignored_words_set)
        assert self._is_soft_input("OK", ignored_words_set)
        assert self._is_soft_input("Ok", ignored_words_set)

    def test_punctuation_is_ignored(self, ignored_words_set):
        """Test that punctuation doesn't affect matching."""
        assert self._is_soft_input("yeah!", ignored_words_set)
        assert self._is_soft_input("ok.", ignored_words_set)
        assert self._is_soft_input("hmm...", ignored_words_set)
        assert self._is_soft_input("yeah, ok", ignored_words_set)

    def test_question_with_command_is_not_soft(self, ignored_words_set):
        """Test that questions with non-backchannel words are not soft."""
        assert not self._is_soft_input("what?", ignored_words_set)
        assert not self._is_soft_input("can you repeat that?", ignored_words_set)
        assert not self._is_soft_input("wait what?", ignored_words_set)
