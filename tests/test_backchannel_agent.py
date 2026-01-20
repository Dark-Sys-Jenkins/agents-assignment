"""
Unit tests for the backchannel-aware interruption handler.

Tests cover:
1. Soft ignore words when agent is speaking
2. Hard interrupt words always trigger interruption
3. Mixed content triggers interruption
4. All inputs processed when agent is silent
5. Edge cases and configuration
"""

import pytest

from examples.voice_agents.interruption_handler import (
    InterruptionFilter,
    DEFAULT_SOFT_IGNORE,
    DEFAULT_HARD_INTERRUPT,
)


class TestInterruptionFilter:
    """Tests for the InterruptionFilter class"""

    def test_initialization(self):
        """Test filter initialization with default values"""
        filter = InterruptionFilter()
        assert filter.soft_ignore == DEFAULT_SOFT_IGNORE
        assert filter.hard_interrupt == DEFAULT_HARD_INTERRUPT

    def test_custom_word_sets(self):
        """Test initialization with custom word sets"""
        custom_soft = {"yes", "sure", "absolutely"}
        custom_hard = {"halt", "cease"}

        filter = InterruptionFilter(
            soft_ignore_words=custom_soft, hard_interrupt_words=custom_hard
        )

        assert filter.soft_ignore == custom_soft
        assert filter.hard_interrupt == custom_hard

    # Scenario 1: Soft ignore when agent is speaking
    def test_soft_ignore_single_word_when_speaking(self):
        """Backchannels should be ignored when agent is speaking"""
        filter = InterruptionFilter()

        assert filter.should_ignore("yeah", is_agent_speaking=True) is True
        assert filter.should_ignore("ok", is_agent_speaking=True) is True
        assert filter.should_ignore("hmm", is_agent_speaking=True) is True
        assert filter.should_ignore("uh-huh", is_agent_speaking=True) is True

    def test_soft_ignore_multiple_words_when_speaking(self):
        """Multiple backchannels should be ignored"""
        filter = InterruptionFilter()

        assert filter.should_ignore("ok okay", is_agent_speaking=True) is True
        assert filter.should_ignore("yeah yeah", is_agent_speaking=True) is True
        assert filter.should_ignore("hmm uh-huh right", is_agent_speaking=True) is True

    def test_soft_ignore_case_insensitive(self):
        """Backchannels should be case-insensitive"""
        filter = InterruptionFilter()

        assert filter.should_ignore("YEAH", is_agent_speaking=True) is True
        assert filter.should_ignore("Ok", is_agent_speaking=True) is True
        assert filter.should_ignore("HMM", is_agent_speaking=True) is True

    # Scenario 2: Hard interrupts are NOT ignored
    def test_hard_interrupt_single_word_when_speaking(self):
        """Hard interrupt words should NOT be ignored"""
        filter = InterruptionFilter()

        assert filter.should_ignore("stop", is_agent_speaking=True) is False
        assert filter.should_ignore("wait", is_agent_speaking=True) is False
        assert filter.should_ignore("no", is_agent_speaking=True) is False
        assert filter.should_ignore("pause", is_agent_speaking=True) is False

    def test_hard_interrupt_case_insensitive(self):
        """Hard interrupts should be case-insensitive"""
        filter = InterruptionFilter()

        assert filter.should_ignore("STOP", is_agent_speaking=True) is False
        assert filter.should_ignore("Wait", is_agent_speaking=True) is False

    # Scenario 3: Mixed content triggers interrupt
    def test_mixed_content_soft_plus_hard(self):
        """Mixed content (soft + hard) should trigger interrupt"""
        filter = InterruptionFilter()

        assert filter.should_ignore("yeah but wait", is_agent_speaking=True) is False
        assert filter.should_ignore("ok stop", is_agent_speaking=True) is False
        assert filter.should_ignore("hmm actually", is_agent_speaking=True) is False

    def test_mixed_content_soft_plus_other(self):
        """Mixed content (soft + other words) should trigger interrupt"""
        filter = InterruptionFilter()

        assert (
            filter.should_ignore("yeah I have a question", is_agent_speaking=True)
            is False
        )
        assert filter.should_ignore("ok tell me more", is_agent_speaking=True) is False
        assert (
            filter.should_ignore("hmm what about this", is_agent_speaking=True)
            is False
        )

    # Scenario 4: All inputs processed when agent is silent
    def test_all_processed_when_silent_soft_words(self):
        """Soft words should be processed when agent is silent"""
        filter = InterruptionFilter()

        assert filter.should_ignore("yeah", is_agent_speaking=False) is False
        assert filter.should_ignore("ok", is_agent_speaking=False) is False
        assert filter.should_ignore("hmm", is_agent_speaking=False) is False

    def test_all_processed_when_silent_hard_words(self):
        """Hard words should be processed when agent is silent"""
        filter = InterruptionFilter()

        assert filter.should_ignore("stop", is_agent_speaking=False) is False
        assert filter.should_ignore("wait", is_agent_speaking=False) is False

    def test_all_processed_when_silent_arbitrary_text(self):
        """Arbitrary text should be processed when agent is silent"""
        filter = InterruptionFilter()

        assert filter.should_ignore("hello there", is_agent_speaking=False) is False
        assert (
            filter.should_ignore("what is the weather", is_agent_speaking=False)
            is False
        )

    # Edge cases
    def test_empty_transcript(self):
        """Empty transcript should not be ignored"""
        filter = InterruptionFilter()

        assert filter.should_ignore("", is_agent_speaking=True) is False
        assert filter.should_ignore("", is_agent_speaking=False) is False

    def test_whitespace_only(self):
        """Whitespace-only transcript should not be ignored"""
        filter = InterruptionFilter()

        assert filter.should_ignore("   ", is_agent_speaking=True) is False

    def test_unknown_words_when_speaking(self):
        """Unknown words should trigger interrupt when agent speaks"""
        filter = InterruptionFilter()

        assert filter.should_ignore("hello", is_agent_speaking=True) is False
        assert (
            filter.should_ignore("tell me more", is_agent_speaking=True) is False
        )

    # make_decision method tests
    def test_make_decision_returns_correct_structure(self):
        """Test that make_decision returns properly structured data"""
        filter = InterruptionFilter()

        decision = filter.make_decision("yeah", is_agent_speaking=True)

        assert decision.should_ignore is True
        assert decision.reason == "all_soft_words"
        assert decision.transcript == "yeah"
        assert decision.is_agent_speaking is True
        assert decision.has_soft_words is True
        assert decision.has_hard_words is False
        assert decision.decision_time_ms >= 0

    def test_make_decision_hard_interrupt(self):
        """Test make_decision with hard interrupt"""
        filter = InterruptionFilter()

        decision = filter.make_decision("stop", is_agent_speaking=True)

        assert decision.should_ignore is False
        assert decision.reason == "hard_interrupt_detected"
        assert decision.has_hard_words is True

    def test_make_decision_agent_silent(self):
        """Test make_decision when agent is silent"""
        filter = InterruptionFilter()

        decision = filter.make_decision("yeah", is_agent_speaking=False)

        assert decision.should_ignore is False
        assert decision.reason == "agent_silent"

    def test_make_decision_mixed_content(self):
        """Test make_decision with mixed content"""
        filter = InterruptionFilter()

        decision = filter.make_decision(
            "yeah but wait", is_agent_speaking=True
        )

        # Should trigger interrupt due to hard word
        assert decision.should_ignore is False
        assert decision.reason == "hard_interrupt_detected"
        assert decision.has_soft_words is True
        assert decision.has_hard_words is True


class TestConfigLoadingEdgeCases:
    """Test configuration edge cases"""

    def test_filter_with_partially_overlapping_sets(self):
        """Test filter when soft and hard sets have overlap"""
        # This is a configuration error but should still work
        filter = InterruptionFilter(
            soft_ignore_words={"yeah", "ok", "wait"},  # 'wait' is problematic
            hard_interrupt_words={"stop", "wait"},
        )

        # 'wait' is in both sets - hard should take precedence
        assert filter.should_ignore("wait", is_agent_speaking=True) is False


class TestPerformance:
    """Test that filtering is fast enough for real-time use"""

    def test_decision_latency(self):
        """Ensure decision time is < 10ms"""
        filter = InterruptionFilter()

        decision = filter.make_decision(
            "yeah ok hmm uh-huh right", is_agent_speaking=True
        )

        # Decision should be very fast (< 10ms for real-time)
        assert decision.decision_time_ms < 10.0

    def test_batch_decisions_performance(self):
        """Test performance with multiple decisions"""
        filter = InterruptionFilter()

        transcripts = [
            "yeah",
            "stop",
            "ok sure",
            "wait a second",
            "hmm interesting",
            "but actually",
        ]

        import time

        start = time.perf_counter()
        for t in transcripts * 100:  # 600 decisions
            filter.should_ignore(t, is_agent_speaking=True)
        elapsed = (time.perf_counter() - start) * 1000

        # Should handle 600 decisions in well under 100ms
        assert elapsed < 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
