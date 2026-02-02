"""
Intelligent Interruption Handler

This module implements context-aware interruption handling that distinguishes
between passive acknowledgements (filler words) and active interruptions.

The handler filters out filler words like "yeah", "ok", "hmm" when the agent
is speaking, but allows them when the agent is silent.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Optional

from ..log import logger


@dataclass
class InterruptionHandlerConfig:
    """Configuration for the interruption handler."""

    # List of filler words to ignore when agent is speaking
    ignore_words: list[str]
    
    # Maximum time to wait for STT transcript before making decision (seconds)
    stt_wait_timeout: float = 0.5
    
    # Minimum words required to consider it a valid interruption (if not all filler)
    min_interruption_words: int = 0


class InterruptionHandler:
    """
    Handles intelligent interruption detection by filtering filler words
    when the agent is actively speaking.
    """

    def __init__(self, config: Optional[InterruptionHandlerConfig] = None):
        """
        Initialize the interruption handler.

        Args:
            config: Configuration object. If None, uses default config with
                   environment variable support.
        """
        if config is None:
            # Load ignore words from environment or use defaults
            ignore_words_env = os.getenv(
                "AGENT_IGNORE_WORDS",
                "yeah,ok,hmm,right,uh-huh,uh huh,aha,yep,yup,okay"
            )
            ignore_words = [w.strip().lower() for w in ignore_words_env.split(",")]
            
            config = InterruptionHandlerConfig(
                ignore_words=ignore_words,
                stt_wait_timeout=float(os.getenv("AGENT_STT_WAIT_TIMEOUT", "0.5")),
                min_interruption_words=int(os.getenv("AGENT_MIN_INTERRUPTION_WORDS", "0")),
            )
        
        self.config = config
        self._pending_interruptions: dict[str, asyncio.Task] = {}
        self._interruption_counter = 0

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, remove punctuation)."""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.strip()

    def _is_filler_word(self, word: str) -> bool:
        """Check if a word is in the ignore list."""
        normalized = self._normalize_text(word)
        ignore_list_normalized = [self._normalize_text(w) for w in self.config.ignore_words]
        is_filler = normalized in ignore_list_normalized
        
        if is_filler:
            logger.debug(
                f"Word '{word}' (normalized: '{normalized}') is a filler word",
                extra={"word": word, "normalized": normalized, "ignore_list": self.config.ignore_words}
            )
        
        return is_filler

    def _contains_only_filler_words(self, text: str) -> bool:
        """
        Check if the text contains only filler words.
        
        Args:
            text: The transcript text to check
            
        Returns:
            True if text contains only filler words, False otherwise
        """
        if not text or not text.strip():
            return True
        
        # Normalize the text first
        normalized = self._normalize_text(text)
        
        # Split into words and check each
        words = re.findall(r'\b\w+\b', normalized)
        
        if not words:
            return True
        
        # Check if all words are filler words
        all_filler = all(self._is_filler_word(word) for word in words)
        
        if all_filler:
            logger.debug(
                f"Text contains only filler words: '{text}' -> words: {words}",
                extra={"text": text, "words": words, "ignore_list": self.config.ignore_words}
            )
        
        return all_filler

    def _contains_interruption_command(self, text: str) -> bool:
        """
        Check if text contains interruption commands (not just filler words).
        
        Args:
            text: The transcript text to check
            
        Returns:
            True if text contains commands that should interrupt
        """
        if not text or not text.strip():
            return False
        
        # Normalize the text
        normalized = self._normalize_text(text)
        
        # Check if it contains only filler words
        if self._contains_only_filler_words(normalized):
            return False
        
        # If it has non-filler words, it's a command
        words = re.findall(r'\b\w+\b', normalized)
        non_filler_words = [w for w in words if not self._is_filler_word(w)]
        
        return len(non_filler_words) > 0

    def should_ignore_interruption(
        self,
        *,
        agent_is_speaking: bool,
        transcript: Optional[str] = None,
        wait_for_transcript: bool = True,
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if an interruption should be ignored.
        
        This is the synchronous version that works with available transcript.
        For async version that waits for STT, use should_ignore_interruption_async.
        
        Args:
            agent_is_speaking: Whether the agent is currently speaking
            transcript: Current STT transcript (interim or final)
            wait_for_transcript: Whether to wait for transcript if not available
            
        Returns:
            Tuple of (should_ignore, reason)
            - should_ignore: True if interruption should be ignored
            - reason: Optional reason string for logging
        """
        # If agent is not speaking, never ignore (user input is valid)
        if not agent_is_speaking:
            return False, None
        
        # If no transcript available and we're not waiting, default to interrupt
        # (safer to interrupt than to miss a real command)
        if not transcript:
            if not wait_for_transcript:
                return False, "no_transcript_available"
            # If waiting, we'll handle this in async version
            return None, "waiting_for_transcript"
        
        # Normalize transcript
        normalized = self._normalize_text(transcript)
        
        # Check if it's only filler words
        if self._contains_only_filler_words(normalized):
            logger.info(
                f"Interruption ignored: only filler words detected",
                extra={"original": transcript, "normalized": normalized}
            )
            return True, f"only_filler_words: {transcript}"
        
        # Check if it contains interruption commands
        if self._contains_interruption_command(normalized):
            return False, f"contains_command: {transcript}"
        
        # If we have transcript but it doesn't match patterns, 
        # check word count if configured
        words = re.findall(r'\b\w+\b', normalized)
        if self.config.min_interruption_words > 0:
            if len(words) < self.config.min_interruption_words:
                return True, f"insufficient_words: {len(words)} < {self.config.min_interruption_words}"
        
        # Default: don't ignore (interrupt)
        return False, None

    async def should_ignore_interruption_async(
        self,
        *,
        agent_is_speaking: bool,
        get_transcript: Callable[[], str | Awaitable[str]],
        interruption_id: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Async version that waits for STT transcript if needed.
        
        Args:
            agent_is_speaking: Whether the agent is currently speaking
            get_transcript: Async callable that returns current transcript
            interruption_id: Optional ID for tracking this interruption
            
        Returns:
            Tuple of (should_ignore, reason)
        """
        if not interruption_id:
            interruption_id = f"interrupt_{int(time.time() * 1000)}"
        
        # If agent is not speaking, never ignore
        if not agent_is_speaking:
            return False, None
        
        # Try to get transcript immediately
        if asyncio.iscoroutinefunction(get_transcript):
            transcript = await get_transcript()
        else:
            transcript = get_transcript()
        
        if transcript:
            result, reason = self.should_ignore_interruption(
                agent_is_speaking=agent_is_speaking,
                transcript=transcript,
                wait_for_transcript=False,
            )
            if result is not None:  # Not waiting
                return result, reason
        
        # If no transcript yet, wait for it (with timeout)
        start_time = time.time()
        while time.time() - start_time < self.config.stt_wait_timeout:
            await asyncio.sleep(0.05)  # Check every 50ms
            if asyncio.iscoroutinefunction(get_transcript):
                transcript = await get_transcript()
            else:
                transcript = get_transcript()
            
            if transcript:
                result, reason = self.should_ignore_interruption(
                    agent_is_speaking=agent_is_speaking,
                    transcript=transcript,
                    wait_for_transcript=False,
                )
                if result is not None:
                    return result, reason
        
        # Timeout: default to interrupt (safer)
        logger.warning(
            f"Interruption handler timeout waiting for transcript (id: {interruption_id})"
        )
        return False, "stt_timeout"
