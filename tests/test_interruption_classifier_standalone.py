"""
Tests for the interruption classifier.

Run: python tests/test_interruption_classifier_standalone.py
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Set


class InterruptionDecision(Enum):
    IGNORE = "ignore"
    INTERRUPT = "interrupt"
    RESPOND = "respond"


@dataclass
class InterruptionConfig:
    soft_words: Set[str] = field(default_factory=lambda: {
        "yeah", "yea", "yep", "yup", "yes",
        "ok", "okay", "k",
        "hmm", "hm", "mm", "mmm", "mhm", "mm-hmm", "mmhmm",
        "uh-huh", "uh huh", "uhuh", "aha", "ah",
        "right", "sure", "alright", "alrighty",
        "got it", "gotcha", "i see", "oh",
        "cool", "nice", "great", "good",
        "true", "exactly", "indeed",
    })

    hard_interrupt_words: Set[str] = field(default_factory=lambda: {
        "stop", "wait", "no", "pause", "hold", "hold on",
        "shut up", "quiet", "enough", "silence",
        "cancel", "abort", "quit", "exit",
        "actually", "but", "however", "wait a second",
        "hold on a second", "one moment", "just a moment",
        "hang on", "never mind", "nevermind",
    })

    debug: bool = False


class InterruptionClassifier:
    def __init__(self, config: InterruptionConfig | None = None) -> None:
        self.config = config or InterruptionConfig()
        self._norm_soft = {self._normalize(w) for w in self.config.soft_words}
        self._norm_hard = {self._normalize(w) for w in self.config.hard_interrupt_words}
        self._soft_phrases = sorted([w for w in self._norm_soft if " " in w], key=len, reverse=True)
        self._hard_phrases = sorted([w for w in self._norm_hard if " " in w], key=len, reverse=True)

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _has_hard_interrupt(self, text: str) -> bool:
        for phrase in self._hard_phrases:
            if phrase in text:
                return True
        single_hard = {w for w in self._norm_hard if " " not in w}
        for word in text.split():
            if word in single_hard:
                return True
        return False

    def _is_all_soft(self, text: str) -> bool:
        remaining = text
        for phrase in self._soft_phrases:
            remaining = remaining.replace(phrase, " ")
        single_soft = {w for w in self._norm_soft if " " not in w}
        for word in remaining.split():
            if word and word not in single_soft:
                return False
        return True

    def classify(self, transcript: str, is_agent_speaking: bool) -> InterruptionDecision:
        if not transcript or not transcript.strip():
            return InterruptionDecision.IGNORE
        normalized = self._normalize(transcript)
        if not is_agent_speaking:
            return InterruptionDecision.RESPOND
        if self._has_hard_interrupt(normalized):
            return InterruptionDecision.INTERRUPT
        if self._is_all_soft(normalized):
            return InterruptionDecision.IGNORE
        return InterruptionDecision.INTERRUPT

    def should_interrupt(self, transcript: str, is_agent_speaking: bool) -> bool:
        return self.classify(transcript, is_agent_speaking) == InterruptionDecision.INTERRUPT

    def should_ignore(self, transcript: str, is_agent_speaking: bool) -> bool:
        return self.classify(transcript, is_agent_speaking) == InterruptionDecision.IGNORE


def run_tests():
    classifier = InterruptionClassifier()
    passed = 0
    failed = 0

    tests = [
        # Scenario 1: Ignore soft words while speaking
        ("yeah", True, InterruptionDecision.IGNORE),
        ("ok", True, InterruptionDecision.IGNORE),
        ("okay", True, InterruptionDecision.IGNORE),
        ("hmm", True, InterruptionDecision.IGNORE),
        ("uh-huh", True, InterruptionDecision.IGNORE),
        ("right", True, InterruptionDecision.IGNORE),
        ("Yeah", True, InterruptionDecision.IGNORE),
        ("YEAH", True, InterruptionDecision.IGNORE),
        ("yeah!", True, InterruptionDecision.IGNORE),
        ("okay yeah uh-huh", True, InterruptionDecision.IGNORE),

        # Scenario 2: Respond to any input while silent
        ("yeah", False, InterruptionDecision.RESPOND),
        ("ok", False, InterruptionDecision.RESPOND),
        ("hello", False, InterruptionDecision.RESPOND),
        ("tell me a story", False, InterruptionDecision.RESPOND),

        # Scenario 3: Interrupt on hard words while speaking
        ("stop", True, InterruptionDecision.INTERRUPT),
        ("wait", True, InterruptionDecision.INTERRUPT),
        ("no", True, InterruptionDecision.INTERRUPT),
        ("pause", True, InterruptionDecision.INTERRUPT),
        ("hold on", True, InterruptionDecision.INTERRUPT),
        ("no stop", True, InterruptionDecision.INTERRUPT),

        # Scenario 4: Interrupt on mixed input while speaking
        ("yeah wait", True, InterruptionDecision.INTERRUPT),
        ("yeah okay but wait", True, InterruptionDecision.INTERRUPT),
        ("ok but stop", True, InterruptionDecision.INTERRUPT),
        ("hmm actually no", True, InterruptionDecision.INTERRUPT),

        # Edge cases
        ("", True, InterruptionDecision.IGNORE),
        ("   ", True, InterruptionDecision.IGNORE),
        ("banana", True, InterruptionDecision.INTERRUPT),
        ("banana", False, InterruptionDecision.RESPOND),
    ]

    print("Running interruption classifier tests...\n")
    for transcript, speaking, expected in tests:
        result = classifier.classify(transcript, speaking)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] '{transcript}' (speaking={speaking}) -> {result.value} (expected: {expected.value})")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
