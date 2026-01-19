"""
Interruption Filter for LiveKit Voice Agents

This module implements context-aware filler word detection to prevent
false interruptions during agent speech while maintaining responsiveness
to genuine user commands.

Key Features:
- State-based filtering: Only filters when agent is speaking
- Accumulation-based detection: Buffers transcript until decision can be made
- Configurable filler words: Easy to customize via configuration
- Zero-latency: Simple set lookup, no ML or external calls

Architecture:
    VAD START → Check if agent speaking → Activate/Deactivate filter
                                ↓
    TRANSCRIPT UPDATE → Check each word → Interrupt if non-filler found
                                ↓
    VAD END → If all fillers → Drop buffer, agent continues
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class FilterDecision(Enum):
    """Decision returned by the interruption filter."""
    
    WAIT = "wait"
    """Keep accumulating, no decision yet."""
    
    INTERRUPT = "interrupt"
    """Non-filler word detected, interrupt the agent."""
    
    IGNORE = "ignore"
    """All words were fillers, ignore this speech segment."""
    
    PASS_THROUGH = "pass_through"
    """Filter not active (agent silent), pass input through normally."""


@dataclass
class FilterResult:
    """Result of a filter operation."""
    
    decision: FilterDecision
    """The filtering decision."""
    
    transcript: str = ""
    """The accumulated transcript (useful when decision is INTERRUPT)."""
    
    reason: str = ""
    """Human-readable reason for the decision."""


# Default filler words that should be ignored during agent speech
DEFAULT_FILLER_WORDS: frozenset[str] = frozenset({
    # Affirmations
    "yeah", "yep", "yes", "yup", "yea",
    "ok", "okay", "k", "kay",
    "sure", "right", "alright", "all right",
    
    # Backchannels / Acknowledgments
    "hmm", "hm", "mm", "mmm", "mhm", "mm-hmm", "mmhmm",
    "uh-huh", "uh huh", "uhuh", "aha", "ah",
    
    # Hesitations
    "uh", "um", "er", "eh", "oh",
    
    # Continuers
    "go on", "continue", "i see", "got it", "gotcha",
    "understood", "makes sense",
    
    # Filler phrases (single words that commonly appear)
    "like", "so", "well", "anyway", "basically",
})


class InterruptionFilter:
    """
    Context-aware interruption filter for voice agents.
    
    This filter implements an accumulation-based approach to handle the
    inherent timing gap between VAD (fast) and STT (slower). Instead of
    making immediate decisions, it accumulates the transcript and checks
    each word as it arrives.
    
    Usage:
        filter = InterruptionFilter(filler_words={"yeah", "ok", "hmm"})
        
        # When user starts speaking
        filter.on_speech_start(agent_is_speaking=True)
        
        # As transcript updates arrive
        result = filter.on_transcript_update("yeah")  # WAIT
        result = filter.on_transcript_update("yeah but")  # INTERRUPT
        
        # When user stops speaking
        result = filter.on_speech_end()  # IGNORE if all fillers
    
    Attributes:
        filler_words: Set of words to treat as fillers/acknowledgments.
        on_decision: Optional callback invoked when a decision is made.
    """
    
    def __init__(
        self,
        filler_words: frozenset[str] | set[str] | list[str] | None = None,
        on_decision: Callable[[FilterResult], None] | None = None,
    ) -> None:
        """
        Initialize the interruption filter.
        
        Args:
            filler_words: Custom set of filler words. If None, uses defaults.
            on_decision: Optional callback when a decision is made.
        """
        if filler_words is None:
            self._filler_words = DEFAULT_FILLER_WORDS
        elif isinstance(filler_words, (list, set)):
            self._filler_words = frozenset(w.lower().strip() for w in filler_words)
        else:
            self._filler_words = filler_words
        
        self._on_decision = on_decision
        
        # State
        self._is_active = False
        self._buffer = ""
        self._words_seen: list[str] = []
        self._found_non_filler = False
        self._decision_made = False
    
    @property
    def filler_words(self) -> frozenset[str]:
        """The set of words treated as fillers."""
        return self._filler_words
    
    @property
    def is_active(self) -> bool:
        """Whether the filter is currently active (accumulating)."""
        return self._is_active
    
    @property
    def current_buffer(self) -> str:
        """The current accumulated transcript."""
        return self._buffer
    
    def _reset(self) -> None:
        """Reset internal state for a new speech segment."""
        self._buffer = ""
        self._words_seen = []
        self._found_non_filler = False
        self._decision_made = False
    
    def _normalize_word(self, word: str) -> str:
        """Normalize a word for comparison."""
        # Remove punctuation and convert to lowercase
        return re.sub(r'[^\w\s-]', '', word.lower().strip())
    
    def _is_filler(self, word: str) -> bool:
        """Check if a word is a filler word."""
        normalized = self._normalize_word(word)
        if not normalized:
            return True  # Empty/punctuation-only = treat as filler
        return normalized in self._filler_words
    
    def _extract_new_words(self, new_transcript: str) -> list[str]:
        """Extract words that are new compared to the buffer."""
        # Simple approach: split and compare
        new_words = new_transcript.split()
        old_word_count = len(self._buffer.split()) if self._buffer else 0
        return new_words[old_word_count:]
    
    def _make_decision(self, decision: FilterDecision, reason: str) -> FilterResult:
        """Create and optionally dispatch a filter result."""
        result = FilterResult(
            decision=decision,
            transcript=self._buffer,
            reason=reason,
        )
        if self._on_decision:
            self._on_decision(result)
        return result
    
    def on_speech_start(self, agent_is_speaking: bool) -> FilterResult:
        """
        Called when VAD detects start of user speech.
        
        This is the context-aware gate: filtering only activates when
        the agent is currently speaking.
        
        Args:
            agent_is_speaking: True if the agent is currently outputting audio.
        
        Returns:
            FilterResult indicating whether filter is now active.
        """
        self._reset()
        
        if agent_is_speaking:
            self._is_active = True
            return self._make_decision(
                FilterDecision.WAIT,
                "Filter activated: agent is speaking, will accumulate transcript"
            )
        else:
            self._is_active = False
            return self._make_decision(
                FilterDecision.PASS_THROUGH,
                "Filter inactive: agent is silent, all input passes through"
            )
    
    def on_transcript_update(self, transcript: str) -> FilterResult:
        """
        Called when STT provides a transcript update (interim or final).
        
        Checks each new word - if any non-filler is found, returns INTERRUPT.
        
        Args:
            transcript: The current (possibly partial) transcript.
        
        Returns:
            FilterResult with decision: WAIT, INTERRUPT, or PASS_THROUGH.
        """
        if not self._is_active:
            return self._make_decision(
                FilterDecision.PASS_THROUGH,
                "Filter inactive, passing through"
            )
        
        if self._decision_made:
            # Already decided to interrupt, maintain that decision
            return self._make_decision(
                FilterDecision.INTERRUPT,
                f"Already decided to interrupt on non-filler word"
            )
        
        # Extract new words since last update
        new_words = self._extract_new_words(transcript)
        self._buffer = transcript
        
        # Check each new word
        for word in new_words:
            normalized = self._normalize_word(word)
            if not normalized:
                continue
                
            self._words_seen.append(normalized)
            
            if not self._is_filler(word):
                # Found a non-filler word - this is a real interruption!
                self._found_non_filler = True
                self._decision_made = True
                return self._make_decision(
                    FilterDecision.INTERRUPT,
                    f"Non-filler word detected: '{normalized}'"
                )
        
        # All new words were fillers, keep waiting
        return self._make_decision(
            FilterDecision.WAIT,
            f"All words are fillers so far: {self._words_seen}"
        )
    
    def on_speech_end(self) -> FilterResult:
        """
        Called when VAD detects end of user speech.
        
        If we reach here without finding a non-filler, the entire speech
        segment was fillers and should be ignored.
        
        Returns:
            FilterResult: IGNORE if all fillers, INTERRUPT if non-filler was found.
        """
        if not self._is_active:
            result = self._make_decision(
                FilterDecision.PASS_THROUGH,
                "Filter was inactive"
            )
            self._is_active = False
            return result
        
        self._is_active = False
        
        if self._found_non_filler:
            return self._make_decision(
                FilterDecision.INTERRUPT,
                f"Speech ended with non-filler content: {self._buffer}"
            )
        else:
            return self._make_decision(
                FilterDecision.IGNORE,
                f"Speech ended with only fillers: {self._words_seen}"
            )
    
    def force_interrupt(self) -> FilterResult:
        """
        Force an interrupt decision regardless of current state.
        
        Useful when other conditions require immediate interruption
        (e.g., specific command words detected by another system).
        
        Returns:
            FilterResult with INTERRUPT decision.
        """
        self._found_non_filler = True
        self._decision_made = True
        return self._make_decision(
            FilterDecision.INTERRUPT,
            "Forced interrupt requested"
        )


# Convenience function for creating filter with custom words
def create_interruption_filter(
    filler_words: list[str] | None = None,
    extend_defaults: bool = True,
) -> InterruptionFilter:
    """
    Create an interruption filter with optional custom filler words.
    
    Args:
        filler_words: List of custom filler words.
        extend_defaults: If True, adds custom words to defaults.
                        If False, uses only custom words.
    
    Returns:
        Configured InterruptionFilter instance.
    
    Example:
        # Use defaults plus custom words
        filter = create_interruption_filter(
            filler_words=["totally", "absolutely"],
            extend_defaults=True
        )
        
        # Use only custom words
        filter = create_interruption_filter(
            filler_words=["yes", "no", "maybe"],
            extend_defaults=False
        )
    """
    if filler_words is None:
        return InterruptionFilter()
    
    if extend_defaults:
        combined = set(DEFAULT_FILLER_WORDS)
        combined.update(w.lower().strip() for w in filler_words)
        return InterruptionFilter(filler_words=frozenset(combined))
    else:
        return InterruptionFilter(filler_words=frozenset(filler_words))
