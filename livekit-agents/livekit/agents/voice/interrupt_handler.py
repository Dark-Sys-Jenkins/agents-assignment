"""
Smart Interrupt Handler for LiveKit Agents

This module implements context-aware filtering for user interruptions.
It distinguishes between passive acknowledgements (backchanneling) and
active interruptions based on whether the agent is currently speaking.

Key Features:
1. Configurable ignore list for passive backchanneling words
2. State-based filtering - only applies when agent is actively speaking
3. Semantic interruption detection for mixed sentences
4. Real-time processing with minimal latency
"""

import logging
import os
from typing import Optional, Set

logger = logging.getLogger(__name__)


class InterruptHandler:
    """
    Context-aware interrupt handler that distinguishes between:
    - Passive acknowledgements (backchanneling): "yeah", "ok", "hmm", etc.
    - Active interruptions (commands): "stop", "wait", "no", etc.
    
    The handler only ignores passive acknowledgements when the agent is
    actively speaking. When silent, all inputs are treated as valid.
    """

    def __init__(
        self,
        ignore_list: Optional[Set[str]] = None,
        command_list: Optional[Set[str]] = None,
    ):
        """
        Initialize the interrupt handler.

        Args:
            ignore_list: Set of words that should be ignored when agent is speaking.
                         Defaults to common backchanneling words.
            command_list: Set of words that force interruption even if agent is speaking.
                         Defaults to common interruption commands.
        """
        # Default backchanneling words that should be ignored when agent is speaking
        self.ignore_list = ignore_list or {
            "yeah",
            "ok",
            "okay",
            "uh-huh",
            "uh huh",
            "hmm",
            "mm",
            "mm-hmm",
            "mmhmm",
            "mhm",
            "right",
            "yep",
            "yup",
            "uh",
            "um",
            "yes",
        }

        # Words that force interruption regardless of agent state
        self.command_list = command_list or {
            "stop",
            "wait",
            "no",
            "nope",
            "pause",
            "hold",
            "hold on",
            "hold up",
            "one second",
            "one sec",
            "hang on",
            "abort",
        }

        logger.debug(
            f"InterruptHandler initialized with ignore_list: {self.ignore_list}, "
            f"command_list: {self.command_list}"
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison: lowercase and strip whitespace."""
        return text.lower().strip()

    @staticmethod
    def _split_into_words(text: str) -> list[str]:
        """Split text into words, normalizing punctuation."""
        import re

        # Remove common punctuation and split
        # Keep hyphens within words (e.g., "uh-huh" becomes ["uh", "huh"])
        words = re.split(r"[\s,!?.;:\s-]+", text.lower().strip())
        return [w for w in words if w]  # Remove empty strings

    def should_ignore_for_backchanneling(
        self, transcript: str, agent_is_speaking: bool
    ) -> bool:
        """
        Determine if an interruption should be ignored based on agent state
        and transcript content.

        Args:
            transcript: The user's spoken text (from STT)
            agent_is_speaking: Whether the agent is currently generating/playing audio

        Returns:
            True if the interruption should be ignored, False otherwise.

        Logic:
            - If agent is silent, always process (return False)
            - If agent is speaking:
                - Check for explicit commands (force interrupt, return False)
                - Check if transcript is purely backchanneling (ignore, return True)
                - Check for mixed sentences (backchanneling + command, return False)
        """
        if not transcript or not agent_is_speaking:
            # Agent is silent: always process the input
            return False

        normalized = self._normalize_text(transcript)
        words = self._split_into_words(normalized)

        if not words:
            return True  # Empty input, ignore

        # Check for explicit interruption commands
        for word in words:
            if word in self.command_list:
                logger.debug(
                    f"Detected interruption command '{word}' in '{transcript}'. "
                    "Will not ignore."
                )
                return False

        # Check if all meaningful words are in the ignore list (backchanneling)
        # Allow articles and single character filler words
        non_filler_words = [
            w for w in words if len(w) > 1 and w not in {"a", "an", "the", "and", "or"}
        ]

        if not non_filler_words:
            # Only filler words, this is backchanneling
            logger.debug(
                f"Detected backchanneling in '{transcript}'. Agent is speaking, will ignore."
            )
            return True

        # Check if all non-filler words are in ignore list
        all_ignored = all(w in self.ignore_list for w in non_filler_words)
        if all_ignored:
            logger.debug(
                f"All words in '{transcript}' are backchanneling. Agent is speaking, will ignore."
            )
            return True

        # Mixed content or non-ignored words detected
        logger.debug(
            f"Mixed or command content detected in '{transcript}'. Agent is speaking, will not ignore."
        )
        return False

    def is_valid_interruption(self, transcript: str, agent_is_speaking: bool) -> bool:
        """
        Determine if a user input should trigger an interruption.

        This is the inverse of should_ignore_for_backchanneling:
        - True if the input should interrupt the agent
        - False if the input should be ignored

        Args:
            transcript: The user's spoken text
            agent_is_speaking: Whether the agent is currently speaking

        Returns:
            True if this should interrupt the agent, False otherwise.
        """
        return not self.should_ignore_for_backchanneling(transcript, agent_is_speaking)

    def get_ignore_list(self) -> Set[str]:
        """Get the current ignore list."""
        return self.ignore_list.copy()

    def get_command_list(self) -> Set[str]:
        """Get the current command list."""
        return self.command_list.copy()

    def add_to_ignore_list(self, word: str) -> None:
        """Add a word to the ignore list."""
        self.ignore_list.add(word.lower())
        logger.debug(f"Added '{word}' to ignore list")

    def add_to_command_list(self, word: str) -> None:
        """Add a word to the command list."""
        self.command_list.add(word.lower())
        logger.debug(f"Added '{word}' to command list")

    def remove_from_ignore_list(self, word: str) -> None:
        """Remove a word from the ignore list."""
        self.ignore_list.discard(word.lower())
        logger.debug(f"Removed '{word}' from ignore list")

    def remove_from_command_list(self, word: str) -> None:
        """Remove a word from the command list."""
        self.command_list.discard(word.lower())
        logger.debug(f"Removed '{word}' from command list")


def create_interrupt_handler_from_env() -> InterruptHandler:
    """
    Create an InterruptHandler with configuration from environment variables.

    Environment Variables:
        AGENT_IGNORE_LIST: Comma-separated list of backchanneling words
        AGENT_COMMAND_LIST: Comma-separated list of interruption commands

    Returns:
        InterruptHandler instance with custom or default configuration
    """
    ignore_list = None
    command_list = None

    if ignore_words := os.getenv("AGENT_IGNORE_LIST"):
        ignore_list = {w.strip() for w in ignore_words.split(",") if w.strip()}
        logger.debug(f"Loaded ignore_list from env: {ignore_list}")

    if command_words := os.getenv("AGENT_COMMAND_LIST"):
        command_list = {w.strip() for w in command_words.split(",") if w.strip()}
        logger.debug(f"Loaded command_list from env: {command_list}")

    return InterruptHandler(ignore_list=ignore_list, command_list=command_list)
