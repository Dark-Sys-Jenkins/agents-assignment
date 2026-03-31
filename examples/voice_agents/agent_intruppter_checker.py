from __future__ import annotations
import os
import re
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

REPORT_PATH = os.getenv("REPORT_PATH", "report.txt")

DEFAULT_BACKCHANNEL_WORDS: set[str] = {
    "ah", "aha", "hm", "hmm", "mhm", "mhmm",
    "uh-huh", "uh", "um", "oh",
    "yes", "yeah", "yep", "yup",
    "ok", "okay", "alright",
    "right", "correct", "exactly",
    "i see", "got it", "makes sense",
    "go on", "keep going", "continue",
}

DEFAULT_INTERRUPT_COMMANDS: set[str] = {
    "stop", "wait", "no", "hold", "pause",
    "cancel", "enough",
    "hold on", "hang on", "actually",
    "listen",
}

def write_report(text: str, category: Category, interrupt: bool):
    with open(REPORT_PATH, "a") as f:
        f.write(f"{text}, {category}, {interrupt}\n")
        
class Category(Enum):
    BACKCHANNEL = "backchannel"
    INTERRUPT = "interrupt"
    MIXED = "mixed"
    UNKNOWN = "unknown"
    
def load_env(env: str, words: set[str]) -> set[str]:
    raw = os.getenv(env)
    if not raw: return words
    return {w.strip().lower() for w in raw.split(",") if w.strip()}


DEFAULT_BACKCHANNEL_WORDS = load_env("BACKCHANNEL_WORDS", DEFAULT_BACKCHANNEL_WORDS)
DEFAULT_INTERRUPT_COMMANDS = load_env("INTERRUPT_COMMANDS", DEFAULT_INTERRUPT_COMMANDS)


@dataclass
class Decision:
    interrupt: bool
    category: Category

def text_transform(text: str) -> list[str]:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.split()


def decision_maker(text: str) -> Decision:
    if not text or not text.strip():
        return Decision(False, Category.UNKNOWN)

    tokens = text_transform(text)
    if not tokens:
        return Decision(False, Category.UNKNOWN)

    if tokens[0] in DEFAULT_INTERRUPT_COMMANDS:
        return Decision(True, Category.INTERRUPT)

    if len(tokens) <= 3 and any(t in DEFAULT_BACKCHANNEL_WORDS for t in tokens):
        return Decision(False, Category.BACKCHANNEL)

    return Decision(True, Category.MIXED)