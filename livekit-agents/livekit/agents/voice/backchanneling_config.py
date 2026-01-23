from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class BackchannelingConfig:
    enabled: bool = True
    backchanneling_words: FrozenSet[str] = field(default_factory=frozenset)
    interrupt_words: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self):
        overlap = self.backchanneling_words & self.interrupt_words
        if overlap:
            raise ValueError(
                f"Words cannot be both backchanneling and interrupt: {overlap}"
            )


DEFAULT_BACKCHANNELING_WORDS: FrozenSet[str] = frozenset({
    "yeah", "yes", "yep", "yup", "ya", "yea", "yah",
    "ok", "okay", "k", "alright", "all right", "great", "nice", "good", "fine",
    "hmm", "hm", "mm", "mhm", "mhmm", "mmhmm", "um", "uh", "umm", "uhh",
    "uh-huh", "uh huh", "uhuh", "ah-ha", "aha", "a-ha",
    "right", "sure", "true", "i see", "see", "got it", "gotcha", "cool", "awesome",
    "ah", "oh", "ooh", "aah", "wow", "understood",
    "go on", "continue", "and", "then", "go ahead", "roger", "copy that",
    "theek", "theek hai", "haan", "han", "bilkul", "sahi", "sahi hai",
    "accha", "achha", "thik", "thik hai", "ji", "ji haan", "haanji",
    "samajh gaya", "samajh gayi", "pata hai",
    "sí", "si", "vale", "claro", "bueno", "ajá", "aja",
    "oui", "ouais", "d'accord", "ok", "bon",
})

DEFAULT_INTERRUPT_WORDS: FrozenSet[str] = frozenset({
    "wait", "stop", "hold", "pause", "halt", "hold on", "wait a minute","cancel",
    "wait a second", "one moment", "just a moment",
    "no", "nope", "nah", "don't", "do not", "cant", "cannot", "can't","abort",
    "won't", "wouldn't", "shouldn't",
    "hey", "listen", "excuse", "excuse me", "actually", "but", "however","emergency",
    "what", "why", "how", "when", "where", "who", "which", "whose",
    "wrong", "incorrect", "mistake", "that's wrong", "not right",
    "sorry", "pardon", "repeat", "say again", "what did you say",
    "ruk", "ruko", "rukiye", "nahi", "nhi", "mat", "mat karo",
    "galat", "galt", "ek minute", "ek second", "suno", "suniye",
    "espera", "para", "no", "perdón", "perdona",
    "attends", "attendez", "non", "arrête", "pardon",
})


DEFAULT_BACKCHANNELING_CONFIG = BackchannelingConfig(
    enabled=True,
    backchanneling_words=DEFAULT_BACKCHANNELING_WORDS,
    interrupt_words=DEFAULT_INTERRUPT_WORDS,
)


def create_config(
    enabled: bool = True,
    backchanneling_words: set[str] | None = None,
    interrupt_words: set[str] | None = None,
    extend_defaults: bool = True,
) -> BackchannelingConfig:
    if extend_defaults:
        bc_words = DEFAULT_BACKCHANNELING_WORDS | frozenset(backchanneling_words or set())
        int_words = DEFAULT_INTERRUPT_WORDS | frozenset(interrupt_words or set())
    else:
        bc_words = frozenset(backchanneling_words) if backchanneling_words else DEFAULT_BACKCHANNELING_WORDS
        int_words = frozenset(interrupt_words) if interrupt_words else DEFAULT_INTERRUPT_WORDS

    return BackchannelingConfig(
        enabled=enabled,
        backchanneling_words=bc_words,
        interrupt_words=int_words,
    )


def create_english_only_config() -> BackchannelingConfig:
    english_bc = frozenset({
        "yeah", "yes", "yep", "yup", "ya", "yea", "yah",
        "ok", "okay", "k", "alright", "all right",
        "hmm", "hm", "mm", "mhm", "mmhmm", "um", "uh",
        "uh-huh", "uh huh", "uhuh", "ah-ha", "aha",
        "right", "sure", "true", "i see", "got it", "gotcha", "cool",
        "ah", "oh", "go on", "continue",
    })

    english_int = frozenset({
        "wait", "stop", "hold", "pause", "halt", "hold on",
        "no", "nope", "nah", "don't", "can't", "won't",
        "hey", "listen", "excuse me", "actually", "but",
        "what", "why", "how", "when", "where", "who",
        "wrong", "incorrect", "mistake",
        "sorry", "pardon", "repeat",
    })

    return BackchannelingConfig(
        enabled=True,
        backchanneling_words=english_bc,
        interrupt_words=english_int,
    )


__all__ = [
    "BackchannelingConfig",
    "DEFAULT_BACKCHANNELING_CONFIG",
    "DEFAULT_BACKCHANNELING_WORDS",
    "DEFAULT_INTERRUPT_WORDS",
    "create_config",
    "create_english_only_config",
]
