"""
Tests for SmartInterruptionHandler

Run with: python -m pytest test_handler.py -v
"""

import pytest
from handler import SmartInterruptionHandler, InterruptionDecision
from config import InterruptionConfig


@pytest.fixture
def handler():
    """Create handler with default config"""
    config = InterruptionConfig()
    return SmartInterruptionHandler(config)


class TestPassiveWords:
    """Test passive word detection using internal helpers"""
    
    def test_single_passive_words(self, handler):
        """Single passive words should be detected as passive-only"""
        passive_words = ["yeah", "okay", "uh-huh", "mhmm", "right", "sure"]
        
        for word in passive_words:
            assert handler._is_passive_only(word), f"'{word}' should be passive"
    
    def test_passive_with_punctuation(self, handler):
        """Passive words with punctuation should be detected"""
        inputs = ["yeah.", "okay!", "uh-huh?", "mhmm...", "Right.", "Sure!"]
        
        for text in inputs:
            assert handler._is_passive_only(text), f"'{text}' should be passive"
    
    def test_multiple_passive_words(self, handler):
        """Multiple passive words should be detected"""
        inputs = ["yeah yeah", "okay sure", "uh-huh right", "mhmm yeah okay"]
        
        for text in inputs:
            assert handler._is_passive_only(text), f"'{text}' should be passive"
    
    def test_case_insensitive_passive(self, handler):
        """Passive words should be case insensitive"""
        inputs = ["YEAH", "Okay", "UH-HUH", "MhMm", "RIGHT"]
        
        for text in inputs:
            assert handler._is_passive_only(text), f"'{text}' should be passive"


class TestCommandWords:
    """Test command word detection"""
    
    def test_single_command_words(self, handler):
        """Single command words should be detected"""
        command_words = ["stop", "wait", "pause", "hold", "silence", "quiet"]
        
        for word in command_words:
            assert handler._contains_command_word(word), f"'{word}' should be command"
    
    def test_command_with_punctuation(self, handler):
        """Command words with punctuation should be detected"""
        inputs = ["stop!", "wait.", "pause?", "hold on!", "silence."]
        
        for text in inputs:
            assert handler._contains_command_word(text), f"'{text}' should contain command"
    
    def test_command_in_sentence(self, handler):
        """Command words in sentences should be detected"""
        inputs = [
            "please stop talking",
            "wait a minute",
            "can you pause",
            "hold on a second",
            "stop right there"
        ]
        
        for text in inputs:
            assert handler._contains_command_word(text), f"'{text}' should contain command"
    
    def test_case_insensitive_command(self, handler):
        """Command words should be case insensitive"""
        inputs = ["STOP", "Wait", "PAUSE", "HoLd On"]
        
        for text in inputs:
            assert handler._contains_command_word(text), f"'{text}' should contain command"


class TestMixedInput:
    """Test mixed passive and command words"""
    
    def test_passive_with_command(self, handler):
        """Passive + command should detect command"""
        inputs = [
            "yeah but stop",
            "okay wait",
            "uh-huh but pause",
            "mhmm hold on",
            "sure but be quiet"
        ]
        
        for text in inputs:
            assert handler._contains_command_word(text), f"'{text}' should contain command"
            assert not handler._is_passive_only(text), f"'{text}' should not be passive-only"
    
    def test_command_with_passive(self, handler):
        """Command + passive should detect command"""
        inputs = [
            "stop yeah",
            "wait okay",
            "pause sure",
            "hold on right"
        ]
        
        for text in inputs:
            assert handler._contains_command_word(text), f"'{text}' should contain command"
            assert not handler._is_passive_only(text), f"'{text}' should not be passive-only"


class TestSubstantiveContent:
    """Test substantive content detection"""
    
    def test_substantive_sentences(self, handler):
        """Substantive content should not be passive-only"""
        inputs = [
            "what time is it",
            "can you tell me more",
            "I have a question",
            "actually I disagree",
            "let me explain something"
        ]
        
        for text in inputs:
            assert not handler._is_passive_only(text), f"'{text}' should not be passive-only"
    
    def test_substantive_with_passive(self, handler):
        """Substantive content with passive should not be passive-only"""
        inputs = [
            "yeah but what about this",
            "okay I have a question",
            "sure but tell me more"
        ]
        
        for text in inputs:
            assert not handler._is_passive_only(text), f"'{text}' should not be passive-only"


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_string(self, handler):
        """Empty string should not be passive-only"""
        assert not handler._is_passive_only("")
    
    def test_whitespace_only(self, handler):
        """Whitespace should not be passive-only"""
        assert not handler._is_passive_only("   ")
    
    def test_numbers_only(self, handler):
        """Numbers should not be passive-only (substantive)"""
        assert not handler._is_passive_only("123")
    
    def test_special_characters(self, handler):
        """Special characters should not be passive-only (substantive)"""
        assert not handler._is_passive_only("@#$%")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
