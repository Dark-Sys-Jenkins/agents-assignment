"""
Unit tests for the InterruptionClassifier.

This module tests the classifier in isolation without requiring
the full livekit framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add examples directory to path so we can import the classifier
sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "voice_agents"))

from interruption_classifier import (
    InterruptionClassifier,
    InterruptionClassifierConfig,
    InterruptionIntent,
)


class TestInterruptionClassifier:
    """Unit tests for the InterruptionClassifier."""

    def test_default_config(self):
        """Test that default configuration is created correctly."""
        config = InterruptionClassifierConfig()
        assert "yeah" in config.backchannel_words
        assert "stop" in config.command_phrases
        assert config.interrupt_on_non_backchannel is True

    def test_single_word_backchannel(self):
        """Test classification of single-word backchannels."""
        classifier = InterruptionClassifier()

        # Standard backchannels should be ignored
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("okay") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("right") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("sure") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_multi_word_backchannel(self):
        """Test classification of multi-word backchannels."""
        classifier = InterruptionClassifier()

        # Multi-word backchannels
        assert classifier.classify("uh huh") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("uh-huh") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("mm hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("mm-hmm") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("i see") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("got it") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_backchannel_case_insensitive(self):
        """Test that backchannel detection is case-insensitive."""
        classifier = InterruptionClassifier()

        assert classifier.classify("Yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("YEAH") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("OK") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("Uh Huh") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_backchannel_with_punctuation(self):
        """Test that punctuation doesn't affect backchannel detection."""
        classifier = InterruptionClassifier()

        assert classifier.classify("yeah.") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok!") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("hmm...") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("yeah?") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_command_detection(self):
        """Test detection of interruption commands."""
        classifier = InterruptionClassifier()

        assert classifier.classify("stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("no") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("cancel") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("hold on") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("pause") == InterruptionIntent.INTERRUPT_COMMAND

    def test_command_case_insensitive(self):
        """Test that command detection is case-insensitive."""
        classifier = InterruptionClassifier()

        assert classifier.classify("Stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("STOP") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("Wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("NO") == InterruptionIntent.INTERRUPT_COMMAND

    def test_command_with_punctuation(self):
        """Test that commands are detected with punctuation."""
        classifier = InterruptionClassifier()

        assert classifier.classify("stop!") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("wait.") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("no!") == InterruptionIntent.INTERRUPT_COMMAND

    def test_mixed_utterance_with_command(self):
        """Test that mixed utterances containing commands are classified as interrupts."""
        classifier = InterruptionClassifier()

        # Command takes priority even with backchannels
        assert classifier.classify("yeah wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("yeah wait a second") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("ok stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("hmm no") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("ok but stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("yeah but wait") == InterruptionIntent.INTERRUPT_COMMAND

    def test_non_backchannel_content(self):
        """Test that non-backchannel content triggers INTERRUPT_OTHER."""
        classifier = InterruptionClassifier()

        # Regular speech should interrupt
        assert classifier.classify("hello") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("what about") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("I have a question") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("tell me more") == InterruptionIntent.INTERRUPT_OTHER

    def test_empty_input(self):
        """Test handling of empty input."""
        classifier = InterruptionClassifier()

        assert classifier.classify("") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("   ") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_none_input(self):
        """Test handling of None input."""
        classifier = InterruptionClassifier()
        # Should handle None gracefully
        result = classifier.classify(None)  # type: ignore
        assert result == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_should_interrupt_convenience_method(self):
        """Test the should_interrupt convenience method."""
        classifier = InterruptionClassifier()

        # Should NOT interrupt
        assert classifier.should_interrupt("yeah") is False
        assert classifier.should_interrupt("ok") is False
        assert classifier.should_interrupt("uh huh") is False

        # Should interrupt
        assert classifier.should_interrupt("stop") is True
        assert classifier.should_interrupt("wait") is True
        assert classifier.should_interrupt("hello there") is True
        assert classifier.should_interrupt("yeah wait") is True

    def test_custom_config(self):
        """Test classifier with custom configuration."""
        config = InterruptionClassifierConfig(
            backchannel_words={"yep", "cool"},
            command_phrases={"halt", "cease"},
            interrupt_on_non_backchannel=False,
        )
        classifier = InterruptionClassifier(config)

        # Custom backchannels
        assert classifier.classify("yep") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("cool") == InterruptionIntent.IGNORE_BACKCHANNEL

        # Default backchannels no longer recognized - treated as non-backchannel
        # But since interrupt_on_non_backchannel=False, they're ignored
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL

        # Custom commands
        assert classifier.classify("halt") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("cease") == InterruptionIntent.INTERRUPT_COMMAND

        # Default commands no longer recognized - treated as non-backchannel
        # But since interrupt_on_non_backchannel=False, they're ignored
        assert classifier.classify("stop") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_interrupt_on_non_backchannel_disabled(self):
        """Test with interrupt_on_non_backchannel disabled."""
        config = InterruptionClassifierConfig(interrupt_on_non_backchannel=False)
        classifier = InterruptionClassifier(config)

        # Commands still interrupt
        assert classifier.classify("stop") == InterruptionIntent.INTERRUPT_COMMAND

        # Non-backchannel content is ignored (only commands interrupt)
        assert classifier.classify("hello") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("I have a question") == InterruptionIntent.IGNORE_BACKCHANNEL

    def test_assignment_scenario_agent_speaking_backchannel(self):
        """
        Assignment Scenario - Case 1: Agent is Speaking
        User says "yeah", "ok", "hmm" → IGNORE
        """
        classifier = InterruptionClassifier()

        # These should all be IGNORE_BACKCHANNEL
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("hmm") == InterruptionIntent.IGNORE_BACKCHANNEL

        # Convenience method should return False (don't interrupt)
        assert classifier.should_interrupt("yeah") is False
        assert classifier.should_interrupt("ok") is False
        assert classifier.should_interrupt("hmm") is False

    def test_assignment_scenario_agent_speaking_command(self):
        """
        Assignment Scenario - Case 1: Agent is Speaking
        User says "stop", "wait", "no" → INTERRUPT
        """
        classifier = InterruptionClassifier()

        # These should all be INTERRUPT_COMMAND
        assert classifier.classify("stop") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("wait") == InterruptionIntent.INTERRUPT_COMMAND
        assert classifier.classify("no") == InterruptionIntent.INTERRUPT_COMMAND

        # Convenience method should return True (do interrupt)
        assert classifier.should_interrupt("stop") is True
        assert classifier.should_interrupt("wait") is True
        assert classifier.should_interrupt("no") is True

    def test_assignment_scenario_mixed_utterance(self):
        """
        Assignment Scenario - Case 1: Agent is Speaking
        User says "yeah wait a second" → INTERRUPT (because command is present)
        """
        classifier = InterruptionClassifier()

        # Mixed utterance with command should interrupt
        assert classifier.classify("yeah wait a second") == InterruptionIntent.INTERRUPT_COMMAND

        # Convenience method should return True
        assert classifier.should_interrupt("yeah wait a second") is True

    def test_assignment_scenario_agent_silent(self):
        """
        Assignment Scenario - Case 2: Agent is Silent
        User says "yeah", "ok" → Should be treated as valid input (IGNORE classification,
        but the framework will handle turn completion normally)
        """
        classifier = InterruptionClassifier()

        # When agent is silent, the classifier still returns IGNORE_BACKCHANNEL
        # but the agent-layer handler won't check because agent isn't speaking
        # so normal turn detection handles it
        assert classifier.classify("yeah") == InterruptionIntent.IGNORE_BACKCHANNEL
        assert classifier.classify("ok") == InterruptionIntent.IGNORE_BACKCHANNEL

        # Regular input still gets classified correctly
        assert classifier.classify("hello") == InterruptionIntent.INTERRUPT_OTHER
        assert classifier.classify("start") == InterruptionIntent.INTERRUPT_OTHER


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
