"""
Unit Tests for Interruption Filter

These tests verify the filler word interruption filtering logic according to
the Salescode.ai Interview Assignment requirements.

Test Scenarios:
1. The Long Explanation - Agent ignores "yeah/ok/hmm" while speaking
2. The Passive Affirmation - Agent responds to "yeah" when silent
3. The Correction - Agent stops for "no stop"
4. The Mixed Input - Agent stops for "yeah okay but wait" (non-filler detected)
"""

import pytest
from livekit.agents.voice.interruption_filter import (
    InterruptionFilter,
    FilterDecision,
    FilterResult,
    DEFAULT_FILLER_WORDS,
    create_interruption_filter,
)


class TestInterruptionFilterBasic:
    """Basic functionality tests for InterruptionFilter."""

    def test_default_filler_words(self):
        """Test that default filler words are loaded."""
        filter = InterruptionFilter()
        assert "yeah" in filter.filler_words
        assert "ok" in filter.filler_words
        assert "hmm" in filter.filler_words
        assert "uh-huh" in filter.filler_words

    def test_custom_filler_words(self):
        """Test custom filler words configuration."""
        custom_words = ["custom1", "custom2"]
        filter = InterruptionFilter(filler_words=custom_words)
        assert "custom1" in filter.filler_words
        assert "custom2" in filter.filler_words
        assert "yeah" not in filter.filler_words  # Defaults not included

    def test_filter_inactive_by_default(self):
        """Test that filter starts inactive."""
        filter = InterruptionFilter()
        assert not filter.is_active

    def test_filter_activates_when_agent_speaking(self):
        """Test filter activates when agent is speaking."""
        filter = InterruptionFilter()
        result = filter.on_speech_start(agent_is_speaking=True)
        assert filter.is_active
        assert result.decision == FilterDecision.WAIT

    def test_filter_stays_inactive_when_agent_silent(self):
        """Test filter stays inactive when agent is silent."""
        filter = InterruptionFilter()
        result = filter.on_speech_start(agent_is_speaking=False)
        assert not filter.is_active
        assert result.decision == FilterDecision.PASS_THROUGH


class TestScenario1LongExplanation:
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Expected Result: Agent audio does not break. It ignores the user input completely.
    """

    def test_filler_words_ignored_during_agent_speech(self):
        """Agent should ignore filler words when speaking."""
        filter = InterruptionFilter()
        
        # Agent starts speaking
        filter.on_speech_start(agent_is_speaking=True)
        assert filter.is_active
        
        # User says filler words one by one
        result = filter.on_transcript_update("okay")
        assert result.decision == FilterDecision.WAIT, "Should wait on 'okay'"
        
        result = filter.on_transcript_update("okay yeah")
        assert result.decision == FilterDecision.WAIT, "Should wait on 'yeah'"
        
        result = filter.on_transcript_update("okay yeah uh-huh")
        assert result.decision == FilterDecision.WAIT, "Should wait on 'uh-huh'"
        
        # User stops speaking - all were fillers
        result = filter.on_speech_end()
        assert result.decision == FilterDecision.IGNORE, "Should IGNORE all filler input"
        # NOTE: filter.is_active remains True to handle late-arriving transcripts

    def test_multiple_filler_words_sequence(self):
        """Test various filler word combinations."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        filler_sequences = [
            "hmm",
            "hmm mm",
            "hmm mm right",
            "hmm mm right sure",
        ]
        
        for seq in filler_sequences:
            result = filter.on_transcript_update(seq)
            assert result.decision == FilterDecision.WAIT, f"Should wait on '{seq}'"
        
        result = filter.on_speech_end()
        assert result.decision == FilterDecision.IGNORE

    def test_hesitation_sounds_ignored(self):
        """Test that hesitation sounds are properly ignored."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("uh")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("uh um")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("uh um er")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_speech_end()
        assert result.decision == FilterDecision.IGNORE


class TestScenario2PassiveAffirmation:
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Expected Result: Agent processes "Yeah" as an answer and proceeds.
    """

    def test_filler_word_processed_when_agent_silent(self):
        """Agent should process filler words as valid input when silent."""
        filter = InterruptionFilter()
        
        # Agent is NOT speaking
        result = filter.on_speech_start(agent_is_speaking=False)
        assert result.decision == FilterDecision.PASS_THROUGH
        assert not filter.is_active
        
        # User says "yeah" - should pass through
        result = filter.on_transcript_update("yeah")
        assert result.decision == FilterDecision.PASS_THROUGH
        
        result = filter.on_speech_end()
        assert result.decision == FilterDecision.PASS_THROUGH

    def test_ok_processed_when_agent_silent(self):
        """'Ok' should be processed as valid input when agent is silent."""
        filter = InterruptionFilter()
        
        filter.on_speech_start(agent_is_speaking=False)
        result = filter.on_transcript_update("ok")
        assert result.decision == FilterDecision.PASS_THROUGH

    def test_hmm_processed_when_agent_silent(self):
        """'Hmm' should be processed as valid input when agent is silent."""
        filter = InterruptionFilter()
        
        filter.on_speech_start(agent_is_speaking=False)
        result = filter.on_transcript_update("hmm")
        assert result.decision == FilterDecision.PASS_THROUGH


class TestScenario3Correction:
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Expected Result: Agent cuts off immediately.
    """

    def test_command_words_interrupt_agent(self):
        """Command words like 'stop' should interrupt the agent."""
        filter = InterruptionFilter()
        
        # Agent is speaking
        filter.on_speech_start(agent_is_speaking=True)
        
        # User says "no stop"
        result = filter.on_transcript_update("no stop")
        assert result.decision == FilterDecision.INTERRUPT
        assert "no" in result.reason.lower() or "stop" in result.reason.lower()

    def test_stop_alone_interrupts(self):
        """'Stop' alone should interrupt."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("stop")
        assert result.decision == FilterDecision.INTERRUPT

    def test_wait_interrupts(self):
        """'Wait' should interrupt."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("wait")
        assert result.decision == FilterDecision.INTERRUPT

    def test_no_interrupts(self):
        """'No' should interrupt (it's not a filler)."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("no")
        assert result.decision == FilterDecision.INTERRUPT

    def test_question_interrupts(self):
        """Questions should interrupt."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("what did you say")
        assert result.decision == FilterDecision.INTERRUPT


class TestScenario4MixedInput:
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Expected Result: Agent stops (because "but wait" is not in the ignore list).
    """

    def test_filler_then_command_interrupts(self):
        """Filler words followed by command should interrupt."""
        filter = InterruptionFilter()
        
        # Agent is speaking
        filter.on_speech_start(agent_is_speaking=True)
        
        # First just fillers
        result = filter.on_transcript_update("yeah")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("yeah okay")
        assert result.decision == FilterDecision.WAIT
        
        # Then non-filler appears
        result = filter.on_transcript_update("yeah okay but")
        assert result.decision == FilterDecision.INTERRUPT
        assert "but" in result.reason.lower()

    def test_filler_then_wait_interrupts(self):
        """'Yeah okay but wait' should interrupt at 'but'."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        # Simulate incremental transcript
        filter.on_transcript_update("yeah")
        filter.on_transcript_update("yeah okay")
        result = filter.on_transcript_update("yeah okay but wait")
        
        assert result.decision == FilterDecision.INTERRUPT

    def test_filler_then_question_interrupts(self):
        """Filler followed by question should interrupt."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("hmm what")
        assert result.decision == FilterDecision.INTERRUPT

    def test_multiple_fillers_then_command(self):
        """Multiple fillers followed by command should still interrupt."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("yeah")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("yeah ok")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("yeah ok sure")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("yeah ok sure actually")
        assert result.decision == FilterDecision.INTERRUPT


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_transcript(self):
        """Empty transcript should wait."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("")
        assert result.decision == FilterDecision.WAIT

    def test_punctuation_only(self):
        """Punctuation-only input should be treated as filler."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("...")
        assert result.decision == FilterDecision.WAIT

    def test_case_insensitivity(self):
        """Filler detection should be case-insensitive."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        result = filter.on_transcript_update("YEAH")
        assert result.decision == FilterDecision.WAIT
        
        result = filter.on_transcript_update("Yeah OK")
        assert result.decision == FilterDecision.WAIT

    def test_filter_resets_between_speech_segments(self):
        """Filter should reset between separate speech segments."""
        filter = InterruptionFilter()
        
        # First speech segment
        filter.on_speech_start(agent_is_speaking=True)
        filter.on_transcript_update("yeah")
        filter.on_speech_end()
        
        # Second speech segment - should start fresh
        filter.on_speech_start(agent_is_speaking=True)
        assert filter.current_buffer == ""
        result = filter.on_transcript_update("stop")
        assert result.decision == FilterDecision.INTERRUPT

    def test_interrupt_decision_persists(self):
        """Once INTERRUPT is decided, it should persist."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        
        # First non-filler triggers interrupt
        result = filter.on_transcript_update("stop")
        assert result.decision == FilterDecision.INTERRUPT
        
        # Subsequent updates should maintain interrupt
        result = filter.on_transcript_update("stop please")
        assert result.decision == FilterDecision.INTERRUPT

    def test_force_interrupt(self):
        """Force interrupt should work regardless of state."""
        filter = InterruptionFilter()
        filter.on_speech_start(agent_is_speaking=True)
        filter.on_transcript_update("yeah")
        
        result = filter.force_interrupt()
        assert result.decision == FilterDecision.INTERRUPT


class TestCreateInterruptionFilter:
    """Tests for the factory function."""

    def test_create_with_defaults(self):
        """Factory with no args should use defaults."""
        filter = create_interruption_filter()
        assert "yeah" in filter.filler_words
        assert len(filter.filler_words) > 10  # Should have many defaults

    def test_create_extending_defaults(self):
        """Factory should be able to extend defaults."""
        filter = create_interruption_filter(
            filler_words=["custom_word"],
            extend_defaults=True
        )
        assert "yeah" in filter.filler_words
        assert "custom_word" in filter.filler_words

    def test_create_replacing_defaults(self):
        """Factory should be able to replace defaults."""
        filter = create_interruption_filter(
            filler_words=["only_this"],
            extend_defaults=False
        )
        assert "only_this" in filter.filler_words
        assert "yeah" not in filter.filler_words


class TestStateTransitions:
    """Test state machine transitions."""

    def test_full_workflow_filler_only(self):
        """Test complete workflow with only filler words."""
        filter = InterruptionFilter()
        
        # Agent speaking
        r1 = filter.on_speech_start(agent_is_speaking=True)
        assert r1.decision == FilterDecision.WAIT
        
        # Filler word
        r2 = filter.on_transcript_update("yeah")
        assert r2.decision == FilterDecision.WAIT
        
        # End with only fillers
        r3 = filter.on_speech_end()
        assert r3.decision == FilterDecision.IGNORE

    def test_full_workflow_with_interrupt(self):
        """Test complete workflow with interrupt."""
        filter = InterruptionFilter()
        
        # Agent speaking
        filter.on_speech_start(agent_is_speaking=True)
        
        # Filler then command
        filter.on_transcript_update("yeah")
        result = filter.on_transcript_update("yeah stop")
        assert result.decision == FilterDecision.INTERRUPT

    def test_full_workflow_agent_silent(self):
        """Test complete workflow when agent is silent."""
        filter = InterruptionFilter()
        
        # Agent silent
        r1 = filter.on_speech_start(agent_is_speaking=False)
        assert r1.decision == FilterDecision.PASS_THROUGH
        
        # Any input passes through
        r2 = filter.on_transcript_update("yeah")
        assert r2.decision == FilterDecision.PASS_THROUGH
        
        r3 = filter.on_speech_end()
        assert r3.decision == FilterDecision.PASS_THROUGH


class TestDefaultFillerWords:
    """Verify specific filler words from the assignment."""

    @pytest.mark.parametrize("word", [
        "yeah", "yep", "yes", "yup",
        "ok", "okay",
        "hmm", "hm", "mm", "mhm",
        "uh-huh", "aha",
        "uh", "um", "er",
        "right", "alright", "sure",
    ])
    def test_common_filler_words(self, word):
        """Test that common filler words are in defaults."""
        assert word in DEFAULT_FILLER_WORDS

    @pytest.mark.parametrize("word", [
        "stop", "wait", "no", "what", "why", "how",
        "hello", "help", "please", "actually", "but",
    ])
    def test_command_words_not_fillers(self, word):
        """Test that command words are NOT in fillers."""
        assert word not in DEFAULT_FILLER_WORDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
