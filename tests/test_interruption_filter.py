"""Tests for the Interruption Filter."""

import pytest
from livekit.agents.voice.interruption_filter import (
    InterruptionFilter,
    InterruptionFilterConfig,
)


class TestInterruptionFilter:
    """Test interruption filter behavior."""

    def setup_method(self):
        self.filter = InterruptionFilter()

    # Agent is speaking - filler words should be ignored
    
    def test_ignore_yeah_while_speaking(self):
        assert not self.filter.should_interrupt("yeah", agent_speaking=True)

    def test_ignore_ok_while_speaking(self):
        assert not self.filter.should_interrupt("ok", agent_speaking=True)

    def test_ignore_hmm_while_speaking(self):
        assert not self.filter.should_interrupt("hmm", agent_speaking=True)

    def test_ignore_multiple_fillers(self):
        assert not self.filter.should_interrupt("yeah okay right", agent_speaking=True)

    # Agent is speaking - interrupt words should always interrupt

    def test_interrupt_on_wait(self):
        assert self.filter.should_interrupt("wait", agent_speaking=True)

    def test_interrupt_on_stop(self):
        assert self.filter.should_interrupt("stop", agent_speaking=True)

    def test_interrupt_on_no(self):
        assert self.filter.should_interrupt("no", agent_speaking=True)

    def test_interrupt_on_hold_on(self):
        assert self.filter.should_interrupt("hold on", agent_speaking=True)

    # Mixed input - interrupt words take priority

    def test_interrupt_on_yeah_wait(self):
        assert self.filter.should_interrupt("yeah wait", agent_speaking=True)

    def test_interrupt_on_ok_but_actually(self):
        assert self.filter.should_interrupt("ok but actually", agent_speaking=True)

    # Agent is silent - should always respond

    def test_respond_to_yeah_when_silent(self):
        assert self.filter.should_interrupt("yeah", agent_speaking=False)

    def test_respond_to_anything_when_silent(self):
        assert self.filter.should_interrupt("hello there", agent_speaking=False)

    # Edge cases

    def test_empty_input(self):
        assert not self.filter.should_interrupt("", agent_speaking=True)
        assert not self.filter.should_interrupt("   ", agent_speaking=True)

    def test_case_insensitive(self):
        assert not self.filter.should_interrupt("YEAH", agent_speaking=True)
        assert self.filter.should_interrupt("WAIT", agent_speaking=True)

    def test_with_punctuation(self):
        assert not self.filter.should_interrupt("yeah!", agent_speaking=True)
        assert self.filter.should_interrupt("wait!", agent_speaking=True)

    # Custom config

    def test_custom_ignore_words(self):
        config = InterruptionFilterConfig(ignore_words=["custom"])
        filter = InterruptionFilter(config)
        assert not filter.should_interrupt("custom", agent_speaking=True)
        assert filter.should_interrupt("yeah", agent_speaking=True)  # Not in custom list

    def test_disabled_filter(self):
        config = InterruptionFilterConfig(enabled=False)
        filter = InterruptionFilter(config)
        assert filter.should_interrupt("yeah", agent_speaking=True)  # Always interrupts
