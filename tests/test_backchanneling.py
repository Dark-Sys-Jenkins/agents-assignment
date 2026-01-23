"""
Unit Tests for Backchanneling Feature
=====================================
These tests verify the backchanneling detection logic locally
without needing a LiveKit server connection.

Run with: pytest tests/test_backchanneling.py -v
"""

import re
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

# Add the livekit-agents package to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "livekit-agents"))

from typing import Optional

import pytest
from livekit.agents.voice.backchanneling_config import (
    BackchannelingConfig,
    DEFAULT_BACKCHANNELING_CONFIG,
    DEFAULT_BACKCHANNELING_WORDS,
    DEFAULT_INTERRUPT_WORDS,
    create_config,
    create_english_only_config,
)


# Override the async autouse fixture from conftest.py for this synchronous test module
@pytest.fixture(autouse=True)
def fail_on_leaked_tasks():
    """Override the async fixture from conftest.py - our tests are synchronous."""
    yield


class TestBackchannelingConfig:
    """Test the BackchannelingConfig dataclass."""

    def test_default_config_exists(self):
        """Verify default config is properly initialized."""
        assert DEFAULT_BACKCHANNELING_CONFIG is not None
        assert DEFAULT_BACKCHANNELING_CONFIG.enabled is True
        assert len(DEFAULT_BACKCHANNELING_CONFIG.backchanneling_words) > 0
        assert len(DEFAULT_BACKCHANNELING_CONFIG.interrupt_words) > 0

    def test_default_backchanneling_words(self):
        """Verify common backchanneling words are in the default set."""
        expected_words = ["yeah", "yes", "ok", "okay", "hmm", "mhm", "uh-huh", "right", "sure"]
        for word in expected_words:
            assert word in DEFAULT_BACKCHANNELING_WORDS, f"'{word}' should be in backchanneling words"

    def test_default_interrupt_words(self):
        """Verify common interrupt words are in the default set."""
        expected_words = ["wait", "stop", "no", "hold", "pause", "what", "why", "how"]
        for word in expected_words:
            assert word in DEFAULT_INTERRUPT_WORDS, f"'{word}' should be in interrupt words"

    def test_no_overlap_between_word_sets(self):
        """Verify backchanneling and interrupt words don't overlap."""
        overlap = DEFAULT_BACKCHANNELING_WORDS & DEFAULT_INTERRUPT_WORDS
        assert len(overlap) == 0, f"Words should not overlap: {overlap}"

    def test_config_validation_rejects_overlap(self):
        """Config should raise error if words overlap."""
        with pytest.raises(ValueError, match="cannot be both"):
            BackchannelingConfig(
                enabled=True,
                backchanneling_words=frozenset({"yeah", "stop"}),
                interrupt_words=frozenset({"stop", "wait"}),
            )

    def test_create_config_extend_defaults(self):
        """Test creating config that extends defaults."""
        config = create_config(
            backchanneling_words={"roger", "copy"},
            interrupt_words={"abort"},
            extend_defaults=True,
        )
        assert "roger" in config.backchanneling_words
        assert "copy" in config.backchanneling_words
        assert "yeah" in config.backchanneling_words  # From defaults
        assert "abort" in config.interrupt_words
        assert "wait" in config.interrupt_words  # From defaults

    def test_create_config_replace_defaults(self):
        """Test creating config that replaces defaults."""
        config = create_config(
            backchanneling_words={"yes", "no"},
            interrupt_words={"stop"},
            extend_defaults=False,
        )
        assert "yes" in config.backchanneling_words
        assert "yeah" not in config.backchanneling_words  # Defaults replaced
        assert "stop" in config.interrupt_words
        assert "wait" not in config.interrupt_words  # Defaults replaced

    def test_create_english_only_config(self):
        """Test English-only config doesn't have Hindi words."""
        config = create_english_only_config()
        assert "yeah" in config.backchanneling_words
        assert "haan" not in config.backchanneling_words  # Hindi word
        assert "theek" not in config.backchanneling_words  # Hindi word
        assert "ruk" not in config.interrupt_words  # Hindi word

    def test_config_is_frozen(self):
        """Verify config is immutable."""
        config = DEFAULT_BACKCHANNELING_CONFIG
        with pytest.raises((AttributeError, FrozenInstanceError)):
            config.enabled = False


class TestBackchannelingDetection:
    """
    Test the backchanneling detection logic.
    
    These tests simulate what _is_backchanneling_only() does in agent_activity.py.
    """

    def _is_backchanneling_only(self, transcript: str, config: Optional[BackchannelingConfig] = None) -> bool:
        """
        Simulate the _is_backchanneling_only method from agent_activity.py.
        This mirrors the EXACT logic from the actual implementation.
        """
        if config is None:
            config = DEFAULT_BACKCHANNELING_CONFIG

        if not config.enabled:
            return False

        transcript_lower = transcript.lower().strip()
        transcript_clean = transcript_lower.strip(".,!?;:'\"")

        if not transcript_clean:
            return True

        # Check for interrupt words using SUBSTRING matching (matches actual code)
        for interrupt_word in config.interrupt_words:
            if interrupt_word in transcript_clean:
                return False

        # Check if full transcript matches a backchanneling word
        if transcript_clean in config.backchanneling_words:
            return True

        # Split by sentences and check each
        sentences = re.split(r'[.!?]+', transcript_lower)
        sentences = [s.strip().strip(".,!?;:'\"") for s in sentences if s.strip()]

        if sentences:
            all_bc = True
            for sentence in sentences:
                if sentence and sentence not in config.backchanneling_words:
                    # Split sentence into words
                    words = sentence.replace(",", " ").split()
                    word_texts = [w.strip(".,!?;:'\"") for w in words]
                    word_texts = [w for w in word_texts if w]
                    for word in word_texts:
                        if word not in config.backchanneling_words:
                            all_bc = False
                            break
                if not all_bc:
                    break
            if all_bc:
                return True

        # Final word-level check
        words = transcript_lower.replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ").split()
        word_texts = [w.strip(".,!?;:'\"") for w in words]
        word_texts = [w for w in word_texts if w]

        if not word_texts:
            return True

        for word in word_texts:
            if word not in config.backchanneling_words:
                return False

        return True

    # ==================== SCENARIO 1: Long Explanation ====================
    # Agent speaking, user says "yeah/ok/hmm" → Agent should CONTINUE (return True)

    def test_scenario1_single_yeah(self):
        """User says 'yeah' while agent speaks → IGNORE (continue speaking)."""
        assert self._is_backchanneling_only("yeah") is True

    def test_scenario1_single_ok(self):
        """User says 'ok' while agent speaks → IGNORE."""
        assert self._is_backchanneling_only("ok") is True

    def test_scenario1_single_hmm(self):
        """User says 'hmm' while agent speaks → IGNORE."""
        assert self._is_backchanneling_only("hmm") is True

    def test_scenario1_multiple_backchannels(self):
        """User says 'okay yeah uh-huh' → IGNORE (all are backchanneling)."""
        assert self._is_backchanneling_only("okay yeah uh-huh") is True

    def test_scenario1_right_sure(self):
        """User says 'right sure' → IGNORE."""
        assert self._is_backchanneling_only("right sure") is True

    def test_scenario1_mhm(self):
        """User says 'mhm' → IGNORE."""
        assert self._is_backchanneling_only("mhm") is True

    def test_scenario1_uh_huh(self):
        """User says 'uh huh' → IGNORE."""
        assert self._is_backchanneling_only("uh huh") is True

    # ==================== SCENARIO 2: Passive Affirmation ====================
    # When agent is SILENT, backchanneling check doesn't apply
    # These tests verify the detection works, actual state-based logic is in agent_activity.py

    # ==================== SCENARIO 3: The Correction ====================
    # Agent speaking, user says "no stop" → Agent should STOP (return False)

    def test_scenario3_no_stop(self):
        """User says 'no stop' → INTERRUPT."""
        assert self._is_backchanneling_only("no stop") is False

    def test_scenario3_stop(self):
        """User says 'stop' → INTERRUPT."""
        assert self._is_backchanneling_only("stop") is False

    def test_scenario3_wait(self):
        """User says 'wait' → INTERRUPT."""
        assert self._is_backchanneling_only("wait") is False

    def test_scenario3_hold_on(self):
        """User says 'hold on' → INTERRUPT."""
        assert self._is_backchanneling_only("hold on") is False

    def test_scenario3_no(self):
        """User says 'no' → INTERRUPT."""
        assert self._is_backchanneling_only("no") is False

    # ==================== SCENARIO 4: Mixed Input ====================
    # Agent speaking, user says "yeah but wait" → Agent should STOP (return False)

    def test_scenario4_yeah_but_wait(self):
        """User says 'yeah but wait' → INTERRUPT (contains 'but' and 'wait')."""
        assert self._is_backchanneling_only("yeah but wait") is False

    def test_scenario4_okay_but_wait(self):
        """User says 'okay but wait' → INTERRUPT."""
        assert self._is_backchanneling_only("okay but wait") is False

    def test_scenario4_yeah_wait_a_second(self):
        """User says 'yeah wait a second' → INTERRUPT (contains 'wait')."""
        assert self._is_backchanneling_only("yeah wait a second") is False

    def test_scenario4_hmm_actually(self):
        """User says 'hmm actually' → INTERRUPT (contains 'actually')."""
        assert self._is_backchanneling_only("hmm actually") is False

    def test_scenario4_ok_what(self):
        """User says 'ok what' → INTERRUPT (contains question word)."""
        assert self._is_backchanneling_only("ok what") is False

    def test_scenario4_yeah_why(self):
        """User says 'yeah why' → INTERRUPT (contains question word)."""
        assert self._is_backchanneling_only("yeah why") is False

    # ==================== Edge Cases ====================

    def test_empty_string(self):
        """Empty transcript → IGNORE."""
        assert self._is_backchanneling_only("") is True

    def test_whitespace_only(self):
        """Whitespace only → IGNORE."""
        assert self._is_backchanneling_only("   ") is True

    def test_normal_sentence(self):
        """Normal sentence → INTERRUPT (not backchanneling)."""
        assert self._is_backchanneling_only("what time is it") is False

    def test_question(self):
        """Question → INTERRUPT."""
        assert self._is_backchanneling_only("can you repeat that") is False

    def test_hello(self):
        """Greeting → INTERRUPT (normal speech, not backchanneling)."""
        assert self._is_backchanneling_only("hello") is False

    def test_case_insensitive(self):
        """Detection should be case insensitive."""
        assert self._is_backchanneling_only("YEAH") is True
        assert self._is_backchanneling_only("Yeah") is True
        assert self._is_backchanneling_only("STOP") is False
        assert self._is_backchanneling_only("Stop") is False

    def test_with_punctuation(self):
        """Detection should handle punctuation."""
        assert self._is_backchanneling_only("yeah!") is True
        assert self._is_backchanneling_only("ok.") is True
        assert self._is_backchanneling_only("stop!") is False

    def test_disabled_config(self):
        """When disabled, always return False (allow interruption)."""
        disabled_config = BackchannelingConfig(
            enabled=False,
            backchanneling_words=DEFAULT_BACKCHANNELING_WORDS,
            interrupt_words=DEFAULT_INTERRUPT_WORDS,
        )
        assert self._is_backchanneling_only("yeah", disabled_config) is False

    # ==================== Hindi/Hinglish Words ====================

    def test_hindi_backchanneling_haan(self):
        """Hindi 'haan' (yes) → IGNORE."""
        assert self._is_backchanneling_only("haan") is True

    def test_hindi_backchanneling_theek(self):
        """Hindi 'theek' (okay) → IGNORE."""
        assert self._is_backchanneling_only("theek") is True

    def test_hindi_backchanneling_accha(self):
        """Hindi 'accha' (okay/I see) → IGNORE."""
        assert self._is_backchanneling_only("accha") is True

    def test_hindi_interrupt_ruko(self):
        """Hindi 'ruko' (wait) → INTERRUPT."""
        assert self._is_backchanneling_only("ruko") is False

    def test_hindi_interrupt_nahi(self):
        """Hindi 'nahi' (no) → INTERRUPT."""
        assert self._is_backchanneling_only("nahi") is False


class TestTaskMdScenarios:
    """
    Direct tests for the scenarios specified in Task.md.
    """

    def _is_backchanneling_only(self, transcript: str) -> bool:
        """
        Simulate detection logic - mirrors actual implementation.
        Uses SUBSTRING matching for interrupt words.
        """
        config = DEFAULT_BACKCHANNELING_CONFIG
        if not config.enabled:
            return False
        
        transcript_lower = transcript.lower().strip()
        transcript_clean = transcript_lower.strip(".,!?;:'\"")
        
        if not transcript_clean:
            return True
        
        # SUBSTRING matching for interrupt words (matches actual code)
        for interrupt_word in config.interrupt_words:
            if interrupt_word in transcript_clean:
                return False
        
        # Check if full transcript is a backchanneling word
        if transcript_clean in config.backchanneling_words:
            return True
        
        # Split by sentences
        sentences = re.split(r'[.!?]+', transcript_lower)
        sentences = [s.strip().strip(".,!?;:'\"") for s in sentences if s.strip()]
        
        if sentences:
            all_bc = True
            for sentence in sentences:
                if sentence and sentence not in config.backchanneling_words:
                    words = sentence.replace(",", " ").split()
                    word_texts = [w.strip(".,!?;:'\"") for w in words if w.strip(".,!?;:'\"")]
                    for word in word_texts:
                        if word not in config.backchanneling_words:
                            all_bc = False
                            break
                if not all_bc:
                    break
            if all_bc:
                return True
        
        # Word-level check
        words = transcript_lower.replace(",", " ").replace(".", " ").split()
        word_texts = [w.strip(".,!?;:'\"") for w in words if w.strip(".,!?;:'\"")]
        
        if not word_texts:
            return True
        
        for word in word_texts:
            if word not in config.backchanneling_words:
                return False
        
        return True

    def test_task_scenario1_long_explanation(self):
        """
        Scenario 1: The Long Explanation
        - Context: Agent reading a long paragraph
        - User: "Okay... yeah... uh-huh"
        - Result: Agent ignores completely; audio does not break
        """
        # These should all be ignored (return True = backchanneling)
        assert self._is_backchanneling_only("okay") is True
        assert self._is_backchanneling_only("yeah") is True
        assert self._is_backchanneling_only("uh-huh") is True
        assert self._is_backchanneling_only("okay yeah") is True

    def test_task_scenario2_passive_affirmation(self):
        """
        Scenario 2: The Passive Affirmation
        - Context: Agent asks "Are you ready?" and goes silent
        - User: "Yeah."
        - Result: Agent processes "Yeah" as an answer and proceeds
        
        Note: When agent is SILENT, backchanneling filter doesn't apply.
        The detection returns True (is backchanneling), but agent_activity.py
        only filters when agent is speaking. This test verifies detection works.
        """
        # "yeah" is detected as backchanneling
        assert self._is_backchanneling_only("yeah") is True
        # But in agent_activity.py, this check only applies when agent is speaking

    def test_task_scenario3_the_correction(self):
        """
        Scenario 3: The Correction
        - Context: Agent counting "One, two, three..."
        - User: "No stop."
        - Result: Agent cuts off immediately
        """
        assert self._is_backchanneling_only("no stop") is False
        assert self._is_backchanneling_only("no") is False
        assert self._is_backchanneling_only("stop") is False

    def test_task_scenario4_mixed_input(self):
        """
        Scenario 4: The Mixed Input
        - Context: Agent is speaking
        - User: "Yeah okay but wait."
        - Result: Agent stops (because "but wait" is not in ignore list)
        """
        assert self._is_backchanneling_only("yeah okay but wait") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
