from __future__ import annotations

import re
from dataclasses import dataclass, field


DEFAULT_BACKCHANNEL_WORDS: list[str] = [
    "yeah",
    "un-hun",
    "yes",
    "ok",
    "okay",
    "uh-huh",
    "uhuh",
    "uh huh",
    "hmm",
    "mhm",
    "mm-hmm",
    "mmhmm",
    "right",
    "aha",
    "yep",
    "yup",
    "sure",
    "got it",
    "i see",
    "alright",
    "all right",
    "mhmm",
    "indeed",
]

DEFAULT_INTERRUPT_COMMANDS: list[str] = [
    "wait",
    "stop",
    "no",
    "hold on",
    "hold up",
    "pause",
    "actually",
    "but",
    "halt",
    "however",
    "sorry",
    "excuse me",
    "hang on",
    "one moment",
    "one second",
    "question",
    "i have a question",
    "i want to ask",
    "wait, wait",
]

DEFAULT_QUESTION_RESPONSE_WORDS: list[str] = [
    "yes",
    "yeah",
    "yep",
    "yup",
    "right",
    "sure",
    "absolutely",
    "definitely",
    "of course",
    "i think so",
]


@dataclass
class FilterDecision:
    should_interrupt: bool
    reason: str
    detected_backchannel: list[str] = field(default_factory=list)
    detected_commands: list[str] = field(default_factory=list)


class BackchannelHandler:
    def __init__(
        self,
        backchannel_words: list[str] | None = None,
        interrupt_commands: list[str] | None = None,
        question_response_words: list[str] | None = None,
    ) -> None:
        self._backchannel_words = set(
            w.lower() for w in (backchannel_words or DEFAULT_BACKCHANNEL_WORDS)
        )
        self._interrupt_commands = set(
            w.lower() for w in (interrupt_commands or DEFAULT_INTERRUPT_COMMANDS)
        )
        self._question_response_words = set(
            w.lower() for w in (question_response_words or DEFAULT_QUESTION_RESPONSE_WORDS)
        )
        self._backchannel_phrases = [
            w for w in self._backchannel_words if " " in w
        ]
        self._interrupt_phrases = [
            w for w in self._interrupt_commands if " " in w
        ]
        self._question_response_phrases = [
            w for w in self._question_response_words if " " in w
        ]

    def _normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s\-]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _tokenize(self, text: str) -> list[str]:
        return text.split()

    def _contains_phrase(self, text: str, phrases: list[str]) -> list[str]:
        found = []
        for phrase in phrases:
            if phrase in text:
                found.append(phrase)
        return found

    def _contains_words(self, tokens: list[str], word_set: set[str]) -> list[str]:
        found = []
        for token in tokens:
            if token in word_set:
                found.append(token)
        return found

    def should_interrupt(
        self,
        transcript: str,
        agent_is_speaking: bool,
        agent_asked_question: bool = False,
    ) -> FilterDecision:
        if not transcript or not transcript.strip():
            return FilterDecision(
                should_interrupt=False,
                reason="empty_transcript",
            )

        normalized = self._normalize_text(transcript)
        tokens = self._tokenize(normalized)

        if not tokens:
            return FilterDecision(
                should_interrupt=False,
                reason="no_tokens",
            )

        interrupt_phrases = self._contains_phrase(normalized, self._interrupt_phrases)
        if interrupt_phrases:
            return FilterDecision(
                should_interrupt=True,
                reason="interrupt_phrase_detected",
                detected_commands=interrupt_phrases,
            )

        interrupt_words = self._contains_words(tokens, self._interrupt_commands)
        if interrupt_words:
            return FilterDecision(
                should_interrupt=True,
                reason="interrupt_command_detected",
                detected_commands=interrupt_words,
            )

        if not agent_is_speaking:
            return FilterDecision(
                should_interrupt=True,
                reason="agent_silent",
            )

        if agent_asked_question:
            response_phrases = self._contains_phrase(normalized, self._question_response_phrases)
            response_words = self._contains_words(tokens, self._question_response_words)

            if response_phrases or response_words:
                detected_responses = response_phrases + response_words
                return FilterDecision(
                    should_interrupt=True,
                    reason="question_response_detected",
                    detected_commands=detected_responses,
                )

        backchannel_phrases = self._contains_phrase(normalized, self._backchannel_phrases)
        backchannel_words = self._contains_words(tokens, self._backchannel_words)

        all_backchannel = set(backchannel_phrases)
        for phrase in backchannel_phrases:
            phrase_tokens = phrase.split()
            for t in phrase_tokens:
                if t in tokens:
                    tokens = [tok for tok in tokens if tok != t or tok not in phrase_tokens]

        remaining_tokens = [t for t in tokens if t not in self._backchannel_words]

        if not remaining_tokens:
            return FilterDecision(
                should_interrupt=False,
                reason="backchannel_only",
                detected_backchannel=list(all_backchannel) + backchannel_words,
            )

        return FilterDecision(
            should_interrupt=True,
            reason="non_backchannel_content",
            detected_backchannel=list(all_backchannel) + backchannel_words,
        )