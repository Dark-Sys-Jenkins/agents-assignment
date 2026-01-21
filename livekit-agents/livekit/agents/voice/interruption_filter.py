from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

_NON_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[^\w]+", re.UNICODE)
_HM_BACKCHANNEL_RE: Final[re.Pattern[str]] = re.compile(r"^[hm]{2,}$")

# This is intentionally conservative: only common "I'm listening" acknowledgements.
# The filter is only applied while the agent is speaking.
DEFAULT_BACKCHANNEL_WORDS: Final[frozenset[str]] = frozenset(
    {
        "yeah",
        "yea",
        "yes",
        "yep",
        "yup",
        "ya",
        "ok",
        "okay",
        "k",
        "kk",
        "right",
        "sure",
        "uh",
        "uhuh",
        "huh",
        "uhhuh",
        "mm",
        "mhm",
        "hmm",
        "hm",
        "aha",
    }
)

# Tokens that indicate an explicit attempt to take the floor.
# This is checked before backchannel-only detection.
DEFAULT_INTERRUPT_WORDS: Final[frozenset[str]] = frozenset(
    {
        "stop",
        "wait",
        "hold",
        "pause",
        "cancel",
        "no",
    }
)

ENV_BACKCHANNEL_WORDS: Final[str] = "LIVEKIT_BACKCHANNEL_WORDS"
ENV_INTERRUPT_WORDS: Final[str] = "LIVEKIT_INTERRUPT_WORDS"
ENV_INTERRUPT_GATE_TIMEOUT_MS: Final[str] = "LIVEKIT_INTERRUPT_GATE_TIMEOUT_MS"


def _parse_env_words(env_value: str | None) -> list[str] | None:
    if not env_value:
        return None
    words = [w.strip().lower() for w in env_value.split(",")]
    return [w for w in words if w]


def normalize_text(text: str) -> str:
    """
    Normalizes user transcripts for simple token-based matching.

    - lowercases
    - replaces punctuation/hyphens with spaces
    - collapses whitespace
    """
    normalized = _NON_WORD_RE.sub(" ", text.lower()).strip()
    return " ".join(normalized.split())


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


@dataclass(frozen=True)
class BackchannelFilterConfig:
    enabled: bool
    gate_timeout: float
    backchannel_words: frozenset[str]
    interrupt_words: frozenset[str]


def _to_token_set(words: Sequence[str]) -> frozenset[str]:
    tokens: set[str] = set()
    for word in words:
        tokens.update(tokenize(word))
    return frozenset(tokens)


def _normalize_phrases(words: Sequence[str]) -> frozenset[str]:
    phrases: set[str] = set()
    for word in words:
        phrase = normalize_text(word)
        if phrase:
            phrases.add(phrase)
    return frozenset(phrases)


def resolve_backchannel_config(
    *,
    enabled: bool,
    gate_timeout: float,
    backchannel_words: Sequence[str] | None,
    interrupt_words: Sequence[str] | None,
) -> BackchannelFilterConfig:
    env_backchannel_words = _parse_env_words(os.environ.get(ENV_BACKCHANNEL_WORDS))
    env_interrupt_words = _parse_env_words(os.environ.get(ENV_INTERRUPT_WORDS))
    env_gate_ms = os.environ.get(ENV_INTERRUPT_GATE_TIMEOUT_MS)

    resolved_backchannels = (
        _to_token_set(backchannel_words)
        if backchannel_words is not None
        else _to_token_set(env_backchannel_words)
        if env_backchannel_words is not None
        else DEFAULT_BACKCHANNEL_WORDS
    )

    resolved_interrupts = (
        _normalize_phrases(interrupt_words)
        if interrupt_words is not None
        else _normalize_phrases(env_interrupt_words)
        if env_interrupt_words is not None
        else DEFAULT_INTERRUPT_WORDS
    )

    resolved_gate_timeout = gate_timeout
    if env_gate_ms:
        try:
            resolved_gate_timeout = max(0.0, float(env_gate_ms) / 1000.0)
        except ValueError:
            # ignore invalid env var
            pass

    return BackchannelFilterConfig(
        enabled=enabled,
        gate_timeout=resolved_gate_timeout,
        backchannel_words=resolved_backchannels,
        interrupt_words=resolved_interrupts,
    )


def _is_backchannel_token(token: str, *, backchannel_words: set[str]) -> bool:
    if token in backchannel_words:
        return True
    # Catch common "hm/mhm/mmhmm/mhmm/hmmm" variants that STT often spells inconsistently.
    return bool(_HM_BACKCHANNEL_RE.fullmatch(token))


def is_backchannel_only(text: str, *, backchannel_words: Iterable[str]) -> bool:
    tokens = tokenize(text)
    if not tokens:
        return False
    backchannels = set(backchannel_words)
    return all(_is_backchannel_token(t, backchannel_words=backchannels) for t in tokens)


def contains_interrupt_intent(text: str, *, interrupt_words: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    tokens = normalized.split()
    interrupts = set(interrupt_words)
    for w in interrupts:
        if " " in w:
            if w in normalized:
                return True
        elif w in tokens:
            return True
    return False


def should_interrupt_while_speaking(
    text: str,
    *,
    backchannel_words: Iterable[str],
    interrupt_words: Iterable[str],
) -> bool:
    """
    Decision function used only while the agent is speaking:
    - if explicit interrupt intent present => interrupt
    - else if purely backchannel => ignore (no interruption)
    - else => interrupt
    """
    if contains_interrupt_intent(text, interrupt_words=interrupt_words):
        return True
    return not is_backchannel_only(text, backchannel_words=backchannel_words)
