import pytest
from livekit.agents.voice.backchanneling import TranscriptAnalyzer, SpeechKind, DEFAULT_FILLER_WORDS, DEFAULT_DIRECTIVE_WORDS

class TestTranscriptAnalyzer:
    def test_default_word_lists(self):
        analyzer = TranscriptAnalyzer()
        assert "yeah" in analyzer.filler_words
        assert "stop" in analyzer.directive_words

    def test_custom_word_lists(self):
        analyzer = TranscriptAnalyzer(
            filler_words=["foo", "bar"],
            directive_words=["baz", "qux"]
        )
        assert "foo" in analyzer.filler_words
        assert "yeah" not in analyzer.filler_words
        assert "baz" in analyzer.directive_words
        assert "stop" not in analyzer.directive_words

    def test_filler_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Yeah", agent_speaking=True)
        assert result.kind == SpeechKind.FILLER
        assert result.allow_continue is True

    def test_multiple_fillers_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Yeah okay", agent_speaking=True)
        assert result.kind == SpeechKind.FILLER
        assert result.allow_continue is True

    def test_directive_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Stop please", agent_speaking=True)
        assert result.kind == SpeechKind.DIRECTIVE
        assert result.allow_continue is False

    def test_mixed_input_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Yeah wait a second", agent_speaking=True)
        assert result.kind == SpeechKind.DIRECTIVE
        assert result.allow_continue is False

    def test_real_input_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("That is interesting", agent_speaking=True)
        assert result.kind == SpeechKind.INPUT
        assert result.allow_continue is False

    def test_new_turn_when_silent(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Yeah", agent_speaking=False)
        assert result.kind == SpeechKind.NEW_TURN
        assert result.allow_continue is False

    def test_any_input_when_silent(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Stop", agent_speaking=False)
        assert result.kind == SpeechKind.NEW_TURN
        assert result.allow_continue is False
    
    def test_case_insensitivity(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("YEAH", agent_speaking=True)
        assert result.kind == SpeechKind.FILLER
        assert result.allow_continue is True

    def test_punctuation_handling(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("Yeah!", agent_speaking=True)
        assert result.kind == SpeechKind.FILLER
        assert result.allow_continue is True

    def test_whitespace_handling(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("  yeah  ", agent_speaking=True)
        assert result.kind == SpeechKind.FILLER
        assert result.allow_continue is True

    def test_empty_input_while_speaking(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("", agent_speaking=True)
        assert result.kind == SpeechKind.NOISE
        assert result.allow_continue is True

    def test_empty_input_when_silent(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("", agent_speaking=False)
        assert result.kind == SpeechKind.NEW_TURN
        assert result.allow_continue is False


class TestBackwardCompatibility:
    def test_should_ignore_api(self):
        from livekit.agents.voice import BackchannelingFilter
        
        bf = BackchannelingFilter(ignore_words=["foo"], interrupt_words=["bar"])
        
        assert bf.should_ignore("foo", agent_speaking=True) is True
        assert bf.should_ignore("bar", agent_speaking=True) is False
        assert bf.should_ignore("hello", agent_speaking=True) is False


class TestEdgeCases:
    def test_sentence_with_fillers(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("yeah I agree", agent_speaking=True)
        assert result.kind == SpeechKind.INPUT
        assert result.allow_continue is False

    def test_only_numbers(self):
        analyzer = TranscriptAnalyzer()
        result = analyzer.analyze("123", agent_speaking=True)
        assert result.kind == SpeechKind.INPUT
        assert result.allow_continue is False
