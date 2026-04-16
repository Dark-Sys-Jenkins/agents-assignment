from dataclasses import dataclass
import re


def split_words(text):
    return re.findall(r"\b\w+\b", text.lower())


@dataclass
class BackchannelConfig:
    enabled: bool = True
    backchannel_words: set = None
    interrupt_words: set = None
    min_words_for_interruption: int = 1

    def __post_init__(self):
        if self.backchannel_words is None:
            self.backchannel_words = {"yeah", "ok", "okay", "hmm"}

        if self.interrupt_words is None:
            self.interrupt_words = {"wait", "stop", "no"}


class BackchannelFilter:
    def __init__(self, config):
        self.config = config

    def should_interrupt(self, text, agent_is_speaking):
        words = split_words(text)

        if not agent_is_speaking:
            return "respond"

        if any(word in self.config.interrupt_words for word in words):
            return "interrupt"

        if all(word in self.config.backchannel_words for word in words):
            return "ignore"

        return "interrupt"


f = BackchannelFilter(BackchannelConfig())

tests = [
    ("yeah", True),
    ("ok", True),
    ("wait", True),
    ("yeah wait", True),
    ("what is python", True),
    ("yeah", False),
]

for text, speaking in tests:
    result = f.should_interrupt(text, speaking)
    print(f"{text} | speaking={speaking} => {result}")