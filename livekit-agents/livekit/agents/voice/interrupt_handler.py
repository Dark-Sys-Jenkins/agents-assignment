from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = [
    "InterruptAction",
    "InterruptHandler",
    "InterruptAnalysis",
]


class InterruptAction(str, Enum):
    """Action to take for a detected interrupt."""

    IGNORE = "ignore"  # Ignore the interrupt (backchannel only)
    INTERRUPT = "interrupt"  # Process the interrupt (user wants agent to stop)
    RESPOND = "respond"  # User is not interrupting (agent is silent)


@dataclass
class InterruptAnalysis:
    """Result of interrupt analysis."""

    action: InterruptAction
    is_backchannel_only: bool
    has_command_words: bool
    matched_words: list[str]
    confidence: float  # 0.0 to 1.0


class InterruptHandler:

    # Default backchannel words - user acknowledgment signals
    # Including common STT transcription variations
    DEFAULT_BACKCHANNEL_WORDS = {
        # Yeah variations (STT often transcribes differently)
        "yeah",
        "yea",
        "ya",
        "yah",
        "yeh",
        "yeaah",
        "yeahh",
        # Yes variations
        "yep",
        "yup",
        "yes",
        "yess",
        # Okay variations (STT often transcribes differently)
        "okay",
        "ok",
        "okey",
        "okk",
        "kay",
        "k",
        "kk",
        "okaay",
        "alright",
        "all right",
        "aight",
        # Sure variations
        "sure",
        "for sure",
        "sure thing",
        # Acknowledgment sounds
        "uh-huh",
        "uh huh",
        "uhuh",
        "mm-hmm",
        "mm hmm",
        "mmhmm",
        "mhm",
        "mmm",
        "hmm",
        "hm",
        "hmmm",
        "uh",
        "uhh",
        "uhhh",
        "um",
        "umm",
        "ummm",
        "ah",
        "ahh",
        "oh",
        "ohh",
        # Right variations
        "right",
        "rite",
        # Understanding/agreement phrases
        "i see",
        "i got it",
        "got it",
        "gotcha",
        "makes sense",
        "understood",
        "copy that",
        "all good",
        "perfect",
        "nice",
        "cool",
        "great",
        "awesome",
        "interesting",
        "no problem",
        "you're right",
        "that's right",
        "i agree",
        "totally",
        "exactly",
        "absolutely",
        "definitely",
        "indeed",
        "quite",
        "go ahead",
        "please continue",
        "go on",
        "continue",
    }

    # Default command words - direct instructions to agent
    DEFAULT_COMMAND_WORDS = {
        "wait",
        "hold on",
        "stop",
        "pause",
        "hold it",
        "hold up",
        "no",
        "nope",
        "don't",
        "don't do that",
        "cancel",
        "never mind",
        "never",
        "forget it",
        "ignore that",
        "skip that",
        "skip it",
        "back up",
        "rewind",
        "again",
        "repeat",
        "slower",
        "faster",
        "louder",
        "quieter",
        "quieter please",
        "speak up",
        "what",
        "huh",
        "pardon",
        "come again",
        "say again",
        "say that again",
        "redo",
        "change that",
        "different",
        "something else",
        "alternative",
        "try again",
        "one more time",
        "rephrase",
        "rephrase that",
        "explain",
        "clarify",
        "say it differently",
        "summarize",
        "start over",
        "begin again",
        "let's start over",
        "restart",
    }

    def __init__(
        self,
        *,
        min_interrupt_duration: int = 200,
        min_interruption_words: int = 1,
        backchannel_words: set[str] | None = None,
        command_words: set[str] | None = None,
    ) -> None:

        self.min_interrupt_duration = min_interrupt_duration
        self.min_interruption_words = min_interruption_words

        # Initialize word sets (lowercase for case-insensitive matching)
        self.backchannel_words = set(
            word.lower() for word in (backchannel_words or self.DEFAULT_BACKCHANNEL_WORDS)
        )
        self.command_words = set(
            word.lower() for word in (command_words or self.DEFAULT_COMMAND_WORDS)
        )

        # Pre-separate single words and multi-word phrases for O(1) lookup
        self._backchannel_singles: set[str] = set()
        self._backchannel_phrases: list[str] = []
        self._command_singles: set[str] = set()
        self._command_phrases: list[str] = []
        self._rebuild_phrase_cache()

    def _rebuild_phrase_cache(self) -> None:
        self._backchannel_singles = {w for w in self.backchannel_words if " " not in w}
        self._backchannel_phrases = [w for w in self.backchannel_words if " " in w]
        self._command_singles = {w for w in self.command_words if " " not in w}
        self._command_phrases = [w for w in self.command_words if " " in w]

    def analyze(
        self,
        transcript: str,
        agent_state: str | None = None,
        speech_duration: int | None = None,
    ) -> InterruptAnalysis:

        # Fast path for empty input
        if not transcript or not transcript.strip():
            return InterruptAnalysis(
                action=InterruptAction.RESPOND,
                is_backchannel_only=False,
                has_command_words=False,
                matched_words=[],
                confidence=0.0,
            )

        transcript_lower = transcript.lower()

        # Tokenize once - O(n) where n is transcript length
        words = [word.strip(".,!?;:\"'") for word in transcript_lower.split()]
        words = [w for w in words if w]  # Remove empty strings

        if not words:
            return InterruptAnalysis(
                action=InterruptAction.RESPOND,
                is_backchannel_only=False,
                has_command_words=False,
                matched_words=[],
                confidence=0.0,
            )

        word_count = len(words)

        # Single-word matching using set intersection - O(min(w, b)) and O(min(w, c))
        word_set = set(words)
        matched_backchannels = list(word_set & self._backchannel_singles)
        matched_commands = list(word_set & self._command_singles)

        # Multi-word phrase matching - only iterate over phrases (typically few)
        # O(p) where p is number of multi-word phrases
        for phrase in self._backchannel_phrases:
            if phrase in transcript_lower:
                matched_backchannels.append(phrase)

        for phrase in self._command_phrases:
            if phrase in transcript_lower:
                matched_commands.append(phrase)

        # Check if entire cleaned transcript is a single backchannel/command
        # O(1) set lookup
        full_cleaned = transcript_lower.strip().strip(".,!?;:\"'").strip()
        if full_cleaned in self.backchannel_words and full_cleaned not in word_set:
            matched_backchannels.append(full_cleaned)
        if full_cleaned in self.command_words and full_cleaned not in word_set:
            matched_commands.append(full_cleaned)

        # Determine classification
        is_backchannel_only = bool(matched_backchannels) and not matched_commands
        has_command_words = bool(matched_commands)

        # Check minimum word threshold
        if word_count < self.min_interruption_words:
            is_backchannel_only = False
            has_command_words = False

        # Decide action based on classification and agent state
        action = self._decide_action(
            is_backchannel_only=is_backchannel_only,
            has_command_words=has_command_words,
            agent_state=agent_state,
            speech_duration=speech_duration,
            word_count=word_count,
        )

        # Calculate confidence (0.0 to 1.0)
        confidence = self._calculate_confidence(
            action=action,
            matched_backchannels=matched_backchannels,
            matched_commands=matched_commands,
            word_count=word_count,
        )

        all_matched = matched_backchannels + matched_commands

        return InterruptAnalysis(
            action=action,
            is_backchannel_only=is_backchannel_only,
            has_command_words=has_command_words,
            matched_words=all_matched,
            confidence=confidence,
        )

    def _decide_action(
        self,
        *,
        is_backchannel_only: bool,
        has_command_words: bool,
        agent_state: str | None,
        speech_duration: int | None,
        word_count: int,
    ) -> InterruptAction:

        # Check duration threshold
        if speech_duration is not None and speech_duration < self.min_interrupt_duration:
            return InterruptAction.RESPOND

        # If it's just backchannel signals, ignore when agent is speaking
        if is_backchannel_only:
            if agent_state and agent_state.lower() in ("speaking", "generating"):
                return InterruptAction.IGNORE
            # If agent is silent and user gives backchannel, respond
            return InterruptAction.RESPOND

        # If there are command words, interrupt
        if has_command_words:
            return InterruptAction.INTERRUPT

        # Default: respond (don't interrupt, but acknowledge)
        return InterruptAction.RESPOND

    def _calculate_confidence(
        self,
        *,
        action: InterruptAction,
        matched_backchannels: list[str],
        matched_commands: list[str],
        word_count: int,
    ) -> float:
        """Calculate confidence score for the action (0.0 to 1.0)."""
        if action == InterruptAction.IGNORE:
            # High confidence if pure backchannel
            return min(1.0, len(matched_backchannels) / word_count) if word_count > 0 else 0.5

        if action == InterruptAction.INTERRUPT:
            # High confidence if commands present
            return min(1.0, len(matched_commands) / word_count) if word_count > 0 else 0.7

        # RESPOND action - medium confidence
        return 0.5

    def add_backchannel_word(self, word: str) -> None:
        """Add a word to the backchannel set."""
        word_lower = word.lower()
        self.backchannel_words.add(word_lower)
        # Update cache
        if " " in word_lower:
            self._backchannel_phrases.append(word_lower)
        else:
            self._backchannel_singles.add(word_lower)

    def add_command_word(self, word: str) -> None:
        """Add a word to the command set."""
        word_lower = word.lower()
        self.command_words.add(word_lower)
        # Update cache
        if " " in word_lower:
            self._command_phrases.append(word_lower)
        else:
            self._command_singles.add(word_lower)

    def remove_backchannel_word(self, word: str) -> None:
        """Remove a word from the backchannel set."""
        word_lower = word.lower()
        self.backchannel_words.discard(word_lower)
        # Update cache
        if " " in word_lower:
            if word_lower in self._backchannel_phrases:
                self._backchannel_phrases.remove(word_lower)
        else:
            self._backchannel_singles.discard(word_lower)

    def remove_command_word(self, word: str) -> None:
        """Remove a word from the command set."""
        word_lower = word.lower()
        self.command_words.discard(word_lower)
        # Update cache
        if " " in word_lower:
            if word_lower in self._command_phrases:
                self._command_phrases.remove(word_lower)
        else:
            self._command_singles.discard(word_lower)
