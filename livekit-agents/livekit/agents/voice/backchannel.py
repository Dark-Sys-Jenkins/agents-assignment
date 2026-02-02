"""Backchannel handling for voice agents.

Backchannels are short affirmative responses (like "yeah", "okay", "uh-huh") that 
allow users to acknowledge agent speech without interrupting the agent's output.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from ..log import logger

if TYPE_CHECKING:
    from livekit import rtc


# Backchannel words - short affirmative responses that shouldn't interrupt agent speech
BACKCHANNEL_WORDS: frozenset[str] = frozenset({
    "yeah", "yep", "yes", "okay", "ok", "uh-huh", "uh huh", "uhuh",
    "mm-hmm", "mmhmm", "mm hmm", "mhm", "right", "sure", "got it",
    "i see", "go on", "continue", "alright", "all right", "aha",
})

# Exit command words - commands that always trigger session exit
EXIT_COMMAND_WORDS: frozenset[str] = frozenset({
    "exit", "quit", "goodbye", "bye", "bye-bye", "byebye", "stop", "end",
    "terminate", "close", "hang up", "hangup", "see you", "take care",
})


class BackchannelHandler:
    """Handles backchannel detection and audio pause/resume logic."""

    def __init__(self) -> None:
        self.paused_speech: any = None  # SpeechHandle
        self.false_interruption_timer: asyncio.TimerHandle | None = None
        self.interrupt_paused_speech_task: asyncio.Task[None] | None = None
        self.resume_paused_called = False
        self.last_skipped_backchannel_transcript: str | None = None
        self.Exit_Command_Words = EXIT_COMMAND_WORDS
        self.Back_Channel_Words = BACKCHANNEL_WORDS

    def is_backchannel(self, text: str) -> bool:
        """Check if transcript contains only backchannel/affirmative words or exit commands."""
        # Fast normalize: remove punctuation and convert to lowercase
        normalized = re.sub(r"[^\w\s-]", "", text.lower()).strip()

        if not normalized:
            return False

        # Check exit commands FIRST (highest priority)
        if normalized in self.Exit_Command_Words:
            logger.info("[BACKCHANNEL] Exit command detected", extra={"transcript": text})
            return True
        
        # Then check backchannel words (lower priority)
        if normalized in self.Back_Channel_Words:
            logger.info("[BACKCHANNEL] Detected", extra={"transcript": text})
            return True

        # Fast space variation check - only compute if needed
        normalized_no_space = normalized.replace(" ", "")
        if len(normalized_no_space) < 2:  # Skip very short strings
            logger.debug("[BACKCHANNEL] Not matched", extra={"transcript": text})
            return False

        # Check exit commands with space variations
        for exit_word in self.Exit_Command_Words:
            if normalized_no_space == exit_word.replace(" ", ""):
                logger.info("[BACKCHANNEL] Exit command detected", extra={"transcript": text})
                return True
        
        # Check backchannel words with space variations
        for bc_word in self.Back_Channel_Words:
            if normalized_no_space == bc_word.replace(" ", ""):
                logger.info("[BACKCHANNEL] Detected", extra={"transcript": text})
                return True

        logger.debug("[BACKCHANNEL] Not matched", extra={"transcript": text})
        return False

    def should_skip_transcript(self, transcript: str) -> bool:
        """Check if this transcript should be skipped (e.g., backchannel that was resumed)."""
        # Fast exit if no backchannel was skipped
        if self.last_skipped_backchannel_transcript is None:
            return False
        # Fast comparison of normalized strings
        return (
            transcript.lower().strip() 
            == self.last_skipped_backchannel_transcript.lower().strip()
        )

    def start_false_interruption_timer(
        self, timeout: float, on_timeout_callback: callable
    ) -> None:
        """Start a timer to resume paused audio if no user input arrives."""
        if self.false_interruption_timer is not None:
            self.false_interruption_timer.cancel()

        self.false_interruption_timer = asyncio.get_event_loop().call_later(
            timeout, on_timeout_callback
        )

    def cancel_false_interruption_timer(self) -> None:
        """Cancel the false interruption timer."""
        if self.false_interruption_timer is not None:
            self.false_interruption_timer.cancel()
            self.false_interruption_timer = None

    def reset_resume_flag(self) -> None:
        """Reset the resume called flag for a new pause cycle."""
        self.resume_paused_called = False

    def mark_resume_called(self) -> None:
        """Mark that resume has been called to prevent duplicate calls."""
        self.resume_paused_called = True

    def is_resume_already_called(self) -> bool:
        """Check if resume was already called in this cycle."""
        return self.resume_paused_called
