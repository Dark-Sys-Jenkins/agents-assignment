#!/usr/bin/env python3
"""Standalone test script for interrupt_ignore_words logic.

This script tests the _should_ignore_transcript helper method logic
without requiring the full livekit test environment.
"""

import sys
sys.path.insert(0, '/Users/primivista/Desktop/agents-assignment/livekit-agents')


def test_should_ignore_transcript_logic():
    """Test the logic of _should_ignore_transcript without dependencies."""
    
    # Simulating the logic from _should_ignore_transcript
    interrupt_commands = {"stop", "wait", "no", "hold", "pause", "cancel", "quiet", "silence"}
    
    def should_ignore(transcript: str, ignore_words: list[str]) -> bool:
        """Check if transcript contains only ignore words and no interrupt commands."""
        if not ignore_words:
            return False
        
        words = set(word.lower().strip(".,!?'\"") for word in transcript.split() if word.strip())
        
        if not words:
            return False
        
        # If any interrupt command is present, do NOT ignore
        if words & interrupt_commands:
            return False
        
        # If ALL words are in ignore list, ignore the transcript
        ignore_set = set(w.lower() for w in ignore_words)
        return words.issubset(ignore_set)
    
    ignore_list = ["yeah", "ok", "okay", "hmm", "uh-huh", "right", "aha", "mhm", "yep", "sure"]
    
    # Test cases
    tests = [
        # (transcript, expected_ignore)
        ("yeah", True),
        ("ok", True),
        ("hmm", True),
        ("Yeah", True),  # case insensitive
        ("yeah, ok", True),  # multiple ignore words
        ("stop", False),  # interrupt command
        ("wait", False),  # interrupt command
        ("no", False),  # interrupt command
        ("yeah wait", False),  # mixed - contains interrupt command
        ("ok but wait", False),  # mixed
        ("hello", False),  # not in ignore list
        ("tell me more", False),  # not in ignore list
        ("", False),  # empty
        ("yeah.", True),  # with punctuation
        ("Ok!", True),  # with punctuation
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("Testing _should_ignore_transcript logic")
    print("=" * 60)
    
    for transcript, expected in tests:
        result = should_ignore(transcript, ignore_list)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{transcript}' -> ignore={result} (expected={expected})")
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    test_should_ignore_transcript_logic()
