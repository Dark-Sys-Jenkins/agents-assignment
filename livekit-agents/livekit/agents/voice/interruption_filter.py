from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable

# NOTE: Keep this module dependency-free and fast.


DEFAULT_BACKCHANNEL_WORDS: tuple[str, ...] = (
    # Common acknowledgements / backchannels
    "yeah",
    "yea",
    "yep",
    "yup",
    "ok",
    "okay",
    "hmm",
    "mhm",
    "mm",
    "aha",
    "right",
    "sure",
    "uh",
    "huh",
)


DEFAULT_HARD_INTERRUPT_WORDS: tuple[str, ...] = (
    # Explicit "active interruption" commands
    "stop",
    "wait",
    "no",
    "cancel",
    "pause",
    "hold",
)


_WORD_RE = re.compile(r"[^a-z0-9\s]+")


def _normalize_text(text: str) -> str:
    """Lowercase + remove most punctuation.

    We intentionally keep this cheap: it runs on interim transcripts.
    """
    text = text.lower().strip()
    # treat hyphens/underscores as word separators ("uh-huh" -> "uh huh")
    text = text.replace("-", " ").replace("_", " ")
    text = _WORD_RE.sub(" ", text)
    return " ".join(text.split())


def _tokenize(text: str) -> list[str]:
    norm = _normalize_text(text)
    return norm.split() if norm else []


def _parse_env_list(env_name: str) -> tuple[str, ...] | None:
    raw = os.getenv(env_name)
    if raw is None:
        return None
    items = [s.strip().lower() for s in raw.split(",")]
    items = [s for s in items if s]
    return tuple(items)


@dataclass(frozen=True)
class InterruptionDecision:
    should_interrupt: bool
    is_backchannel: bool
    has_hard_command: bool
    tokens: tuple[str, ...]


class InterruptionFilter:
    """Classify user transcripts into backchannel vs active interruption.

    This is used *only* when the agent is currently speaking.
    """

    def __init__(
        self,
        *,
        backchannel_words: Iterable[str],
        hard_interrupt_words: Iterable[str],
    ) -> None:
        self._backchannel = {w.strip().lower() for w in backchannel_words if w.strip()}
        self._hard = {w.strip().lower() for w in hard_interrupt_words if w.strip()}

    @property
    def backchannel_words(self) -> frozenset[str]:
        return frozenset(self._backchannel)

    @property
    def hard_interrupt_words(self) -> frozenset[str]:
        return frozenset(self._hard)

    def classify(self, text: str) -> InterruptionDecision:
        tokens = tuple(_tokenize(text))
        if not tokens:
            return InterruptionDecision(
                should_interrupt=False,
                is_backchannel=False,
                has_hard_command=False,
                tokens=(),
            )

        has_hard = any(t in self._hard for t in tokens)
        if has_hard:
            return InterruptionDecision(
                should_interrupt=True,
                is_backchannel=False,
                has_hard_command=True,
                tokens=tokens,
            )

        is_backchannel = all(t in self._backchannel for t in tokens)
        return InterruptionDecision(
            should_interrupt=not is_backchannel,
            is_backchannel=is_backchannel,
            has_hard_command=False,
            tokens=tokens,
        )


def load_default_backchannel_words() -> tuple[str, ...]:
    """Load backchannel words from env if provided, else defaults.

    Env: LK_BACKCHANNEL_WORDS="yeah,ok,hmm,right"
    """
    env = _parse_env_list("LK_BACKCHANNEL_WORDS")
    return env if env is not None else DEFAULT_BACKCHANNEL_WORDS


def load_default_hard_interrupt_words() -> tuple[str, ...]:
    """Load hard interrupt words from env if provided, else defaults.

    Env: LK_HARD_INTERRUPT_WORDS="stop,wait,no"
    """
    env = _parse_env_list("LK_HARD_INTERRUPT_WORDS")
    return env if env is not None else DEFAULT_HARD_INTERRUPT_WORDS
