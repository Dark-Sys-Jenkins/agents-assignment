"""
Intelligent Interruption Handler for LiveKit Agents

This module provides context-aware interruption handling that distinguishes between
passive acknowledgements (backchanneling) and active interruptions based on agent state.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..log import logger

if TYPE_CHECKING:
    from .agent_activity import AgentActivity


@dataclass
class InterruptionConfig:
    """Configuration for intelligent interruption handling."""

    # Words/phrases that should be ignored when agent is speaking
    ignore_words: list[str] = field(
        default_factory=lambda: [
            "yeah",
            "ok",
            "okay",
            "hmm",
            "hmmm",
            "uh-huh",
            "uh huh",
            "right",
            "yep",
            "yup",
            "mm-hmm",
            "mm hmm",
            "aha",
            "ah",
            "mhm",
            "sure",
            "got it",
            "gotcha",
        ]
    )

    # Words/phrases that should always trigger interruption
    interrupt_commands: list[str] = field(
        default_factory=lambda: [
            "wait",
            "stop",
            "no",
            "hold",
            "hold on",
            "pause",
            "cancel",
            "never mind",
            "nevermind",
        ]
    )

    # Whether to enable the intelligent handler
    enabled: bool = True

    # Maximum time to wait for STT before allowing interruption (seconds)
    stt_validation_timeout: float = 0.5


class InterruptionHandler:
    """
    Intelligent interruption handler that filters VAD-triggered interruptions
    based on agent state and user input content.
    """

    def __init__(self, config: InterruptionConfig | None = None):
        self._config = config or InterruptionConfig()
        self._agent_speaking = False
        self._agent_stopped_speaking_time: float | None = None  # Track when agent stopped speaking
        self._pending_interruptions: dict[str, asyncio.Task] = {}
        self._transcript_buffer: dict[str, tuple[str, float]] = {}  # session_id -> (text, timestamp)
        self._ignored_transcripts: set[str] = set()  # Track transcripts that were already ignored

    def set_agent_speaking(self, speaking: bool) -> None:
        """Update the agent's speaking state."""
        was_speaking = self._agent_speaking
        self._agent_speaking = speaking
        if not speaking and was_speaking:
            # Agent just stopped speaking - record the time
            import time
            self._agent_stopped_speaking_time = time.time()
            # Clear any pending interruptions when agent stops speaking
            self._clear_pending_interruptions()
        elif speaking:
            # Agent is speaking - clear the stopped time
            self._agent_stopped_speaking_time = None

    def is_agent_speaking(self) -> bool:
        """Check if the agent is currently speaking."""
        if self._agent_speaking:
            return True
        # Also check if agent recently stopped speaking (within last 1.0 seconds)
        # This handles brief gaps where state might not be updated yet
        # We use 1.0s to be more conservative - if agent just stopped, treat as speaking
        if self._agent_stopped_speaking_time is not None:
            import time
            time_since_stopped = time.time() - self._agent_stopped_speaking_time
            if time_since_stopped < 1.0:  # Within 1 second of stopping
                return True  # Treat as still speaking (handles timing edge cases)
        return False

    def should_ignore_interruption(
        self, transcript: str | None = None, session_id: str = "default", speech_duration: float | None = None
    ) -> bool:
        """
        Determine if an interruption should be ignored based on agent state and transcript.

        Args:
            transcript: The user's transcribed text (if available)
            session_id: Unique identifier for this interruption attempt

        Returns:
            True if the interruption should be ignored, False if it should proceed
        """
        if not self._config.enabled:
            return False

        # If no transcript provided, try to get it from buffer
        if not transcript:
            transcript = self.get_transcript(session_id)

        # If we have a transcript, check if it was already ignored
        if transcript:
            normalized = self._normalize_text(transcript)
            if normalized in self._ignored_transcripts:
                logger.debug(
                    f"Transcript '{transcript}' was already ignored - skipping interruption"
                )
                return True  # Already ignored, don't interrupt again

        # Check if agent is speaking (including recently stopped)
        agent_is_speaking = self.is_agent_speaking()
        
        # CRITICAL: If we have a transcript that's in the ignore list, check it FIRST
        # This allows us to ignore backchanneling even if state detection failed
        if transcript and transcript.strip():
            normalized = self._normalize_text(transcript)
            # Check if it's ONLY ignore words (backchanneling)
            if self._is_only_ignore_words(normalized):
                # If it's only ignore words, check if agent was speaking when user started
                # But be more lenient - if we're not sure, default to ignoring if it's short
                if agent_is_speaking:
                    logger.info(
                        f"Transcript '{transcript}' is only ignore words and agent is speaking - IGNORING"
                    )
                    self._ignored_transcripts.add(normalized)
                    return True
                # If agent is not speaking but speech is very short, might still be backchanneling
                # (user might have said it right after agent stopped)
                if speech_duration is not None and speech_duration < 0.5:
                    logger.info(
                        f"Transcript '{transcript}' is only ignore words and speech is very short "
                        f"({speech_duration:.2f}s) - IGNORING (likely backchanneling)"
                    )
                    self._ignored_transcripts.add(normalized)
                    return True
        
        # If agent is not speaking, never ignore (allow normal conversation)
        if not agent_is_speaking:
            # Clear ignored transcripts when agent stops speaking (new conversation turn)
            self._ignored_transcripts.clear()
            return False

        # If still no transcript available, use speech duration as a hint
        # When agent is speaking, short speech is likely backchanneling
        # We're VERY aggressive here: if agent is speaking and speech is short (< 1.0s),
        # default to ignoring (most short utterances when agent is speaking are backchanneling)
        if not transcript or not transcript.strip():
            if agent_is_speaking:  # Use the checked value from above
                # When agent is speaking, be VERY aggressive about ignoring short speech
                # Most short utterances (< 1.0s) are backchanneling ("yeah", "ok", "right", "hmm")
                if speech_duration is not None and speech_duration < 1.0:
                    logger.info(
                        f"Agent is speaking, no transcript yet, but speech duration ({speech_duration:.2f}s) is short - "
                        f"likely backchanneling, IGNORING interruption to prevent any pause"
                    )
                    return True  # Ignore short utterances when agent is speaking (likely backchanneling)
                
                # For longer speech without transcript when agent is speaking, still be cautious
                # But allow it (could be "stop", "wait", "no")
                duration_str = f"{speech_duration:.2f}s" if speech_duration is not None else "unknown"
                logger.debug(
                    f"Agent is speaking, no transcript available, speech duration: {duration_str} - "
                    f"allowing interruption (could be a command)"
                )
            else:
                # When agent is NOT speaking, allow all interruptions (normal conversation)
                duration_str = f"{speech_duration:.2f}s" if speech_duration is not None else "unknown"
                logger.debug(
                    f"Agent not speaking, no transcript available - allowing interruption "
                    f"(speech_duration: {duration_str} if available)"
                )
            return False  # Allow interruption if we can't determine what was said

        # Normalize transcript for comparison
        normalized = self._normalize_text(transcript)

        # Check if transcript contains any interrupt commands
        if self._contains_interrupt_command(normalized):
            return False  # Always interrupt for commands

        # Check if transcript is only ignore words
        if self._is_only_ignore_words(normalized):
            logger.info(
                f"Transcript '{transcript}' (normalized: '{normalized}') contains only ignore words - IGNORING interruption"
            )
            # Mark this transcript as ignored so we don't process it again in on_final_transcript
            self._ignored_transcripts.add(normalized)
            return True  # Ignore backchanneling

        # If transcript contains both ignore words and other content,
        # check if it contains interrupt commands (redundant check, but safe)
        if self._contains_interrupt_command(normalized):
            return False

        # Default: if agent is speaking and transcript is not clearly ignorable, allow interruption
        # This handles edge cases where transcript might be partial or unclear
        return False

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase and remove extra whitespace
        text = text.lower().strip()
        # Remove punctuation for better matching (but keep word boundaries)
        text = re.sub(r"[^\w\s]", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove trailing/leading spaces
        text = text.strip()
        return text

    def _contains_interrupt_command(self, text: str) -> bool:
        """Check if text contains any interrupt command."""
        normalized_text = self._normalize_text(text)
        words = normalized_text.split()

        for command in self._config.interrupt_commands:
            normalized_cmd = self._normalize_text(command)
            cmd_words = normalized_cmd.split()

            # Check if all words of the command appear in sequence
            if len(cmd_words) == 1:
                # Single word command - check if it appears as a word
                if normalized_cmd in words:
                    return True
            else:
                # Multi-word command - check if it appears as a phrase
                if normalized_cmd in normalized_text:
                    return True

        return False

    def _is_only_ignore_words(self, text: str) -> bool:
        """Check if text consists only of ignore words."""
        normalized_text = self._normalize_text(text)
        words = normalized_text.split()

        if not words:
            return False

        # Check if all words are in the ignore list
        ignore_set = {self._normalize_text(word) for word in self._config.ignore_words}

        # Also check for multi-word ignore phrases
        for ignore_phrase in self._config.ignore_words:
            normalized_phrase = self._normalize_text(ignore_phrase)
            if normalized_phrase in normalized_text:
                # If the entire text matches an ignore phrase, it's ignorable
                if normalized_text == normalized_phrase:
                    return True
                # If text starts with ignore phrase, check remaining words
                if normalized_text.startswith(normalized_phrase + " "):
                    remaining = normalized_text[len(normalized_phrase) + 1 :].strip()
                    if not remaining or self._is_only_ignore_words(remaining):
                        return True

        # Check individual words - also handle variations like "hm" vs "hmm" vs "hmmm"
        for word in words:
            word_matched = False
            # Exact match
            if word in ignore_set:
                word_matched = True
            else:
                # Check for partial matches (e.g., "hm" should match "hmm", "hmmm")
                # This handles variations in backchanneling words
                for ignore_word in ignore_set:
                    # If both are short (<= 4 chars) and one is a prefix of the other
                    if len(word) <= 4 and len(ignore_word) <= 4:
                        if word.startswith(ignore_word) or ignore_word.startswith(word):
                            word_matched = True
                            break
            if not word_matched:
                return False
        
        return True

    async def validate_interruption(
        self,
        transcript_getter: callable | None = None,
        session_id: str = "default",
        timeout: float | None = None,
    ) -> bool:
        """
        Validate an interruption by waiting for STT transcript if needed.

        Args:
            transcript_getter: Function that returns current transcript (sync or async)
            session_id: Unique identifier for this interruption attempt
            timeout: Maximum time to wait for transcript (uses config default if None)

        Returns:
            True if interruption should proceed, False if it should be ignored
        """
        if not self._config.enabled:
            return True

        if not self._agent_speaking:
            return True  # Always allow when agent is not speaking

        timeout = timeout or self._config.stt_validation_timeout
        start_time = time.time()

        # Check if we already have a transcript in buffer
        transcript = self.get_transcript(session_id)
        if transcript:
            return not self.should_ignore_interruption(transcript, session_id)

        # Try to get transcript from getter if provided
        if transcript_getter:
            try:
                if asyncio.iscoroutinefunction(transcript_getter):
                    transcript = await asyncio.wait_for(transcript_getter(), timeout=0.1)
                else:
                    transcript = await asyncio.wait_for(
                        asyncio.to_thread(transcript_getter), timeout=0.1
                    )
                if transcript:
                    return not self.should_ignore_interruption(transcript, session_id)
            except asyncio.TimeoutError:
                # Best-effort fast path for transcript; on timeout we fall back to normal polling.
                pass
            except Exception:
                # Unexpected errors in transcript_getter should not break interruption handling;
                # log at debug level and continue with the standard polling-based behavior.
                logger.debug("transcript_getter failed during fast-path STT validation", exc_info=True)

        # Wait for transcript with remaining timeout
        elapsed = time.time() - start_time
        remaining_timeout = max(0.0, timeout - elapsed)

        if remaining_timeout > 0:
            # Poll for transcript update
            poll_interval = 0.05  # Check every 50ms
            end_time = time.time() + remaining_timeout
            while time.time() < end_time:
                transcript = self.get_transcript(session_id)
                if transcript:
                    return not self.should_ignore_interruption(transcript, session_id)
                await asyncio.sleep(poll_interval)

        # If no transcript available after timeout, default to allowing interruption
        # This ensures we don't block legitimate interruptions
        logger.debug(
            f"Interruption validation timeout for session {session_id}, "
            "defaulting to allow interruption"
        )
        return True

    def _clear_pending_interruptions(self) -> None:
        """Clear all pending interruption validation tasks."""
        for task in list(self._pending_interruptions.values()):
            if not task.done():
                task.cancel()
        self._pending_interruptions.clear()

    def update_transcript(self, session_id: str, transcript: str) -> None:
        """Update the transcript buffer for a session."""
        self._transcript_buffer[session_id] = (transcript, time.time())

    def get_transcript(self, session_id: str = "default") -> str | None:
        """Get the latest transcript for a session."""
        if session_id in self._transcript_buffer:
            return self._transcript_buffer[session_id][0]
        return None


def load_config_from_env() -> InterruptionConfig:
    """Load interruption configuration from environment variables."""
    # Start with defaults
    ignore_words = [
        "yeah",
        "ok",
        "okay",
        "hmm",
        "hmmm",
        "uh-huh",
        "uh huh",
        "right",
        "yep",
        "yup",
        "mm-hmm",
        "mm hmm",
        "aha",
        "ah",
        "mhm",
        "sure",
        "got it",
        "gotcha",
    ]
    interrupt_commands = [
        "wait",
        "stop",
        "no",
        "hold",
        "hold on",
        "pause",
        "cancel",
        "never mind",
        "nevermind",
    ]

    # Load ignore words from environment
    ignore_words_env = os.getenv("LIVEKIT_IGNORE_WORDS")
    if ignore_words_env:
        ignore_words = [w.strip().lower() for w in ignore_words_env.split(",") if w.strip()]

    # Load interrupt commands from environment
    interrupt_commands_env = os.getenv("LIVEKIT_INTERRUPT_COMMANDS")
    if interrupt_commands_env:
        interrupt_commands = [
            w.strip().lower() for w in interrupt_commands_env.split(",") if w.strip()
        ]

    # Enable/disable from environment
    enabled_env = os.getenv("LIVEKIT_INTELLIGENT_INTERRUPTIONS", "true")
    enabled = enabled_env.lower() in ("true", "1", "yes", "on")

    # STT validation timeout
    stt_validation_timeout = 0.5
    timeout_env = os.getenv("LIVEKIT_STT_VALIDATION_TIMEOUT")
    if timeout_env:
        try:
            stt_validation_timeout = float(timeout_env)
        except ValueError:
            logger.warning(f"Invalid STT_VALIDATION_TIMEOUT value: {timeout_env}")

    return InterruptionConfig(
        ignore_words=ignore_words,
        interrupt_commands=interrupt_commands,
        enabled=enabled,
        stt_validation_timeout=stt_validation_timeout,
    )
