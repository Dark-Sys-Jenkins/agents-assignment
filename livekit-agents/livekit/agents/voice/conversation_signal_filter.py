from __future__ import annotations

import re
from dataclasses import dataclass, field


CORE_BACKCHANNEL_TERMS: list[str] = [
    "yeah", "yes", "ok", "okay", "uh-huh", "uhuh", "uh huh", "hmm", "mhm", "mm-hmm", "mmhmm", "right", "aha", "yep", "yup", "sure", "got it", "i see", "alright", "all right", "mhmm",
]

CORE_INTERRUPT_TERMS: list[str] = [
    "wait", "stop", "no", "hold on", "hold up", "pause", "actually","but", "however", "sorry", "excuse me", "hang on", "one moment", "one second", "question",
]

CORE_QUESTION_RESPONSE_TERMS: list[str] = [
    "yes", "yeah", "yep", "yup"
]

@dataclass
class FilterDecision:
    should_interrupt: bool
    reason: str
    detected_backchannel: list[str] = field(default_factory=list)
    detected_commands: list[str] = field(default_factory=list)


class ConversationSignalFilter:
    def __init__(
        self,
        backchannel_terms: list[str] | None = None,
        interrupt_terms: list[str] | None = None,
        question_response_terms: list[str] | None = None,
    ) -> None:
        self._backchannel_terms = set(
            w.lower() for w in (backchannel_terms or CORE_BACKCHANNEL_TERMS)
        )
        self._interrupt_terms = set(
            w.lower() for w in (interrupt_terms or CORE_INTERRUPT_TERMS)
        )
        self._question_response_terms = set(
            w.lower() for w in (question_response_terms or CORE_QUESTION_RESPONSE_TERMS)
        )
        self._backchannel_phrases = [
            w for w in self._backchannel_terms if " " in w
        ]
        self._interrupt_phrases = [
            w for w in self._interrupt_terms if " " in w
        ]
        self._question_response_phrases = [
            w for w in self._question_response_terms if " " in w
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

    def _contains_terms(self, tokens: list[str], word_set: set[str]) -> list[str]:
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

        interrupt_words = self._contains_terms(tokens, self._interrupt_terms)
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
            response_words = self._contains_terms(tokens, self._question_response_terms)

            if response_phrases or response_words:
                detected_responses = response_phrases + response_words
                return FilterDecision(
                    should_interrupt=True,
                    reason="question_response_detected",
                    detected_commands=detected_responses,
                )

        backchannel_phrases = self._contains_phrase(normalized, self._backchannel_phrases)
        backchannel_terms = self._contains_terms(tokens, self._backchannel_terms)

        all_backchannel = set(backchannel_phrases)
        for phrase in backchannel_phrases:
            phrase_tokens = phrase.split()
            for t in phrase_tokens:
                if t in tokens:
                    tokens = [tok for tok in tokens if tok != t or tok not in phrase_tokens]

        remaining_tokens = [t for t in tokens if t not in self._backchannel_terms]

        if not remaining_tokens:
            return FilterDecision(
                should_interrupt=False,
                reason="backchannel_only",
                detected_backchannel=list(all_backchannel) + backchannel_terms,
            )

        return FilterDecision(
            should_interrupt=True,
            reason="non_backchannel_content",
            detected_backchannel=list(all_backchannel) + backchannel_terms,
        )
