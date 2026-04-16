"""Backchannel detection for intelligent interruption handling.

Distinguishes between passive acknowledgements ("yeah", "ok", "hmm") and
active interruptions ("stop", "wait", "no") based on whether the agent is
currently speaking or silent.
"""

from __future__ import annotations

import re
from collections.abc import Set

DEFAULT_BACKCHANNEL_WORDS: frozenset[str] = frozenset(
    {
        "yeah",
        "yep",
        "yup",
        "yes",
        "ok",
        "okay",
        "hmm",
        "hm",
        "mhm",
        "mm",
        "uh-huh",
        "uh huh",
        "uhuh",
        "ah",
        "aha",
        "right",
        "sure",
        "got it",
        "i see",
        "alright",
        "cool",
    }
)

_WORD_SPLIT_RE = re.compile(r"[^\w'-]+", re.UNICODE)


def is_backchannel(transcript: str, backchannel_words: Set[str]) -> bool:
    """Check if the entire transcript consists only of backchannel words.

    Returns True if every word/phrase in the transcript is a backchannel word,
    meaning it should be ignored while the agent is speaking.

    For mixed inputs like "yeah okay but wait", returns False because
    "but" and "wait" are not backchannel words.
    """
    text = transcript.strip().lower()
    if not text:
        return False

    for phrase in backchannel_words:
        if " " in phrase and phrase in text:
            text = text.replace(phrase, " ")

    words = [w for w in _WORD_SPLIT_RE.split(text) if w]
    if not words:
        return True

    single_bc = {w for w in backchannel_words if " " not in w}
    return all(w in single_bc for w in words)
