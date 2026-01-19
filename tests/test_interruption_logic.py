import pytest
from livekit.agents.voice.interruption_logic import should_ignore_interruption

IGNORE_LIST = ["yeah", "ok", "uh-huh", "hmm", "right"]

def test_ignore_single_word():
    assert should_ignore_interruption("Yeah", IGNORE_LIST) is True
    assert should_ignore_interruption("ok", IGNORE_LIST) is True
    assert should_ignore_interruption("hmm", IGNORE_LIST) is True

def test_interrupt_command():
    assert should_ignore_interruption("Stop", IGNORE_LIST) is False
    assert should_ignore_interruption("Wait", IGNORE_LIST) is False

def test_mixed_input():
    # "Yeah wait" -> Should interrupt because "wait" is not ignored
    assert should_ignore_interruption("Yeah wait", IGNORE_LIST) is False
    assert should_ignore_interruption("Ok stop", IGNORE_LIST) is False

def test_multiple_ignored_words():
    # "Yeah ok" -> Should ignore because both are ignored
    assert should_ignore_interruption("Yeah ok", IGNORE_LIST) is True

def test_punctuation_handling():
    assert should_ignore_interruption("Yeah.", IGNORE_LIST) is True
    assert should_ignore_interruption("Ok!", IGNORE_LIST) is True
    assert should_ignore_interruption("...hmm...", IGNORE_LIST) is True

def test_case_sensitivity():
    assert should_ignore_interruption("YEAH", IGNORE_LIST) is True

def test_empty_input():
    assert should_ignore_interruption("", IGNORE_LIST) is False # Empty input usually handled by VAD before this, but if logic receives it, default to interrupt?
    # Wait, if text is empty, my logic returned False on line 12. 
    # But line 18 says: "if not clean_text: return True".
    # Logic: if input is "..." -> clean matches "" -> returns True (Ignore). Correct.
    # If input is empty string "" -> line 12 returns False. 
    # Is that correct? If text is empty, we probably shouldn't be calling this?
    # Or if we do, it means we have no info. Default behavior is to Interrupt (False) or Ignore (True)?
    # Existing code: if text is empty, it usually interrupts on VAD. 
    # My wrapper is strictly for text analysis.
    pass 
