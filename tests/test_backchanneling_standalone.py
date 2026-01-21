"""
Standalone unit tests for BackchannelingFilter that can run without full environment setup.

This test suite validates the core functionality of the BackchannelingFilter class
without requiring the full livekit agents environment.
"""

import sys
import os
import re
from typing import Set, List


# Mock logger for the backchanneling module
class MockLogger:
    def debug(self, msg, extra=None):
        pass
    
    def info(self, msg, extra=None):
        pass


# Copy of the BackchannelingFilter implementation for testing
DEFAULT_BACKCHANNELING_WORDS: Set[str] = {
    "yeah", "yep", "yes", "ok", "okay", "uh-huh", "huh",
    "hmm", "um", "uh", "ah", "right", "sure",
    "i see", "got it", "understood", "mm-hmm", "mhm",
    "alright", "uh huh", "yup", "ya", "yea",
}

DEFAULT_INTERRUPT_WORDS: Set[str] = {
    "wait", "stop", "pause", "hold", "hold on", "no", "dont", "don't",
    "shut up", "quiet", "stop talking", "enough",
    "never mind", "nevermind", "actually", "cancel",
    "hang on", "one second", "excuse me",
}


def _split_phrases(items: Set[str]) -> tuple[Set[str], Set[str]]:
    """Split a set into (single_words, multi_word_phrases)."""
    singles: Set[str] = set()
    phrases: Set[str] = set()
    for x in items:
        x = x.strip().lower()
        if not x:
            continue
        if " " in x:
            phrases.add(x)
        else:
            singles.add(x)
    return singles, phrases


class BackchannelingFilter:
    """
    Filters backchanneling words to prevent false interruptions.
    
    This filter checks if user speech is just passive acknowledgement
    (backchanneling) or an active attempt to interrupt/communicate.
    """
    
    def __init__(
        self,
        backchanneling_words: Set[str] | None = None,
        interrupt_words: Set[str] | None = None,
    ):
        """
        Initialize the backchanneling filter.
        
        Args:
            backchanneling_words: Words to ignore when agent is speaking.
                                  If None, uses DEFAULT_BACKCHANNELING_WORDS.
            interrupt_words: Words that always trigger interruption.
                            If None, uses DEFAULT_INTERRUPT_WORDS.
        """
        self._backchanneling_words = backchanneling_words or DEFAULT_BACKCHANNELING_WORDS.copy()
        self._interrupt_words = interrupt_words or DEFAULT_INTERRUPT_WORDS.copy()
        
        # Load from environment variables if set
        self._load_from_env()
        
        # Pre-split for efficient matching
        self._bc_single, self._bc_phrases = _split_phrases(self._backchanneling_words)
        self._int_single, self._int_phrases = _split_phrases(self._interrupt_words)
    
    def _load_from_env(self) -> None:
        """Load word lists from environment variables."""
        bc_env = os.getenv("BACKCHANNELING_WORDS", "").strip()
        if bc_env:
            self._backchanneling_words = {
                w.lower().strip() for w in bc_env.split(",") if w.strip()
            }
        
        int_env = os.getenv("INTERRUPT_WORDS", "").strip()
        if int_env:
            self._interrupt_words = {
                w.lower().strip() for w in int_env.split(",") if w.strip()
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        t = text.lower().strip()
        # Remove punctuation but keep spaces
        t = re.sub(r"[^a-z0-9\s]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    
    def _tokenize(self, text: str) -> List[str]:
        """Split text into tokens."""
        norm = self._normalize_text(text)
        return [w for w in norm.split(" ") if w]
    
    def contains_interrupt_word(self, text: str) -> bool:
        """
        Check if text contains any interrupt words.
        
        Interrupt words like "wait", "stop", "no" should always
        trigger an interruption regardless of context.
        """
        norm = self._normalize_text(text)
        tokens = self._tokenize(text)
        
        # Check multi-word phrases first
        for phrase in self._int_phrases:
            if f" {phrase} " in f" {norm} ":
                return True
        
        # Check single words
        return any(tok in self._int_single for tok in tokens)
    
    def is_pure_backchanneling(self, text: str) -> bool:
        """
        Check if text consists entirely of backchanneling words.
        
        Returns True if the text is only passive acknowledgement
        like "yeah", "ok", "uh-huh", "yeah ok hmm", etc.
        """
        norm = self._normalize_text(text)
        if not norm:
            return True  # Empty is considered backchanneling (noise)
        
        tokens = self._tokenize(text)
        if not tokens:
            return True
        
        # Check if entire text matches a known phrase
        if norm in self._bc_phrases:
            return True
        
        # Check if all tokens are backchanneling words
        return all(tok in self._bc_single for tok in tokens)
    
    def should_filter_interruption(self, transcript: str) -> bool:
        """
        Determine if this transcript should be filtered (not cause interruption).
        
        This is the main method to call when deciding whether to interrupt.
        
        Args:
            transcript: The user's speech transcript
            
        Returns:
            True if the transcript should be FILTERED (agent continues speaking)
            False if the transcript should cause an INTERRUPTION
        """
        if not transcript or not transcript.strip():
            return True  # Empty transcript - filter it
        
        # If it contains explicit interrupt words, don't filter
        if self.contains_interrupt_word(transcript):
            return False
        
        # If it's pure backchanneling, filter it
        if self.is_pure_backchanneling(transcript):
            return True
        
        # Unknown content - allow interruption (conservative)
        return False
    
    @property
    def backchanneling_words(self) -> Set[str]:
        """Get the current set of backchanneling words."""
        return self._backchanneling_words.copy()
    
    @property
    def interrupt_words(self) -> Set[str]:
        """Get the current set of interrupt words."""
        return self._interrupt_words.copy()


def test_basic_backchanneling():
    """Test detection of pure backchanneling words."""
    print("Testing basic backchanneling detection...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("yeah", True),
        ("ok", True),
        ("uh-huh", True),
        ("i see", True),
        ("got it", True),
        ("yeah ok hmm", True),
        ("i need help", False),
        ("wait", False),
        ("", True),  # empty is backchanneling
    ]
    
    for text, expected in test_cases:
        result = filter_.is_pure_backchanneling(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} is_pure_backchanneling('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_interrupt_words():
    """Test detection of interrupt words."""
    print("\nTesting interrupt word detection...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("wait", True),
        ("stop", True),
        ("no", True),
        ("hold on", True),
        ("never mind", True),
        ("yeah", False),
        ("ok", False),
        ("i need help", False),
    ]
    
    for text, expected in test_cases:
        result = filter_.contains_interrupt_word(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} contains_interrupt_word('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_should_filter_interruption():
    """Test the main filtering logic."""
    print("\nTesting should_filter_interruption logic...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("yeah", True),          # pure backchanneling -> filter
        ("ok", True),             # pure backchanneling -> filter
        ("wait", False),          # interrupt word -> don't filter
        ("stop", False),          # interrupt word -> don't filter
        ("hold on", False),       # interrupt phrase -> don't filter
        ("i need help", False),   # regular speech -> don't filter
        ("can you help", False),  # regular speech -> don't filter
        ("", True),               # empty -> filter
        ("  yeah  ", True),       # backchanneling with whitespace -> filter
    ]
    
    for text, expected in test_cases:
        result = filter_.should_filter_interruption(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} should_filter_interruption('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_case_insensitivity():
    """Test that filtering is case-insensitive."""
    print("\nTesting case insensitivity...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("YEAH", True),
        ("Ok", True),
        ("HMM", True),
        ("WAIT", False),
        ("Stop", False),
        ("YeAh Ok HmM", True),
    ]
    
    for text, expected in test_cases:
        result = filter_.should_filter_interruption(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} should_filter_interruption('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_punctuation_handling():
    """Test that punctuation is properly handled."""
    print("\nTesting punctuation handling...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("yeah!", True),
        ("ok?", True),
        ("hmm...", True),
        ("wait!", False),
        ("stop.", False),
        ("yeah, ok.", True),
    ]
    
    for text, expected in test_cases:
        result = filter_.should_filter_interruption(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} should_filter_interruption('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_mixed_content():
    """Test mixed backchanneling and other content."""
    print("\nTesting mixed content handling...")
    filter_ = BackchannelingFilter()
    
    test_cases = [
        ("yeah but I need help", False),     # mixed -> not filtered
        ("wait I have a question", False),   # interrupt + content -> not filtered
        ("ok and then what", False),         # mixed -> not filtered
    ]
    
    for text, expected in test_cases:
        result = filter_.should_filter_interruption(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} should_filter_interruption('{text}') = {result} (expected {expected})")
        assert result == expected, f"Failed for '{text}'"


def test_custom_word_lists():
    """Test custom word lists."""
    print("\nTesting custom word lists...")
    
    # Custom backchanneling words (avoid underscores, they get normalized)
    filter_ = BackchannelingFilter(backchanneling_words={"custombc", "test"})
    assert filter_.is_pure_backchanneling("custombc") is True
    assert filter_.is_pure_backchanneling("test") is True
    assert filter_.is_pure_backchanneling("yeah") is False  # not in custom list
    print("  ✓ Custom backchanneling words work")
    
    # Custom interrupt words
    filter_ = BackchannelingFilter(interrupt_words={"customint", "halt"})
    assert filter_.contains_interrupt_word("customint") is True
    assert filter_.contains_interrupt_word("halt") is True
    assert filter_.contains_interrupt_word("wait") is False  # not in custom list
    print("  ✓ Custom interrupt words work")


def test_default_lists():
    """Test that default word lists are populated correctly."""
    print("\nTesting default word lists...")
    
    # Check that defaults are not empty
    assert len(DEFAULT_BACKCHANNELING_WORDS) > 0, "Default backchanneling words is empty"
    assert len(DEFAULT_INTERRUPT_WORDS) > 0, "Default interrupt words is empty"
    print(f"  ✓ Default backchanneling words: {len(DEFAULT_BACKCHANNELING_WORDS)} words")
    print(f"  ✓ Default interrupt words: {len(DEFAULT_INTERRUPT_WORDS)} words")
    
    # Check for common words
    common_bc = ["yeah", "ok", "hmm", "yes"]
    for word in common_bc:
        assert word in DEFAULT_BACKCHANNELING_WORDS, f"'{word}' not in default backchanneling words"
    print(f"  ✓ Common backchanneling words present: {common_bc}")
    
    common_int = ["wait", "stop", "no"]
    for word in common_int:
        assert word in DEFAULT_INTERRUPT_WORDS, f"'{word}' not in default interrupt words"
    print(f"  ✓ Common interrupt words present: {common_int}")


def test_edge_cases():
    """Test edge cases."""
    print("\nTesting edge cases...")
    
    filter_ = BackchannelingFilter()
    
    # Very long text
    long_text = "yeah " * 1000
    result = filter_.is_pure_backchanneling(long_text)
    assert result is True, "Failed on very long backchanneling text"
    print("  ✓ Handles very long text")
    
    # Multiple spaces
    result = filter_.should_filter_interruption("yeah    ok    hmm")
    assert result is True, "Failed on multiple spaces"
    print("  ✓ Handles multiple spaces")
    
    # Tabs and newlines
    result = filter_.should_filter_interruption("yeah\t\nok")
    assert result is True, "Failed on tabs and newlines"
    print("  ✓ Handles tabs and newlines")


def test_real_world_scenarios():
    """Test real-world usage scenarios."""
    print("\nTesting real-world scenarios...")
    
    filter_ = BackchannelingFilter()
    
    # Scenario 1: User acknowledging during agent speech
    transcript = "yeah"
    result = filter_.should_filter_interruption(transcript)
    assert result is True, "User acknowledgement should be filtered"
    print("  ✓ User acknowledgement filtered (agent continues)")
    
    # Scenario 2: User interrupting with 'wait'
    transcript = "wait"
    result = filter_.should_filter_interruption(transcript)
    assert result is False, "User interrupt should NOT be filtered"
    print("  ✓ User interrupt not filtered (agent stops)")
    
    # Scenario 3: User asking a real question
    transcript = "can you explain that more?"
    result = filter_.should_filter_interruption(transcript)
    assert result is False, "Real question should NOT be filtered"
    print("  ✓ Real question not filtered (can be processed)")
    
    # Scenario 4: Multiple backchanneling words
    transcript = "yeah yeah ok hmm"
    result = filter_.should_filter_interruption(transcript)
    assert result is True, "Multiple backchanneling words should be filtered"
    print("  ✓ Multiple backchanneling words filtered")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running BackchannelingFilter Tests")
    print("=" * 60)
    
    try:
        test_basic_backchanneling()
        test_interrupt_words()
        test_should_filter_interruption()
        test_case_insensitivity()
        test_punctuation_handling()
        test_mixed_content()
        test_custom_word_lists()
        test_default_lists()
        test_edge_cases()
        test_real_world_scenarios()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        print("=" * 60)
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
