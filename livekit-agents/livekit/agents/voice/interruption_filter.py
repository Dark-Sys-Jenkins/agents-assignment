"""
Intelligent interruption filtering for LiveKit voice agents.

This module provides semantic classification of user speech to distinguish between:
- Soft acknowledgements (e.g., "yeah", "ok", "hmm") that should be ignored when agent is speaking
- Hard interrupt commands (e.g., "stop", "wait", "no") that should immediately interrupt the agent
- Mixed inputs (e.g., "yeah but stop") that should trigger interruption

The decision logic is deterministic and fast (<300ms), using simple string tokenization
without ML models or external API calls.
"""

from __future__ import annotations

import os
import re

__all__ = [
    "SOFT_ACKNOWLEDGMENT_WORDS",
    "HARD_INTERRUPT_WORDS",
    "should_ignore_as_soft_acknowledgment",
]

# Default soft acknowledgment words (passive listening signals)
_DEFAULT_SOFT_WORDS = frozenset(
    [
        "yeah",
        "ok",
        "okay",
        "uh-huh",
        "mm-hmm",
        "hmm",
        "mhm",
        "yep",
        "yup",
        "right",
        "sure",
        "gotcha",
        "alright",
        "uh",
        "um",
        "ah",
        "oh",
        "yes",
    ]
)

# Default hard interrupt words (explicit stop commands)
_DEFAULT_INTERRUPT_WORDS = frozenset(
    [
        "stop",
        "wait",
        "hold",
        "pause",
        "no",
        "dont",
        "don't",
        "never",
        "wrong",
        "halt",
        "enough",
    ]
)

# Load from environment variables if provided
_soft_words_env = os.getenv("LIVEKIT_SOFT_WORDS", "")
_interrupt_words_env = os.getenv("LIVEKIT_INTERRUPT_WORDS", "")

SOFT_ACKNOWLEDGMENT_WORDS = (
    frozenset(_soft_words_env.split(",")) if _soft_words_env else _DEFAULT_SOFT_WORDS
)
HARD_INTERRUPT_WORDS = (
    frozenset(_interrupt_words_env.split(",")) if _interrupt_words_env else _DEFAULT_INTERRUPT_WORDS
)


def _tokenize_transcript(transcript: str) -> list[str]:
    """
    Tokenize transcript into words, handling contractions and punctuation.
    
    Args:
        transcript: Raw transcript text to tokenize
        
    Returns:
        List of normalized word tokens (lowercase, no punctuation)
    """
    # Remove punctuation and normalize to lowercase
    normalized = re.sub(r"[^\w\s'-]", " ", transcript.lower())
    # Split on whitespace
    tokens = normalized.split()
    return [token.strip() for token in tokens if token.strip()]


def _is_phonetic_utterance(transcript: str) -> bool:
    """
    Detect purely phonetic utterances that should be treated as soft acknowledgments.
    
    Phonetic utterances consist only of phoneme fragments like "mm", "hm", "uh", "um"
    that Deepgram emits for sounds like "mmhm" before lexical tokens stabilize.
    
    Args:
        transcript: Normalized transcript (lowercase, stripped)
        
    Returns:
        True if the utterance is purely phonetic (should be ignored)
        False otherwise
        
    Examples:
        >>> _is_phonetic_utterance("mm")
        True
        >>> _is_phonetic_utterance("hm")
        True
        >>> _is_phonetic_utterance("mm hm")
        True
        >>> _is_phonetic_utterance("uh um")
        True
        >>> _is_phonetic_utterance("hello")
        False
    """
    # Normalize: lowercase, remove punctuation, collapse multiple spaces
    normalized = re.sub(r"[^\w\s]", "", transcript.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    
    if not normalized:
        return True  # Empty after normalization
    
    # Phonetic pattern: only m, h, u characters (possibly repeated and space-separated)
    # Matches: "mm", "hm", "uh", "um", "mmm", "mm hm", "uh um", etc.
    phonetic_pattern = re.compile(r"^[mhu\s]+$")
    
    if phonetic_pattern.match(normalized):
        # Additional check: must contain at least one m or h (not just spaces)
        has_phoneme = any(c in normalized for c in "mhu")
        return has_phoneme
    
    return False



def should_ignore_as_soft_acknowledgment(
    transcript: str, agent_speaking: bool
) -> bool:
    """
    Determine if user input should be ignored as a soft acknowledgment.
    
    Decision Logic:
    1. If agent is NOT speaking → never ignore (all inputs should be processed)
    2. If agent IS speaking:
       a. Empty transcript → ignore (safety check)
       b. Contains any hard interrupt word → do NOT ignore (immediate interrupt)
       c. Contains ONLY soft acknowledgment words → ignore
       d. Contains soft words + other content → do NOT ignore (mixed intent)
    
    Args:
        transcript: The user's speech transcript (from STT)
        agent_speaking: Whether the agent is currently speaking
        
    Returns:
        True if input should be ignored (soft acknowledgment while agent speaking)
        False if input should trigger interruption or processing
        
    Examples:
        >>> should_ignore_as_soft_acknowledgment("yeah", agent_speaking=True)
        True  # Ignore passive acknowledgment
        
        >>> should_ignore_as_soft_acknowledgment("yeah", agent_speaking=False)
        False  # Process all inputs when agent is silent
        
        >>> should_ignore_as_soft_acknowledgment("stop", agent_speaking=True)
        False  # Hard interrupt word → immediate stop
        
        >>> should_ignore_as_soft_acknowledgment("yeah but wait", agent_speaking=True)
        False  # Mixed input → interrupt
        
        >>> should_ignore_as_soft_acknowledgment("hmm okay", agent_speaking=True)
        True  # Multiple soft words → ignore
    """
    # Rule 1: Agent silent → never ignore, process all inputs normally
    if not agent_speaking:
        return False

    # Safety check: empty transcript
    if not transcript or not transcript.strip():
        return True  # Ignore empty input

    # Rule 2a: Check for phonetic utterances BEFORE tokenization
    # This catches fragments like "mm", "hm", "uh" that arrive before stable lexical tokens
    if _is_phonetic_utterance(transcript):
        return True  # Phonetic fragment → ignore

    # Tokenize the transcript
    tokens = _tokenize_transcript(transcript)

    if not tokens:
        return True  # No valid tokens → ignore

    # Rule 2b: Check for hard interrupt words (takes precedence)
    for token in tokens:
        if token in HARD_INTERRUPT_WORDS:
            return False  # Hard interrupt detected → do NOT ignore

    # Rule 2c: Check if ALL tokens are soft acknowledgments
    all_soft = all(token in SOFT_ACKNOWLEDGMENT_WORDS for token in tokens)

    if all_soft:
        return True  # Only soft words → ignore

    # Rule 2d: Mixed input (soft + other content) → do NOT ignore
    return False
