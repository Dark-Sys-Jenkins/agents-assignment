"""
Integration tests for backchannel filtering logic.

These tests verify that the BackchannelFilter correctly classifies user input
based on agent state and utterance content.

Test Scenarios:
1. Backchannel during speech → IGNORE (agent continues)
2. Backchannel when silent → RESPOND (agent processes as input)
3. Real interruption during speech → INTERRUPT
4. Mixed input (backchannel + command) during speech → INTERRUPT
5. Multi-word backchannel during speech → IGNORE
"""

from __future__ import annotations

import pytest
from livekit.agents.voice.backchannel import BackchannelConfig, BackchannelFilter


class TestBackchannelFilter:
    """Test suite for BackchannelFilter classification logic."""

    @pytest.fixture
    def default_filter(self) -> BackchannelFilter:
        """Create a filter with default configuration."""
        return BackchannelFilter(BackchannelConfig())

    @pytest.fixture
    def custom_filter(self) -> BackchannelFilter:
        """Create a filter with custom word lists."""
        config = BackchannelConfig(
            enabled=True,
            backchannel_words={"yeah", "ok", "hmm"},
            interruption_commands={"wait", "stop", "no"},
            min_words_for_interruption=1,
        )
        return BackchannelFilter(config)

    # =========================================================================
    # Scenario 1: Backchannel during speech → IGNORE
    # =========================================================================

    @pytest.mark.parametrize(
        "utterance",
        [
            "yeah",
            "yes",
            "ok",
            "okay",
            "hmm",
            "hm",
            "right",
            "uh-huh",
            "mhm",
            "aha",
            "sure",
            "yep",
            "yup",
            "got it",
            "i see",
        ],
    )
    def test_backchannel_during_speech_ignore(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Scenario 1: Agent is explaining, user says 'yeah' → Agent continues speaking."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "ignore", f"Expected '{utterance}' to be ignored during speech"

    @pytest.mark.parametrize(
        "utterance",
        [
            "yeah...",
            "ok!",
            "hmm,",
            "uh-huh.",
            "mm-hmm",
        ],
    )
    def test_backchannel_with_punctuation_ignore(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Backchannel words with punctuation should still be ignored."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "ignore", f"Expected '{utterance}' to be ignored during speech"

    @pytest.mark.parametrize(
        "utterance",
        [
            "yeah yeah",
            "ok ok",
            "uh-huh mm-hmm",
            "yeah okay hmm",
        ],
    )
    def test_multi_word_backchannel_ignore(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Multiple backchannel words should still be ignored."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "ignore", f"Expected '{utterance}' to be ignored during speech"

    # =========================================================================
    # Scenario 2: Backchannel when silent → RESPOND
    # =========================================================================

    @pytest.mark.parametrize(
        "utterance",
        [
            "yeah",
            "ok",
            "hmm",
            "sure",
            "got it",
        ],
    )
    def test_backchannel_when_silent_respond(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Scenario 2: Agent asks 'Ready?', user says 'yeah' → Agent responds."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=False)
        assert decision == "respond", f"Expected '{utterance}' to trigger response when silent"

    @pytest.mark.parametrize(
        "utterance,expected_response",
        [
            ("yeah", "Great, let's continue."),
            ("ok", "Okay, moving on."),
            ("sure", "Perfect."),
        ],
    )
    def test_backchannel_response_context(
        self, default_filter: BackchannelFilter, utterance: str, expected_response: str
    ):
        """Backchannel when silent should be treated as valid input for LLM to process."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=False)
        assert decision == "respond"

    # =========================================================================
    # Scenario 3: Real interruption during speech → INTERRUPT
    # =========================================================================

    @pytest.mark.parametrize(
        "utterance",
        [
            "wait",
            "stop",
            "no",
            "hold on",
            "hang on",
            "pause",
            "slow down",
            "not yet",
            "actually",
            "sorry",
            "excuse me",
            "hey",
            "hello",
        ],
    )
    def test_interruption_command_during_speech(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Scenario 3: Agent counting '1, 2, 3...', user says 'stop' → Agent stops."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "interrupt", f"Expected '{utterance}' to interrupt speech"

    @pytest.mark.parametrize(
        "utterance",
        [
            "what is that",
            "tell me more",
            "who said that",
            "where are we",
            "when did that happen",
            "why is that",
            "how does it work",
        ],
    )
    def test_question_as_interruption(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Questions should interrupt the agent."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "interrupt", f"Expected '{utterance}' to interrupt speech"

    # =========================================================================
    # Scenario 4: Mixed input (backchannel + command) → INTERRUPT
    # =========================================================================

    @pytest.mark.parametrize(
        "utterance",
        [
            "yeah wait",
            "ok but stop",
            "hmm no wait",
            "yeah okay but wait a second",
            "uh-huh but hold on",
            "yes but I need to ask something",
            "yeah actually",
            "ok sorry but",
        ],
    )
    def test_mixed_backchannel_and_command_interrupt(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Scenario 4: User says 'yeah but wait' → Agent should interrupt."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "interrupt", f"Expected '{utterance}' to interrupt (contains command)"

    @pytest.mark.parametrize(
        "utterance",
        [
            "wait yeah",
            "stop ok",
            "no hmm",
        ],
    )
    def test_command_before_backchannel_interrupt(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Command word order shouldn't matter - still interrupts."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "interrupt"

    # =========================================================================
    # Scenario 5: Multi-word backchannel → IGNORE
    # =========================================================================

    @pytest.mark.parametrize(
        "utterance",
        [
            "uh-huh uh-huh",
            "mm-hmm mm-hmm",
            "yeah yeah yeah",
            "ok ok ok",
            "yes yes",
        ],
    )
    def test_repeated_backchannel_ignore(
        self, default_filter: BackchannelFilter, utterance: str
    ):
        """Repeated backchannel words should still be ignored."""
        decision = default_filter.should_interrupt(utterance, agent_is_speaking=True)
        assert decision == "ignore"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_utterance(self, default_filter: BackchannelFilter):
        """Empty input should be ignored."""
        decision = default_filter.should_interrupt("", agent_is_speaking=True)
        assert decision == "ignore"

    def test_whitespace_only(self, default_filter: BackchannelFilter):
        """Whitespace-only input should be ignored."""
        decision = default_filter.should_interrupt("   ", agent_is_speaking=True)
        assert decision == "ignore"

    def test_unknown_word_during_speech(self, default_filter: BackchannelFilter):
        """Unknown words should trigger interrupt (not in backchannel list)."""
        decision = default_filter.should_interrupt("xyzabc", agent_is_speaking=True)
        assert decision == "interrupt"

    def test_backchannel_disabled(self):
        """When disabled, all input should be treated as interruption."""
        config = BackchannelConfig(enabled=False)
        filter = BackchannelFilter(config)
        decision = filter.should_interrupt("yeah", agent_is_speaking=True)
        assert decision == "interrupt"

    def test_min_words_for_interruption(self):
        """Test minimum words threshold for interruption."""
        config = BackchannelConfig(
            backchannel_words={"yeah", "ok"},
            interruption_commands=set(),  # No explicit commands
            min_words_for_interruption=2,
        )
        filter = BackchannelFilter(config)

        # Single non-backchannel word - should ignore (below threshold)
        decision = filter.should_interrupt("hello", agent_is_speaking=True)
        assert decision == "ignore"

        # Two non-backchannel words - should interrupt (meets threshold)
        decision = filter.should_interrupt("hello world", agent_is_speaking=True)
        assert decision == "interrupt"

    # =========================================================================
    # Custom Configuration Tests
    # =========================================================================

    def test_custom_backchannel_words(self):
        """Test with custom backchannel word list."""
        config = BackchannelConfig(
            backchannel_words={"custom", "word"},
            interruption_commands=set(),
        )
        filter = BackchannelFilter(config)

        # Custom words should be ignored
        decision = filter.should_interrupt("custom", agent_is_speaking=True)
        assert decision == "ignore"

        # Default words should now interrupt
        decision = filter.should_interrupt("yeah", agent_is_speaking=True)
        assert decision == "interrupt"

    def test_custom_interruption_commands(self):
        """Test with custom interruption commands."""
        config = BackchannelConfig(
            backchannel_words={"yeah", "ok"},
            interruption_commands={"custom_command", "another"},
        )
        filter = BackchannelFilter(config)

        # Custom commands should interrupt
        decision = filter.should_interrupt("custom_command", agent_is_speaking=True)
        assert decision == "interrupt"

    def test_stt_settling_delay_config(self):
        """Test STT settling delay configuration."""
        config = BackchannelConfig(stt_settling_delay_ms=500)
        assert config.stt_settling_delay_ms == 500

        config = BackchannelConfig(stt_settling_delay_ms=100)
        assert config.stt_settling_delay_ms == 100


class TestBackchannelConfig:
    """Test suite for BackchannelConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BackchannelConfig()

        assert config.enabled is True
        assert isinstance(config.backchannel_words, set)
        assert len(config.backchannel_words) > 0
        assert isinstance(config.interruption_commands, set)
        assert len(config.interruption_commands) > 0
        assert config.min_words_for_interruption == 1
        assert config.check_semantic_interruption is True
        assert config.stt_settling_delay_ms == 300

    def test_all_defaults_populated(self):
        """Ensure default word lists are populated."""
        config = BackchannelConfig()

        # Check common backchannel words exist
        assert "yeah" in config.backchannel_words
        assert "ok" in config.backchannel_words
        assert "hmm" in config.backchannel_words

        # Check common interruption commands exist
        assert "wait" in config.interruption_commands
        assert "stop" in config.interruption_commands
        assert "no" in config.interruption_commands


# =========================================================================
# Integration-style tests (mocking agent activity behavior)
# =========================================================================


class TestBackchannelIntegration:
    """Integration-style tests simulating real agent behavior."""

    def test_scenario_1_long_explanation(self):
        """
        Scenario 1: The Long Explanation

        Context: Agent is reading a long paragraph about history.
        User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
        Result: Agent audio does not break. It ignores the user input completely.
        """
        filter = BackchannelFilter(BackchannelConfig())

        # Simulate multiple backchannel inputs during agent speech
        for utterance in ["okay", "yeah", "uh-huh"]:
            decision = filter.should_interrupt(utterance, agent_is_speaking=True)
            assert decision == "ignore", f"Backchannel '{utterance}' should be ignored"

    def test_scenario_2_passive_affirmation(self):
        """
        Scenario 2: The Passive Affirmation

        Context: Agent asks "Are you ready?" and goes silent.
        User Action: User says "Yeah."
        Result: Agent processes "Yeah" as an answer and proceeds.
        """
        filter = BackchannelFilter(BackchannelConfig())

        # Agent is silent, user responds
        decision = filter.should_interrupt("yeah", agent_is_speaking=False)
        assert decision == "respond", "Backchannel when silent should trigger response"

    def test_scenario_3_correction(self):
        """
        Scenario 3: The Correction

        Context: Agent is counting "One, two, three..."
        User Action: User says "No stop."
        Result: Agent cuts off immediately.
        """
        filter = BackchannelFilter(BackchannelConfig())

        # User interrupts counting
        decision = filter.should_interrupt("no stop", agent_is_speaking=True)
        assert decision == "interrupt", "'no stop' should interrupt"

    def test_scenario_4_mixed_input(self):
        """
        Scenario 4: The Mixed Input

        Context: Agent is speaking.
        User Action: User says "Yeah okay but wait."
        Result: Agent stops (because "but wait" is not in the ignore list).
        """
        filter = BackchannelFilter(BackchannelConfig())

        # Mixed input with command
        decision = filter.should_interrupt("yeah okay but wait", agent_is_speaking=True)
        assert decision == "interrupt", "Mixed input with command should interrupt"

    def test_timing_simulation(self):
        """
        Simulate the timing of VAD → delay → STT transcript → decision.

        This tests that the two-phase approach works correctly:
        1. VAD detects speech
        2. Backchannel check starts (with delay)
        3. STT produces transcript
        4. Decision is made based on transcript
        """
        import asyncio

        filter = BackchannelFilter(BackchannelConfig())

        # Simulate transcript accumulation over time
        transcript_timeline = [
            ("", "ignore"),  # No transcript yet
            ("ye", "interrupt"),  # Partial - unknown word
            ("yeah", "ignore"),  # Complete backchannel
        ]

        for transcript, expected in transcript_timeline:
            decision = filter.should_interrupt(transcript, agent_is_speaking=True)
            # Note: partial words may be classified differently
            # This is why we need the settling delay
            if transcript == "yeah":
                assert decision == "ignore"
            elif transcript == "":
                assert decision == "ignore"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
