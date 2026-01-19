from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ..log import logger

DEFAULT_FILLER_WORDS: list[str] = [
    "yeah",
    "yes",
    "yep",
    "yup",
    "ok",
    "okay",
    "hmm",
    "hm",
    "uh-huh",
    "uh huh",
    "right",
    "aha",
    "mhm",
    "mmhmm",
    "mm-hmm",
    "mm hmm",
    "sure",
    "alright",
    "got it",
    "i see",
    "uh",
    "um",
    "ah",
    "oh",
]

DEFAULT_DIRECTIVE_WORDS: list[str] = [
    "wait",
    "stop",
    "hold on",
    "hold",
    "pause",
    "no",
    "actually",
    "but",
    "however",
    "excuse me",
    "sorry",
    "question",
    "hang on",
    "one moment",
    "one second",
    "never mind",
    "cancel",
]


class SpeechKind(Enum):
    """Classification of user speech while agent is talking."""

    FILLER = "filler"
    DIRECTIVE = "directive"
    INPUT = "input"
    NOISE = "noise"
    NEW_TURN = "new_turn"


@dataclass
class AnalysisResult:
    """Result of analyzing a transcript."""

    kind: SpeechKind
    allow_continue: bool
    transcript: str

    @property
    def should_ignore(self) -> bool:
        """True if this transcript should be completely ignored."""
        return self.allow_continue


def _load_words_from_env(env_var: str, default: list[str]) -> list[str]:
    """Load a word list from an environment variable (comma-separated)."""
    env_value = os.environ.get(env_var)
    if env_value:
        return [word.strip().lower() for word in env_value.split(",") if word.strip()]
    return default


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, remove punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _split_into_words(text: str) -> list[str]:
    """Split text into individual words."""
    return text.split()


class TranscriptAnalyzer:
    """
    Analyzes user transcripts to determine if agent should continue or stop.

    Logic when agent IS speaking:
    - Empty/no words → NOISE (allow_continue=True)
    - Contains directive word → DIRECTIVE (allow_continue=False) → interrupt
    - All words are fillers → FILLER (allow_continue=True) → continue
    - Otherwise → INPUT (allow_continue=False) → interrupt

    Logic when agent is NOT speaking:
    - Always returns NEW_TURN (allow_continue=False) → process normally

    Example:
        analyzer = TranscriptAnalyzer()

        # Agent speaking, user says "yeah"
        result = analyzer.analyze("yeah", agent_speaking=True)
        # result.kind = FILLER, result.allow_continue = True

        # Agent speaking, user says "stop"
        result = analyzer.analyze("stop", agent_speaking=True)
        # result.kind = DIRECTIVE, result.allow_continue = False

        # Agent silent, user says "yeah"
        result = analyzer.analyze("yeah", agent_speaking=False)
        # result.kind = NEW_TURN, result.allow_continue = False (process it)
    """

    def __init__(
        self,
        *,
        filler_words: Sequence[str] | None = None,
        directive_words: Sequence[str] | None = None,
    ) -> None:
        """
        Initialize the TranscriptAnalyzer.

        Args:
            filler_words: Words to treat as passive acknowledgements.
                Defaults to DEFAULT_FILLER_WORDS. Can be overridden via
                LIVEKIT_FILLER_WORDS environment variable.
            directive_words: Words that always trigger interruption.
                Defaults to DEFAULT_DIRECTIVE_WORDS. Can be overridden via
                LIVEKIT_DIRECTIVE_WORDS environment variable.
        """
        words_source = (
            filler_words
            if filler_words is not None
            else _load_words_from_env("LIVEKIT_FILLER_WORDS", DEFAULT_FILLER_WORDS)
        )
        self._filler_words: set[str] = {word.lower() for word in words_source}

        self._directive_words: list[str] = [
            word.lower()
            for word in (
                directive_words
                if directive_words is not None
                else _load_words_from_env("LIVEKIT_DIRECTIVE_WORDS", DEFAULT_DIRECTIVE_WORDS)
            )
        ]
        self._directive_words.sort(key=len, reverse=True)

    @property
    def filler_words(self) -> set[str]:
        """Get the set of filler words."""
        return self._filler_words.copy()

    @property
    def directive_words(self) -> list[str]:
        """Get the list of directive words."""
        return self._directive_words.copy()

    def _contains_directive(self, normalized_text: str) -> bool:
        """Check if text contains any directive word/phrase."""
        for word in self._directive_words:
            if word in normalized_text:
                return True
        return False

    def _is_all_fillers(self, normalized_text: str) -> bool:
        """Check if text consists only of filler words."""
        words = _split_into_words(normalized_text)
        if not words:
            return True

        for word in words:
            if word not in self._filler_words:
                return False
        return True

    def analyze(self, transcript: str, *, agent_speaking: bool) -> AnalysisResult:
        """
        Analyze a transcript and determine the appropriate action.

        Args:
            transcript: The user's speech transcript.
            agent_speaking: Whether the agent is currently speaking.

        Returns:
            AnalysisResult with kind and allow_continue flag.
        """
        if not agent_speaking:
            return AnalysisResult(
                kind=SpeechKind.NEW_TURN,
                allow_continue=False,
                transcript=transcript,
            )

        normalized = _normalize_text(transcript)

        if not normalized:
            logger.debug("transcript_analyzer: empty/noise - allowing agent to continue")
            return AnalysisResult(
                kind=SpeechKind.NOISE,
                allow_continue=True,
                transcript=transcript,
            )

        if self._contains_directive(normalized):
            logger.debug(
                "transcript_analyzer: directive detected - interrupting agent",
                extra={"transcript": transcript, "normalized": normalized},
            )
            return AnalysisResult(
                kind=SpeechKind.DIRECTIVE,
                allow_continue=False,
                transcript=transcript,
            )

        if self._is_all_fillers(normalized):
            logger.debug(
                "transcript_analyzer: filler words only - allowing agent to continue",
                extra={"transcript": transcript, "normalized": normalized},
            )
            return AnalysisResult(
                kind=SpeechKind.FILLER,
                allow_continue=True,
                transcript=transcript,
            )

        logger.debug(
            "transcript_analyzer: real input detected - interrupting agent",
            extra={"transcript": transcript, "normalized": normalized},
        )
        return AnalysisResult(
            kind=SpeechKind.INPUT,
            allow_continue=False,
            transcript=transcript,
        )


class BackchannelingFilter(TranscriptAnalyzer):
    """Backward compatible alias for TranscriptAnalyzer."""

    def __init__(
        self,
        *,
        ignore_words: Sequence[str] | None = None,
        interrupt_words: Sequence[str] | None = None,
    ) -> None:
        super().__init__(
            filler_words=ignore_words,
            directive_words=interrupt_words,
        )

    def should_ignore(self, transcript: str, *, agent_speaking: bool) -> bool:
        """Check if transcript should be ignored (backward compatible API)."""
        result = self.analyze(transcript, agent_speaking=agent_speaking)
        return result.allow_continue
