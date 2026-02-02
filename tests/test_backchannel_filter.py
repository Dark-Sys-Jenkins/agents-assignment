"""
Unit test's for backchannel filtering check.

The tests verify that the backchannel logic is correct or not:
1. Identifies single word backchannels like (yeah, ok, hmm, etc.)
2. Identifies multi word backchannels like (ok ok ok, yeah yeah)
3. Detects command words that should NOT be ignored like (stop, wait, hold on, etc.)
4. Handles mixed inputs like (yeah wait a second, etc.)
5. Handles edge cases and normalization like (etc.)
"""

import pytest
from livekit.agents.voice.backchannel_filter import (
    is_backchannel,
    contains_command_words,
    is_likely_continuation,
    normalize_transcript,
    DEFAULT_BACKCHANNEL_WORDS,
    COMMAND_WORDS,
)


class TestNormalizeTranscript:
    # Tests for transcript normalization.

    def test_lowercase_conversion(self):
        assert normalize_transcript("YEAH") == "yeah"
        assert normalize_transcript("OK") == "ok"

    def test_strip_whitespace(self):
        assert normalize_transcript("  yeah  ") == "yeah"
        assert normalize_transcript("\tyeah\n") == "yeah"

    def test_remove_punctuation(self):
        assert normalize_transcript("yeah!") == "yeah"
        assert normalize_transcript("ok.") == "ok"
        assert normalize_transcript("hmm?") == "hmm"
        assert normalize_transcript("yeah, ok") == "yeah ok"

    def test_collapse_multiple_spaces(self):
        assert normalize_transcript("yeah   ok") == "yeah ok"


class TestIsBackchannel:
    # Tests for backchannel detection.

    # Test Scenario 1: Single word backchannels
    @pytest.mark.parametrize("word", [
        "yeah", "yea", "ya", "yep", "yup", "yes",
        "ok", "okay", "okie", "k", "kay",
        "right", "alright",
        "aha", "hmm", "hm", "mhm", "mmhmm",
        "uhuh",
        "got it", "gotcha",
        "i see", "oh", "cool", "nice", "great",
        "uh", "um", "er", "ah"
    ])
    def test_single_word_backchannels(self, word):
        # Single backchannel words should be detected.
        assert is_backchannel(word) is True, f"'{word}' should be a backchannel"

    # Test Scenario 2: Repeated backchannels
    @pytest.mark.parametrize("phrase", [
        "ok ok ok",
        "yeah yeah",
        "mmhmm mmhmm",
        "uh uh uh"
    ])
    def test_repeated_backchannels(self, phrase):
        # Repeated backchannel words should be detected.
        assert is_backchannel(phrase) is True, f"'{phrase}' should be a backchannel"

    # Test Scenario 3: Command words should NOT be backchannels
    @pytest.mark.parametrize("command", [
        "stop",
        "wait",
        "hold on",
        "pause",
        "what",
        "why",
        "how",
        "repeat",
    ])
    def test_command_words_not_backchannels(self, command):
        # Command words should NOT be detected as backchannels.
        assert is_backchannel(command) is False, f"'{command}' should NOT be a backchannel"

    # Test Scenario 4: Mixed inputs with command words
    @pytest.mark.parametrize("mixed", [
        "yeah wait",
        "yeah wait a second",
        "ok but stop",
        "hmm actually",
        "yeah okay but wait",
        "uh huh what did you say"
    ])
    def test_mixed_input_with_commands(self, mixed):
        # Mixed inputs containing command words should NOT be backchannels.
        assert is_backchannel(mixed) is False, f"'{mixed}' should NOT be a backchannel"

    # Test edge cases
    def test_empty_string(self):
        assert is_backchannel("") is False

    def test_whitespace_only(self):
        assert is_backchannel("   ") is False

    def test_long_sentence_not_backchannel(self):
        # Long sentences should not be backchannels regardless of content.
        assert is_backchannel("yeah I think that is a really good idea") is False

    def test_case_insensitive(self):
        assert is_backchannel("YEAH") is True
        assert is_backchannel("Ok") is True
        assert is_backchannel("HMM") is True

    def test_with_punctuation(self):
        assert is_backchannel("yeah!") is True
        assert is_backchannel("ok.") is True
        assert is_backchannel("hmm?") is True

    def test_custom_words(self):
        # Custom word list can extend detection to custom words.
        custom = frozenset({"custom", "words"})
        # Custom words ARE detected
        assert is_backchannel("custom", custom_words=custom) is True
        assert is_backchannel("words", custom_words=custom) is True


class TestContainsCommandWords:
    # Tests for command word detection.

    @pytest.mark.parametrize("transcript,expected", [
        ("stop", True),
        ("wait a second", True),
        ("what did you say", True),
        ("yeah", False),
        ("ok ok ok", False),
        ("please stop talking", True),
        ("actually I think", True),
    ])
    def test_command_detection(self, transcript, expected):
        assert contains_command_words(transcript) is expected

    def test_empty_string(self):
        assert contains_command_words("") is False


class TestIsLikelyContinuation:
    # Tests for continuation detection.

    @pytest.mark.parametrize("transcript,expected", [
        ("yeah so I was wondering", True),
        ("ok but what if", True),
        ("hmm actually I think", True),
        ("yeah", False),  # Too short
        ("ok ok", False),  # Too short
        ("hello there", False),  # Doesn't start with backchannel
    ])
    def test_continuation_detection(self, transcript, expected):
        assert is_likely_continuation(transcript) is expected


class TestDefaultWordLists:
    # Tests for default word lists.

    def test_default_backchannel_words_not_empty(self):
        assert len(DEFAULT_BACKCHANNEL_WORDS) > 0

    def test_command_words_not_empty(self):
        assert len(COMMAND_WORDS) > 0

    def test_no_overlap_between_lists(self):
        # Backchannel words and command words should not overlap.
        overlap = DEFAULT_BACKCHANNEL_WORDS & COMMAND_WORDS
        # Note: "no" may appear in both as it can be acknowledgement or command
        # We allow specific exceptions
        allowed_overlap = {"no", "nope", "nah"}
        unexpected_overlap = overlap - allowed_overlap
        assert len(unexpected_overlap) == 0, f"Unexpected overlap: {unexpected_overlap}"


class TestScenarios:
    # End-to-end tests matching the challenge test scenarios.

    def test_scenario_1_long_explanation(self):
        """
        Scenario 1: The Long Explanation
        Context: Agent is reading a long paragraph about history.
        User Action: User says "Okay... yeah... uhuh" while Agent is talking.
        Result: These should all be detected as backchannels.
        """
        assert is_backchannel("okay") is True
        assert is_backchannel("yeah") is True
        assert is_backchannel("uhuh") is True
        assert is_backchannel("mhm") is True

    def test_scenario_2_passive_affirmation(self):
        """
        Scenario 2: The Passive Affirmation
        Context: Agent asks "Are you ready?" and goes silent.
        User Action: User says "Yeah."
        Result: "Yeah" is still detected as backchannel by this function.
        Note: The state-based logic in agent_activity.py determines whether
        to ignore it (agent speaking) or respond to it (agent silent).
        """
        assert is_backchannel("yeah") is True

    def test_scenario_3_correction(self):
        """
        Scenario 3: The Correction
        Context: Agent is counting "One, two, three..."
        User Action: User says "No stop."
        Result: Should NOT be a backchannel due to "stop" command word.
        """
        assert is_backchannel("no stop") is False

    def test_scenario_4_mixed_input(self):
        """
        Scenario 4: The Mixed Input
        Context: Agent is speaking.
        User Action: User says "Yeah okay but wait."
        Result: Should NOT be a backchannel due to "wait" command word.
        """
        assert is_backchannel("yeah okay but wait") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
