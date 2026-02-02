"""
Unit tests for the interruption_filter module.

Tests the should_ignore_interruption() function with various input scenarios
to verify correct filtering of backchannels, commands, mixed utterances, and edge cases.
"""

import pytest
from interruption_filter import should_ignore_interruption


def test_pure_filler():
    """Test that pure filler/backchannel words are ignored."""
    assert should_ignore_interruption("yeah") == True
    assert should_ignore_interruption("okay") == True
    assert should_ignore_interruption("mm-hmm") == True
    assert should_ignore_interruption("yeah okay hmm") == True
    assert should_ignore_interruption("uh-huh right sure") == True


def test_command():
    """Test that command words trigger interruption."""
    assert should_ignore_interruption("stop") == False
    assert should_ignore_interruption("wait") == False
    assert should_ignore_interruption("stop wait") == False
    assert should_ignore_interruption("hold on") == False
    assert should_ignore_interruption("cancel") == False


def test_mixed():
    """Test that mixed utterances (filler + command) trigger interruption."""
    assert should_ignore_interruption("yeah but stop") == False
    assert should_ignore_interruption("okay wait") == False
    assert should_ignore_interruption("yeah stop now") == False
    assert should_ignore_interruption("mm-hmm hold on") == False


def test_empty():
    """Test that empty or whitespace-only input is ignored."""
    assert should_ignore_interruption("") == True
    assert should_ignore_interruption("   ") == True
    assert should_ignore_interruption("\n") == True
    assert should_ignore_interruption("\t") == True


def test_unknown():
    """Test that unknown (non-filler, non-command) words trigger interruption."""
    assert should_ignore_interruption("hello world") == False
    assert should_ignore_interruption("tell me a joke") == False
    assert should_ignore_interruption("what time is it") == False
    assert should_ignore_interruption("xyz") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
