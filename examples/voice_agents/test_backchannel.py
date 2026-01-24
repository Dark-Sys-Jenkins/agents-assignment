"""
Unit tests for backchannel filter.

Tests all scenarios required by the LiveKit Intelligent Interruption
Handling Challenge.

Usage:
    python test_backchannel.py

Author: Aswani Sahoo
"""

import sys
import os

# Add livekit-agents to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'livekit-agents'))

from livekit.agents.voice.backchannel_filter import (
    classify,
    should_ignore,
    BackchannelConfig,
    set_config,
    get_config,
)


def test_pure_backchannels():
    """Test that pure backchannel words are classified as ignore."""
    assert classify("yeah") == "ignore"
    assert classify("ok") == "ignore"
    assert classify("hmm") == "ignore"
    assert classify("uh-huh") == "ignore"
    assert classify("Yeah, ok, hmm") == "ignore"
    assert classify("  YEAH  ") == "ignore"
    assert classify("mhm") == "ignore"
    print("PASS: Pure backchannels")


def test_interrupt_words():
    """Test that interrupt words are classified as interrupt."""
    assert classify("stop") == "interrupt"
    assert classify("wait") == "interrupt"
    assert classify("no") == "interrupt"
    assert classify("No stop") == "interrupt"
    assert classify("STOP") == "interrupt"
    print("PASS: Interrupt words")


def test_mixed_input():
    """Test that mixed input with interrupt words is classified as interrupt."""
    assert classify("yeah okay but wait") == "interrupt"
    assert classify("ok actually") == "interrupt"
    assert classify("hmm but") == "interrupt"
    assert classify("yeah wait a second") == "interrupt"
    print("PASS: Mixed input")


def test_real_content():
    """Test that real content (not in ignore list) is classified as interrupt."""
    assert classify("tell me about space") == "interrupt"
    assert classify("what is AI") == "interrupt"
    assert classify("hello") == "interrupt"
    assert classify("explain that") == "interrupt"
    print("PASS: Real content")


def test_state_based_filtering():
    """Test that filtering only applies when agent is speaking."""
    # Agent speaking - ignore backchannels
    assert should_ignore("yeah", agent_speaking=True) == True
    assert should_ignore("ok", agent_speaking=True) == True
    assert should_ignore("hmm", agent_speaking=True) == True
    
    # Agent silent - process everything
    assert should_ignore("yeah", agent_speaking=False) == False
    assert should_ignore("ok", agent_speaking=False) == False
    
    # Interrupt words NEVER ignored
    assert should_ignore("stop", agent_speaking=True) == False
    assert should_ignore("wait", agent_speaking=True) == False
    assert should_ignore("no", agent_speaking=True) == False
    print("PASS: State-based filtering")


def test_empty_input():
    """Test that empty input is classified as ignore."""
    assert classify("") == "ignore"
    assert classify("   ") == "ignore"
    print("PASS: Empty input")


def test_custom_config():
    """Test custom configuration."""
    original_config = get_config()
    
    config = BackchannelConfig()
    config.ignore_words.add("gotcha")
    config.interrupt_words.add("cancel")
    set_config(config)
    
    assert classify("gotcha") == "ignore"
    assert classify("cancel") == "interrupt"
    
    set_config(original_config)
    print("PASS: Custom config")


def test_edge_cases():
    """Test edge cases."""
    assert classify("uh-huh") == "ignore"
    assert classify("yeah!") == "ignore"
    assert classify("ok?") == "ignore"
    assert classify("stop!") == "interrupt"
    assert classify("YEAH") == "ignore"
    assert classify("STOP") == "interrupt"
    print("PASS: Edge cases")


if __name__ == "__main__":
    print("Running backchannel filter tests...")
    print()
    
    test_pure_backchannels()
    test_interrupt_words()
    test_mixed_input()
    test_real_content()
    test_state_based_filtering()
    test_empty_input()
    test_custom_config()
    test_edge_cases()
    
    print()
    print("All tests passed!")
