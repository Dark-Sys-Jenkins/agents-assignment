"""Interruption decision logic for LiveKit voice agents.

This module implements context-aware interruption classification that distinguishes
between passive acknowledgements (backchanneling) and active interruptions.
"""

from __future__ import annotations

from typing import Literal

# Decision types
InterruptionDecision = Literal["INTERRUPT", "IGNORE", "RESPOND"]

# Passive acknowledgements (soft inputs)
PASSIVE_ACKNOWLEDGEMENTS = {
    "yeah",
    "ok",
    "okay",
    "hmm",
    "aha",
    "uh-huh",
    "uh huh",
    "right",
}

# Interrupt commands (hard inputs)
INTERRUPT_COMMANDS = {
    "stop",
    "wait",
    "no",
    "cancel",
    "hold on",
    "hold",
}


def classify_interruption(
    agent_state: Literal["SPEAKING", "SILENT"],
    user_transcript: str,
) -> InterruptionDecision:
    """Classify user input as INTERRUPT, IGNORE, or RESPOND.
    
    This function implements the core interruption decision logic based on:
    - Agent state (SPEAKING or SILENT)
    - Semantic content of user transcript
    
    Args:
        agent_state: Current state of the agent - "SPEAKING" or "SILENT"
        user_transcript: The transcribed user speech text
        
    Returns:
        One of: "INTERRUPT", "IGNORE", or "RESPOND"
        
    Rules:
        1. If transcript contains ANY interrupt command, return INTERRUPT
        2. If agent is SPEAKING and transcript contains ONLY passive acknowledgements, return IGNORE
        3. If agent is SILENT and transcript contains passive acknowledgement, return RESPOND
        4. If agent is SILENT and transcript contains normal input, return RESPOND
    """
    # Normalize transcript for processing
    transcript_lower = user_transcript.lower().strip()
    
    # Handle empty transcript
    if not transcript_lower:
        # If no transcript, default behavior depends on agent state
        if agent_state == "SPEAKING":
            return "INTERRUPT"  # Unknown input while speaking = interrupt
        else:
            return "RESPOND"  # Unknown input while silent = respond
    
    # Rule 1: Semantic Interruption Rule (Highest Priority)
    # Check if transcript contains ANY interrupt command
    words = transcript_lower.split()
    
    # Remove punctuation from words for matching
    words_clean = [w.strip(".,!?;:") for w in words]
    
    # Check for single-word interrupt commands
    for word in words_clean:
        if word in INTERRUPT_COMMANDS:
            return "INTERRUPT"
    
    # Check for multi-word interrupt commands (substring match)
    for cmd in INTERRUPT_COMMANDS:
        if cmd in transcript_lower:
            return "INTERRUPT"
    
    # Rule 2: Speaking + Passive Acknowledgement
    if agent_state == "SPEAKING":
        # Check if transcript contains ONLY passive acknowledgement words
        transcript_words = set(words_clean)
        # Remove empty strings
        transcript_words.discard("")
        
        # If no words after cleaning, check exact match
        if not transcript_words:
            transcript_normalized = transcript_lower.strip(".,!?;:")
            if transcript_normalized in PASSIVE_ACKNOWLEDGEMENTS:
                return "IGNORE"
        
        # Check if all words are passive acknowledgements
        if transcript_words and transcript_words.issubset(PASSIVE_ACKNOWLEDGEMENTS):
            return "IGNORE"
        
        # Also check for exact matches (handles punctuation variations)
        transcript_normalized = transcript_lower.strip(".,!?;:")
        if transcript_normalized in PASSIVE_ACKNOWLEDGEMENTS:
            return "IGNORE"
    
    # Rule 3 & 4: Silent + Any Input
    if agent_state == "SILENT":
        return "RESPOND"
    
    # Default: if agent is speaking and it's not a passive acknowledgement, interrupt
    # This handles cases where the transcript contains both passive and non-passive words
    return "INTERRUPT"

