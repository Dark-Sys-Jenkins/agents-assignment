"""
Utility functions for text processing and word detection.
"""

import re
from typing import List, Set


def normalize_and_tokenize(text: str) -> List[str]:
    """
    Normalize text and extract words.
    
    Handles:
    - Lowercasing
    - Punctuation removal
    - Multiple spaces
    - Special characters
    - Hyphenated words (e.g., "uh-huh")
    
    Args:
        text: Raw transcript text
        
    Returns:
        List of normalized words
        
    Examples:
        >>> normalize_and_tokenize("Yeah, okay!")
        ['yeah', 'okay']
        >>> normalize_and_tokenize("wait...stop")
        ['wait', 'stop']
        >>> normalize_and_tokenize("uh-huh")
        ['uh-huh']
    """
    if not text:
        return []
    
    # Convert to lowercase
    text = text.lower()
    
    # Extract words using regex (alphanumeric + hyphens)
    # This handles "uh-huh", "mm-hmm" correctly
    words = re.findall(r'\b[\w-]+\b', text)
    
    # Filter empty strings
    words = [w for w in words if w]
    
    return words


def contains_any_word(words: List[str], word_set: Set[str]) -> bool:
    """
    Check if any word from the list is in the word set.
    
    Args:
        words: List of words to check
        word_set: Set of target words
        
    Returns:
        True if any word matches
        
    Examples:
        >>> contains_any_word(['yeah', 'but'], {'yeah', 'ok'})
        True
        >>> contains_any_word(['hello', 'there'], {'yeah', 'ok'})
        False
    """
    return any(word in word_set for word in words)


def contains_only_words(words: List[str], word_set: Set[str]) -> bool:
    """
    Check if ALL words are in the word set.
    
    Args:
        words: List of words to check
        word_set: Set of allowed words
        
    Returns:
        True if all words are in the set
        
    Examples:
        >>> contains_only_words(['yeah', 'ok'], {'yeah', 'ok', 'hmm'})
        True
        >>> contains_only_words(['yeah', 'but'], {'yeah', 'ok', 'hmm'})
        False
    """
    if not words:
        return False
    
    return all(word in word_set for word in words)


def detect_phrase_match(text: str, phrases: Set[str]) -> bool:
    """
    Detect if any multi-word phrase appears in text.
    
    Useful for phrases like "hold on", "wait a second"
    
    Args:
        text: Input text
        phrases: Set of phrases to detect
        
    Returns:
        True if any phrase is found
        
    Examples:
        >>> detect_phrase_match("hold on a second", {"hold on"})
        True
        >>> detect_phrase_match("yeah ok", {"hold on"})
        False
    """
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def classify_utterance(text: str, filler_words: Set[str], 
                       interrupt_words: Set[str]) -> str:
    """
    Classify an utterance as FILLER, INTERRUPT, MIXED, or UNKNOWN.
    
    Classification rules:
    1. If contains ANY interrupt word → INTERRUPT
    2. If contains ONLY filler words → FILLER
    3. If contains mix of filler + other → MIXED
    4. Otherwise → UNKNOWN
    
    Args:
        text: Transcript text
        filler_words: Set of filler words
        interrupt_words: Set of interrupt words
        
    Returns:
        'FILLER' | 'INTERRUPT' | 'MIXED' | 'UNKNOWN' | 'EMPTY'
        
    Examples:
        >>> classify_utterance("yeah ok", {'yeah', 'ok'}, {'wait'})
        'FILLER'
        >>> classify_utterance("wait stop", {'yeah'}, {'wait', 'stop'})
        'INTERRUPT'
        >>> classify_utterance("yeah but wait", {'yeah'}, {'wait'})
        'INTERRUPT'
    """
    if not text or not text.strip():
        return 'EMPTY'
    
    words = normalize_and_tokenize(text)
    
    if not words:
        return 'EMPTY'
    
    # Check for interrupt words first (higher priority)
    has_interrupt = contains_any_word(words, interrupt_words)
    if has_interrupt:
        return 'INTERRUPT'
    
    # Check for multi-word interrupt phrases
    interrupt_phrases = {p for p in interrupt_words if ' ' in p}
    if detect_phrase_match(text, interrupt_phrases):
        return 'INTERRUPT'
    
    # Mixed content or unknown words
    # NEW: Check for multi-word filler phrases
    # Strategy: Remove all multi-word filler phrases from text, then check if remaining tokens are fillers
    
    text_lower = text.lower()
    temp_text = text_lower
    
    filler_phrases = {p for p in filler_words if ' ' in p}
    # Sort by length descending to match longest phrases first
    sorted_phrases = sorted(filler_phrases, key=len, reverse=True)
    
    for phrase in sorted_phrases:
        # Remove phrase if it exists as a whole word match
        pattern = r'\b' + re.escape(phrase) + r'\b'
        temp_text = re.sub(pattern, '', temp_text)
        
    remaining_words = normalize_and_tokenize(temp_text)
    
    # If nothing left, it was all filler phrases
    if not remaining_words:
        return 'FILLER'
        
    # Check if remaining are fillers
    if contains_only_words(remaining_words, filler_words):
        return 'FILLER'
        
    # If we still have content, it means we have non-filler words -> MIXED/INTERRUPT
    return 'MIXED'
    
    return 'UNKNOWN'


def format_transcript_for_display(text: str, max_length: int = 50) -> str:
    """
    Format transcript for display in logs.
    
    Args:
        text: Transcript text
        max_length: Maximum length before truncation
        
    Returns:
        Formatted string
    """
    if len(text) <= max_length:
        return f"'{text}'"
    
    return f"'{text[:max_length]}...'"
