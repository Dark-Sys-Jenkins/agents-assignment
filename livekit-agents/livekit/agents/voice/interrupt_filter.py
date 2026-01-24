from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InterruptionDecision:
    should_interrupt: bool
    should_ignore: bool


@dataclass
class InterruptionFilter:
    ignore_words: set[str]
    interrupt_words: set[str]

    @classmethod
    def default(cls) -> "InterruptionFilter":
        return cls(
            ignore_words={"yeah", "ok", "okay", "hmm", "uh-huh", "right", "yep", "ah"},
            interrupt_words={"wait", "stop", "no", "hold", "cancel"},
        )

    def analyze(self, text: str, agent_speaking: bool) -> InterruptionDecision:
        text = text.lower().strip()
        if not text:
            return InterruptionDecision(False, True)

        words = set(text.replace(",", " ").replace(".", " ").split())

        # semantic interruption overrides everything
        if self.interrupt_words & words:
            return InterruptionDecision(True, False)

        # if agent is speaking and user said only filler → ignore
        if agent_speaking and words.issubset(self.ignore_words):
            return InterruptionDecision(False, True)

        return InterruptionDecision(False, False)