"""
Tests for the InterruptionFilter module.

These tests verify the four core scenarios:
1. Agent speaking + backchannel → no interrupt
2. Agent speaking + real interrupt → stops
3. Agent silent + backchannel → valid response (passthrough)
4. Mixed "yeah wait" → interrupts
"""

import pytest

from livekit.agents.voice.interruption_filter import (
    DEFAULT_IGNORE_WORDS,
    DEFAULT_INTERRUPT_WORDS,
    InterruptDecision,
    InterruptionContext,
    InterruptionFilter,
    InterruptionFilterConfig,
)


class TestInterruptDecision:
    """Test InterruptDecision enum values."""

    def test_decision_values(self):
        assert InterruptDecision.IGNORE.value == "ignore"
        assert InterruptDecision.INTERRUPT.value == "interrupt"
        assert InterruptDecision.PENDING.value == "pending"
        assert InterruptDecision.PASSTHROUGH.value == "passthrough"


class TestInterruptionFilterConfig:
    """Test InterruptionFilterConfig dataclass."""

    def test_default_config(self):
        config = InterruptionFilterConfig()
        assert config.ignore_words == DEFAULT_IGNORE_WORDS
        assert config.interrupt_words == DEFAULT_INTERRUPT_WORDS
        assert config.grace_period_ms == 150
        assert config.min_words_for_ignore == 1
        assert config.max_words_for_ignore == 3
        assert config.case_sensitive is False

    def test_custom_config(self):
        custom_ignore = frozenset({"custom1", "custom2"})
        custom_interrupt = frozenset({"halt", "freeze"})
        config = InterruptionFilterConfig(
            ignore_words=custom_ignore,
            interrupt_words=custom_interrupt,
            grace_period_ms=200,
        )
        assert config.ignore_words == custom_ignore
        assert config.interrupt_words == custom_interrupt
        assert config.grace_period_ms == 200


class TestInterruptionFilterBasics:
    """Test basic InterruptionFilter functionality."""

    def test_filter_initialization_default(self):
        filter = InterruptionFilter()
        assert filter.config is not None
        assert filter.grace_period_ms == 150

    def test_filter_initialization_with_config(self):
        config = InterruptionFilterConfig(grace_period_ms=300)
        filter = InterruptionFilter(config=config)
        assert filter.grace_period_ms == 300

    def test_filter_with_additional_words(self):
        filter = InterruptionFilter(
            ignore_words=["custom_backchannel"],
            interrupt_words=["custom_interrupt"],
        )
        # Verify custom words are merged with defaults
        assert "custom_backchannel" in filter.config.ignore_words
        assert "custom_interrupt" in filter.config.interrupt_words
        # Verify defaults still present
        assert "yeah" in filter.config.ignore_words
        assert "stop" in filter.config.interrupt_words


class TestAgentSpeakingBackchannel:
    """
    Scenario 1: Agent speaking + backchannel → no interrupt (IGNORE)
    """

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    @pytest.mark.parametrize(
        "transcript",
        [
            "yeah",
            "ok",
            "okay",
            "hmm",
            "mhm",
            "uh-huh",
            "right",
            "sure",
            "got it",
            "gotcha",
            "alright",
            "cool",
            "nice",
            "great",
            "good",
            "fine",
            "yes",
            "yep",
            "yup",
            "i see",
        ],
    )
    def test_ignore_single_backchannels(self, filter, transcript):
        """Single backchannel words should be ignored when agent is speaking."""
        ctx = InterruptionContext(
            transcript=transcript,
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=len(transcript.split()),
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE, f"Expected IGNORE for '{transcript}'"

    @pytest.mark.parametrize(
        "transcript",
        [
            "Yeah",
            "OK",
            "OKAY",
            "Hmm",
            "Uh-huh",
            "RIGHT",
            "Sure",
        ],
    )
    def test_ignore_case_insensitive(self, filter, transcript):
        """Backchannel matching should be case-insensitive by default."""
        ctx = InterruptionContext(
            transcript=transcript,
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE


class TestAgentSpeakingRealInterrupt:
    """
    Scenario 2: Agent speaking + real interrupt → stops (INTERRUPT)
    """

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    @pytest.mark.parametrize(
        "transcript",
        [
            "stop",
            "wait",
            "hold on",
            "pause",
            "no",
            "nope",
            "actually",
            "excuse me",
            "let me",
            "i want to",
            "can i",
            "question",
            "one second",
            "before you",
        ],
    )
    def test_interrupt_single_keywords(self, filter, transcript):
        """Interrupt words should trigger INTERRUPT when agent is speaking."""
        ctx = InterruptionContext(
            transcript=transcript,
            is_final=True,
            agent_speaking=True,
            speech_duration=0.5,
            word_count=len(transcript.split()),
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT, f"Expected INTERRUPT for '{transcript}'"

    def test_interrupt_longer_utterance(self, filter):
        """Longer utterances without clear keywords should interrupt."""
        ctx = InterruptionContext(
            transcript="I have something important to tell you about this",
            is_final=True,
            agent_speaking=True,
            speech_duration=2.0,
            word_count=9,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT


class TestAgentSilentBackchannel:
    """
    Scenario 3: Agent silent + backchannel → valid response (PASSTHROUGH)
    """

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    @pytest.mark.parametrize(
        "transcript",
        [
            "yeah",
            "ok",
            "hmm",
            "sure",
            "right",
        ],
    )
    def test_passthrough_when_agent_not_speaking(self, filter, transcript):
        """Backchannels should passthrough when agent is NOT speaking."""
        ctx = InterruptionContext(
            transcript=transcript,
            is_final=True,
            agent_speaking=False,  # Agent is silent
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.PASSTHROUGH


class TestMixedUtterances:
    """
    Scenario 4: Mixed "yeah wait" → interrupts (interrupt words take priority)
    """

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    @pytest.mark.parametrize(
        "transcript",
        [
            "yeah wait",
            "yeah wait a second",
            "ok but wait",
            "sure but actually",
            "hmm but no",
            "right but stop",
            "yeah hold on",
            "ok actually",
            "mhm but let me",
        ],
    )
    def test_interrupt_mixed_with_interrupt_word(self, filter, transcript):
        """Mixed utterances containing interrupt words should INTERRUPT."""
        ctx = InterruptionContext(
            transcript=transcript,
            is_final=True,
            agent_speaking=True,
            speech_duration=0.8,
            word_count=len(transcript.split()),
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT, f"Expected INTERRUPT for '{transcript}'"


class TestPendingDecisions:
    """Test PENDING decisions when more STT context is needed."""

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    def test_pending_when_transcript_empty(self, filter):
        """Empty transcript should return PENDING when agent is speaking."""
        ctx = InterruptionContext(
            transcript="",
            is_final=False,
            agent_speaking=True,
            speech_duration=0.2,
            word_count=0,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.PENDING

    def test_pending_for_non_final_unclear_transcript(self, filter):
        """Non-final transcript with unclear content should return PENDING."""
        ctx = InterruptionContext(
            transcript="I th",  # Partial word - could be anything
            is_final=False,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=2,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.PENDING


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def filter(self):
        return InterruptionFilter()

    def test_rapid_backchannel_spam(self, filter):
        """Multiple rapid backchannels should all be ignored."""
        backchannels = ["yeah", "yeah", "yeah"]
        for transcript in backchannels:
            ctx = InterruptionContext(
                transcript=transcript,
                is_final=True,
                agent_speaking=True,
                speech_duration=0.2,
                word_count=1,
            )
            decision = filter.should_interrupt(ctx)
            assert decision == InterruptDecision.IGNORE

    def test_whitespace_handling(self, filter):
        """Transcripts with extra whitespace should be handled correctly."""
        ctx = InterruptionContext(
            transcript="  yeah  ",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE

    def test_punctuation_handling(self, filter):
        """Transcripts with punctuation should be handled correctly."""
        ctx = InterruptionContext(
            transcript="yeah!",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE

    def test_short_final_unknown_word(self, filter):
        """Short final transcript with unknown word should be ignored (short = likely noise)."""
        ctx = InterruptionContext(
            transcript="um",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.2,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE

    def test_multi_word_phrase_matching(self, filter):
        """Multi-word interrupt phrases should be matched correctly."""
        ctx = InterruptionContext(
            transcript="hold on a second",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.8,
            word_count=4,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT


class TestCustomClassifier:
    """Test custom classifier callback functionality."""

    def test_custom_classifier_override(self):
        """Custom classifier can override default behavior."""

        def always_interrupt(ctx: InterruptionContext) -> InterruptDecision:
            return InterruptDecision.INTERRUPT

        filter = InterruptionFilter(custom_classifier=always_interrupt)

        # Even a backchannel should interrupt with custom classifier
        ctx = InterruptionContext(
            transcript="yeah",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT

    def test_custom_classifier_passthrough(self):
        """Custom classifier returning None falls through to default logic."""

        def selective_override(ctx: InterruptionContext) -> InterruptDecision | None:
            if "magic" in ctx.transcript.lower():
                return InterruptDecision.INTERRUPT
            return None  # Fall through to default

        filter = InterruptionFilter(custom_classifier=selective_override)

        # Normal backchannel uses default logic
        ctx = InterruptionContext(
            transcript="yeah",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE

        # Magic word triggers custom override
        ctx = InterruptionContext(
            transcript="magic word",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.5,
            word_count=2,
        )
        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.INTERRUPT


class TestOnInterruptionSuppressed:
    """Test the on_interruption_suppressed callback."""

    def test_suppression_callback_invoked(self):
        """Verify on_interruption_suppressed can be overridden."""
        suppressed_contexts = []

        class TrackingFilter(InterruptionFilter):
            def on_interruption_suppressed(self, ctx: InterruptionContext) -> None:
                suppressed_contexts.append(ctx)

        filter = TrackingFilter()

        ctx = InterruptionContext(
            transcript="yeah",
            is_final=True,
            agent_speaking=True,
            speech_duration=0.3,
            word_count=1,
        )

        decision = filter.should_interrupt(ctx)
        assert decision == InterruptDecision.IGNORE

        # Manually call suppressed callback (as agent_activity.py would do)
        filter.on_interruption_suppressed(ctx)
        assert len(suppressed_contexts) == 1
        assert suppressed_contexts[0].transcript == "yeah"
