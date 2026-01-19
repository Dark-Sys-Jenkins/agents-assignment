"""
Smart interruption handler for LiveKit agents.

This module implements context-aware interruption handling that distinguishes between
passive acknowledgements (backchanneling) and active interruptions based on agent state.

The handler uses the following logic matrix:
- User says backchanneling word (yeah, ok, hmm, etc.) + Agent is speaking → IGNORE
- User says command word (stop, wait, no, etc.) + Agent is speaking → INTERRUPT
- User says backchanneling word + Agent is silent → RESPOND (allow interruption)
- User says command word + Agent is silent → RESPOND (allow interruption)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Set

logger = logging.getLogger(__name__)


@dataclass
class BackchannelingConfig:
    """Configuration for backchanneling (passive acknowledgement) detection."""

    # Words that indicate passive acknowledgement (ignore when agent is speaking)
    backchanneling_words: Set[str] = field(
        default_factory=lambda: {
            "yeah", "yep", "yes", "yea",
            "ok", "okay", "okey",
            "hmm", "hm", "mm", "mmm",
            "aha", "ah", "ohh", "oh",
            "right", "uh-huh", "uhhuh", "uh huh",
            "uh", "um", "umm", "uhh",
            "sure", "exactly", "absolutely",
            "mhm", "mhmm", "mm-hmm", "mmhmm",
            "gotcha", "got it",
        }
    )

    # Words that indicate active commands/interruptions (always interrupt)
    command_words: Set[str] = field(
        default_factory=lambda: {
            "stop", "wait", "hold", "hold on",
            "no", "nope", "not", "never",
            "pause", "later", "never mind",
            "wrong", "incorrect", "that's wrong",
            "repeat", "again", "rewind",
            "cancel", "reset", "restart",
            "clear", "skip",
        }
    )

    # Enable/disable the smart filtering
    enabled: bool = True


class InterruptionAnalyzer:
    """
    Analyzes user speech to determine if it's a backchanneling or active interruption.

    This class provides the core logic for distinguishing between passive acknowledgements
    and active interruptions based on transcript analysis and agent state.
    """

    def __init__(self, config: BackchannelingConfig | None = None):
        """
        Initialize the interruption analyzer.

        Args:
            config: Backchanneling configuration. Uses defaults if None.
        """
        self.config = config or BackchannelingConfig()
        self._word_cache: dict[str, bool] = {}

    def should_ignore_interruption(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> bool:
        """
        Determine if an interruption should be ignored (filtered out).

        Logic:
        - If agent is NOT speaking: never ignore (return False)
        - If agent IS speaking:
          - If transcript contains command words: don't ignore (return False)
          - If transcript is ONLY backchanneling words: ignore (return True)

        Args:
            transcript: The user's transcribed speech
            agent_is_speaking: Whether the agent is currently speaking/playing audio

        Returns:
            True if the interruption should be ignored, False otherwise
        """
        if not self.config.enabled or not agent_is_speaking:
            return False

        # Normalize transcript
        normalized = self._normalize_text(transcript)

        # Extract words from transcript
        words = self._extract_words(normalized)

        if not words:
            # Empty transcript, ignore
            return True

        # Check if transcript contains any command words
        has_command = any(word in self.config.command_words for word in words)

        if has_command:
            # Contains a command, don't ignore (interrupt)
            logger.debug(
                f"Detected command word in transcript: '{transcript}'. Allowing interruption.",
                extra={"transcript": transcript, "words": words},
            )
            return False

        # Check if all words are backchanneling
        all_backchanneling = all(word in self.config.backchanneling_words for word in words)

        if all_backchanneling:
            # All words are backchanneling, ignore the interruption
            logger.debug(
                f"Detected backchanneling in transcript: '{transcript}'. Filtering interruption.",
                extra={"transcript": transcript, "words": words},
            )
            return True

        # Contains unknown words mixed with backchanneling - be conservative and interrupt
        logger.debug(
            f"Detected mixed/unknown content in transcript: '{transcript}'. Allowing interruption.",
            extra={"transcript": transcript, "words": words},
        )
        return False

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for analysis.

        Converts to lowercase and strips whitespace.
        """
        return text.lower().strip()

    def _extract_words(self, text: str) -> list[str]:
        """
        Extract individual words from text.

        Handles contractions and common multi-word backchanneling phrases.
        """
        # Handle common multi-word phrases first
        text = text.replace("uh-huh", "uhhuh")
        text = text.replace("uh huh", "uhhuh")
        text = text.replace("hold on", "holdon")
        text = text.replace("never mind", "nevermind")
        text = text.replace("that's wrong", "thatswrong")
        text = text.replace("got it", "gotit")
        text = text.replace("mm-hmm", "mmhmm")

        # Split on whitespace and punctuation
        import re

        # Split on whitespace and punctuation, but keep the words
        words = re.findall(r'\b\w+\b', text)

        return words

    def get_analysis(
        self,
        transcript: str,
        agent_is_speaking: bool,
    ) -> dict:
        """
        Get detailed analysis of the transcript for logging/debugging.

        Args:
            transcript: The user's transcribed speech
            agent_is_speaking: Whether the agent is currently speaking

        Returns:
            Dictionary with analysis details
        """
        normalized = self._normalize_text(transcript)
        words = self._extract_words(normalized)

        backchanneling = [w for w in words if w in self.config.backchanneling_words]
        commands = [w for w in words if w in self.config.command_words]
        unknown = [w for w in words if w not in self.config.backchanneling_words
                   and w not in self.config.command_words]

        should_ignore = self.should_ignore_interruption(transcript, agent_is_speaking)

        return {
            "original_transcript": transcript,
            "normalized": normalized,
            "words": words,
            "backchanneling_words": backchanneling,
            "command_words": commands,
            "unknown_words": unknown,
            "agent_is_speaking": agent_is_speaking,
            "should_ignore": should_ignore,
        }
