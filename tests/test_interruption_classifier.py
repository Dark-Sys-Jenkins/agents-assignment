"""Unit tests for interruption transcript classification (four acceptance scenarios)."""

import pytest

from livekit.agents.voice.agent_activity import _classify_interruption_transcript

# Match examples/dev/wordList.yaml (minimal set for the four scenarios).
# Note: split_words strips punctuation, so "uh-huh" becomes token "uhhuh"; include both.
IGNORE_WORDS = [
    "yeah",
    "ok",
    "okay",
    "hmm",
    "right",
    "uh-huh",
    "uh huh",
    "uhhuh",  # token form when punctuation stripped from "uh-huh"
    "mm-hmm",
]
STOP_WORDS = ["wait", "stop", "no"]


class TestClassifyInterruptionTranscript:
    """Lock in classification for the four acceptance scenarios."""

    def test_scenario_1_long_explanation_backchannel_only(self) -> None:
        """Scenario 1: 'Okay... yeah... uh-huh' while agent speaking -> should_ignore, no interrupt."""
        # All tokens in ignore_words; none in stop_words
        for transcript in ("Okay yeah uh-huh", "Okay... yeah... uh-huh", "ok yeah uh-huh"):
            should_ignore, should_stop, only_stop, stop_no_reply = (
                _classify_interruption_transcript(transcript, IGNORE_WORDS, STOP_WORDS)
            )
            assert should_ignore is True
            assert should_stop is False
            assert only_stop is False
            assert stop_no_reply is False

    def test_scenario_3_correction_only_stop_words(self) -> None:
        """Scenario 3: 'No stop.' while agent speaking -> interrupt, no reply (only_stop)."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "No stop.", IGNORE_WORDS, STOP_WORDS
        )
        assert should_ignore is False
        assert should_stop is True
        assert only_stop is True
        assert stop_no_reply is True

    def test_scenario_3_okay_stop_no_reply(self) -> None:
        """'Okay. Stop.' -> interrupt, no reply (stop + backchannel only)."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "Okay. Stop.", IGNORE_WORDS, STOP_WORDS
        )
        assert should_ignore is False
        assert should_stop is True
        assert only_stop is False  # "okay" is not a stop word
        assert stop_no_reply is True  # stop + backchannel only -> do not reply

    def test_scenario_3_single_stop_word(self) -> None:
        """Scenario 3 variant: single stop word."""
        for transcript in ("stop", "wait", "no"):
            should_ignore, should_stop, only_stop, stop_no_reply = (
                _classify_interruption_transcript(transcript, IGNORE_WORDS, STOP_WORDS)
            )
            assert should_ignore is False
            assert should_stop is True
            assert only_stop is True
            assert stop_no_reply is True

    def test_scenario_4_mixed_input(self) -> None:
        """Scenario 4: 'Yeah okay but wait.' -> interrupt, then process turn (not only_stop)."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "Yeah okay but wait.", IGNORE_WORDS, STOP_WORDS
        )
        assert should_ignore is False
        assert should_stop is True
        assert only_stop is False
        assert stop_no_reply is False  # "but" is substantive -> reply

    def test_edge_stop_takes_precedence(self) -> None:
        """Edge: 'yeah wait' -> stop takes precedence (interrupt, not backchannel)."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "yeah wait", IGNORE_WORDS, STOP_WORDS
        )
        assert should_ignore is False
        assert should_stop is True
        assert only_stop is False
        assert stop_no_reply is True  # only yeah + wait -> stop, no reply

    def test_empty_or_no_lists(self) -> None:
        """Empty transcript or no word lists -> no ignore, no stop."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "", IGNORE_WORDS, STOP_WORDS
        )
        assert should_ignore is False
        assert should_stop is False
        assert only_stop is False
        assert stop_no_reply is False

        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "yeah", [], []
        )
        assert should_ignore is False
        assert should_stop is False
        assert only_stop is False
        assert stop_no_reply is False

    @pytest.mark.parametrize("fuzzy_match", [False, True])
    def test_fuzzy_hmmm_matches_hmm(self, fuzzy_match: bool) -> None:
        """With fuzzy_match, 'hmmm' matches ignore word 'hmm'."""
        should_ignore, should_stop, only_stop, stop_no_reply = _classify_interruption_transcript(
            "hmmm", IGNORE_WORDS, STOP_WORDS, fuzzy_match=fuzzy_match, fuzzy_threshold=0.8
        )
        if fuzzy_match:
            assert should_ignore is True
            assert should_stop is False
            assert only_stop is False
            assert stop_no_reply is False
        else:
            # Exact match: "hmmm" != "hmm"
            assert should_ignore is False
            assert should_stop is False
            assert only_stop is False
            assert stop_no_reply is False
