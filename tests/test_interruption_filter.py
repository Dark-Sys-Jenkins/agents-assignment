# Copyright 2023 LiveKit, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the InterruptionFilter module."""

from __future__ import annotations

import pytest

from livekit.agents.voice.interruption_filter import (
    DEFAULT_BACKCHANNEL_WORDS,
    DEFAULT_INTERRUPT_WORDS,
    InterruptionFilter,
    InterruptionFilterConfig,
)


class TestInterruptionFilterConfig:
    """Tests for InterruptionFilterConfig defaults."""

    def test_default_backchannel_words(self):
        """Verify default backchannel words include common acknowledgements."""
        config = InterruptionFilterConfig()
        
        assert "yeah" in config.backchannel_words
        assert "ok" in config.backchannel_words
        assert "hmm" in config.backchannel_words
        assert "uh-huh" in config.backchannel_words
        assert "mhm" in config.backchannel_words

    def test_default_interrupt_words(self):
        """Verify default interrupt words include stop commands."""
        config = InterruptionFilterConfig()
        
        assert "stop" in config.interrupt_words
        assert "wait" in config.interrupt_words
        assert "no" in config.interrupt_words
        assert "actually" in config.interrupt_words

    def test_custom_word_sets(self):
        """Verify custom word sets can be provided."""
        custom_backchannel = {"yes", "okay", "sure"}
        custom_interrupt = {"halt", "cease"}
        
        config = InterruptionFilterConfig(
            backchannel_words=custom_backchannel,
            interrupt_words=custom_interrupt,
        )
        
        assert config.backchannel_words == custom_backchannel
        assert config.interrupt_words == custom_interrupt

    def test_enabled_default(self):
        """Verify filter is enabled by default."""
        config = InterruptionFilterConfig()
        assert config.enabled is True


class TestInterruptionFilter:
    """Tests for InterruptionFilter functionality."""

    @pytest.fixture
    def filter(self) -> InterruptionFilter:
        """Create a filter with default configuration."""
        return InterruptionFilter()

    # Tests for backchannel words when agent is speaking
    
    def test_backchannel_ignored_when_speaking(self, filter: InterruptionFilter):
        """Agent speaking + user says 'yeah' → no interrupt."""
        assert filter.should_interrupt("yeah", "speaking") is False
        assert filter.should_interrupt("ok", "speaking") is False
        assert filter.should_interrupt("uh-huh", "speaking") is False
        assert filter.should_interrupt("hmm", "speaking") is False
        assert filter.should_interrupt("mhm", "speaking") is False
        assert filter.should_interrupt("right", "speaking") is False

    def test_backchannel_case_insensitive(self, filter: InterruptionFilter):
        """Backchannel detection should be case insensitive."""
        assert filter.should_interrupt("Yeah", "speaking") is False
        assert filter.should_interrupt("YEAH", "speaking") is False
        assert filter.should_interrupt("OK", "speaking") is False
        assert filter.should_interrupt("Okay", "speaking") is False

    def test_multiple_backchannel_words(self, filter: InterruptionFilter):
        """Multiple backchannel words together should not interrupt."""
        assert filter.should_interrupt("yeah yeah", "speaking") is False
        assert filter.should_interrupt("ok ok ok", "speaking") is False
        assert filter.should_interrupt("yeah, ok", "speaking") is False
        assert filter.should_interrupt("hmm, yeah", "speaking") is False

    # Tests for backchannel words when agent is silent/listening

    def test_backchannel_processed_when_silent(self, filter: InterruptionFilter):
        """Agent silent + user says 'yeah' → process as input."""
        assert filter.should_interrupt("yeah", "listening") is True
        assert filter.should_interrupt("ok", "listening") is True
        assert filter.should_interrupt("hmm", "listening") is True

    def test_backchannel_processed_when_thinking(self, filter: InterruptionFilter):
        """Agent thinking + user says 'yeah' → process as input."""
        assert filter.should_interrupt("yeah", "thinking") is True
        assert filter.should_interrupt("ok", "thinking") is True

    def test_backchannel_processed_when_initializing(self, filter: InterruptionFilter):
        """Agent initializing + user says 'yeah' → process as input."""
        assert filter.should_interrupt("yeah", "initializing") is True

    # Tests for interrupt words

    def test_interrupt_word_always_interrupts(self, filter: InterruptionFilter):
        """Agent speaking + user says 'stop' → interrupt."""
        assert filter.should_interrupt("stop", "speaking") is True
        assert filter.should_interrupt("wait", "speaking") is True
        assert filter.should_interrupt("no", "speaking") is True
        assert filter.should_interrupt("hold on", "speaking") is True

    def test_interrupt_word_case_insensitive(self, filter: InterruptionFilter):
        """Interrupt words should be case insensitive."""
        assert filter.should_interrupt("Stop", "speaking") is True
        assert filter.should_interrupt("STOP", "speaking") is True
        assert filter.should_interrupt("Wait", "speaking") is True

    # Tests for mixed input

    def test_mixed_input_interrupts(self, filter: InterruptionFilter):
        """Agent speaking + user says 'yeah but wait' → interrupt due to 'but wait'."""
        assert filter.should_interrupt("yeah but wait", "speaking") is True
        assert filter.should_interrupt("ok wait", "speaking") is True
        assert filter.should_interrupt("yeah, actually no", "speaking") is True
        assert filter.should_interrupt("hmm, stop", "speaking") is True

    def test_backchannel_with_unknown_words_interrupts(self, filter: InterruptionFilter):
        """Backchannel + unknown words should interrupt (be conservative)."""
        assert filter.should_interrupt("yeah I have a question", "speaking") is True
        assert filter.should_interrupt("ok so anyway", "speaking") is True

    # Tests for edge cases

    def test_empty_transcript_no_interrupt(self, filter: InterruptionFilter):
        """Empty transcript should not trigger interrupt."""
        assert filter.should_interrupt("", "speaking") is False
        assert filter.should_interrupt("   ", "speaking") is False

    def test_punctuation_only_no_interrupt(self, filter: InterruptionFilter):
        """Punctuation-only input should not interrupt."""
        assert filter.should_interrupt("...", "speaking") is False
        assert filter.should_interrupt("?", "speaking") is False

    def test_transcript_with_punctuation(self, filter: InterruptionFilter):
        """Backchannel words with punctuation should still be recognized."""
        assert filter.should_interrupt("yeah.", "speaking") is False
        assert filter.should_interrupt("ok!", "speaking") is False
        assert filter.should_interrupt("hmm?", "speaking") is False
        assert filter.should_interrupt("uh-huh,", "speaking") is False

    # Tests for filter configuration

    def test_disabled_filter_always_interrupts(self):
        """When filter is disabled, all input should trigger interrupt."""
        filter = InterruptionFilter(InterruptionFilterConfig(enabled=False))
        
        assert filter.should_interrupt("yeah", "speaking") is True
        assert filter.should_interrupt("ok", "speaking") is True
        assert filter.should_interrupt("hmm", "speaking") is True

    def test_custom_backchannel_words(self):
        """Custom backchannel words should work correctly."""
        filter = InterruptionFilter(InterruptionFilterConfig(
            backchannel_words={"affirmative", "copy that"},
            interrupt_words=set(),
        ))
        
        assert filter.should_interrupt("affirmative", "speaking") is False
        assert filter.should_interrupt("copy that", "speaking") is False
        assert filter.should_interrupt("yeah", "speaking") is True  # Not in custom set

    def test_custom_interrupt_words(self):
        """Custom interrupt words should work correctly."""
        filter = InterruptionFilter(InterruptionFilterConfig(
            backchannel_words=set(),
            interrupt_words={"halt", "cease"},
        ))
        
        assert filter.should_interrupt("halt", "speaking") is True
        assert filter.should_interrupt("cease", "speaking") is True
        assert filter.should_interrupt("stop", "speaking") is True  # Unknown = interrupt

    def test_update_config(self):
        """Verify config can be updated dynamically."""
        filter = InterruptionFilter()
        
        # Initially "yeah" is filtered
        assert filter.should_interrupt("yeah", "speaking") is False
        
        # Update to remove "yeah" from backchannel
        filter.update_config(backchannel_words={"ok", "hmm"})
        
        # Now "yeah" should interrupt (unknown word)
        assert filter.should_interrupt("yeah", "speaking") is True
        assert filter.should_interrupt("ok", "speaking") is False

    def test_update_config_enable_disable(self):
        """Verify filter can be enabled/disabled dynamically."""
        filter = InterruptionFilter()
        
        # Initially enabled
        assert filter.should_interrupt("yeah", "speaking") is False
        
        # Disable
        filter.update_config(enabled=False)
        assert filter.should_interrupt("yeah", "speaking") is True
        
        # Re-enable
        filter.update_config(enabled=True)
        assert filter.should_interrupt("yeah", "speaking") is False


class TestInterruptionFilterIntegration:
    """Integration tests simulating real-world scenarios."""

    @pytest.fixture
    def filter(self) -> InterruptionFilter:
        """Create a filter with default configuration."""
        return InterruptionFilter()

    def test_scenario_agent_explaining_user_acknowledges(self, filter: InterruptionFilter):
        """User acknowledges while agent explains something."""
        # Agent is speaking, user provides acknowledgements
        assert filter.should_interrupt("yeah", "speaking") is False
        assert filter.should_interrupt("uh-huh", "speaking") is False
        assert filter.should_interrupt("ok", "speaking") is False
        assert filter.should_interrupt("I see", "speaking") is False
        assert filter.should_interrupt("right", "speaking") is False

    def test_scenario_agent_explaining_user_stops(self, filter: InterruptionFilter):
        """User wants to stop agent's explanation."""
        assert filter.should_interrupt("stop", "speaking") is True
        assert filter.should_interrupt("wait", "speaking") is True
        assert filter.should_interrupt("hold on", "speaking") is True
        assert filter.should_interrupt("one second", "speaking") is True

    def test_scenario_agent_done_user_responds(self, filter: InterruptionFilter):
        """Agent finished speaking, user responds with acknowledgement + question."""
        assert filter.should_interrupt("yeah", "listening") is True
        assert filter.should_interrupt("ok so what about...", "listening") is True
        assert filter.should_interrupt("hmm", "listening") is True

    def test_scenario_user_changes_mind(self, filter: InterruptionFilter):
        """User starts with acknowledgement but changes direction."""
        assert filter.should_interrupt("yeah but actually", "speaking") is True
        assert filter.should_interrupt("ok wait", "speaking") is True
        assert filter.should_interrupt("hmm, no", "speaking") is True
        assert filter.should_interrupt("right but however", "speaking") is True

    def test_scenario_user_asks_question_during_speech(self, filter: InterruptionFilter):
        """User asks a question while agent is speaking."""
        assert filter.should_interrupt("what about the weather?", "speaking") is True
        assert filter.should_interrupt("can you explain more?", "speaking") is True
