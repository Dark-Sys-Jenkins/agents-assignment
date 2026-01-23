from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class InterruptionConfig:
    ignore_words: List[str] = field(default_factory=lambda: ["yeah", "ok", "hmm", "right", "uh-huh"])
    interrupt_words: List[str] = field(default_factory=lambda: ["stop", "wait", "no", "hold on", "quiet"])
    case_sensitive: bool = False

@dataclass
class InterruptionDecision:
    should_interrupt: bool
    reason: str
    code: str  # Code for reliable branching: IGNORE, INTERRUPT_WORD, SUBSTANTIVE, AGENT_SILENT

class IntelligentInterruptionHandler:
    def __init__(self, config: Optional[InterruptionConfig] = None):
        self.config = config or InterruptionConfig()

    def should_interrupt(self, transcript: str, agent_speaking: bool) -> InterruptionDecision:
        if not transcript.strip():
            return InterruptionDecision(should_interrupt=False, reason="Empty transcript", code="IGNORE")

        # Normalize text
        text = transcript.lower().strip() if not self.config.case_sensitive else transcript.strip()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()

        if not words:
            return InterruptionDecision(should_interrupt=False, reason="No words detected", code="IGNORE")

        # If agent is silent, we always want to process input
        if not agent_speaking:
            return InterruptionDecision(should_interrupt=True, reason="Agent is silent, process normally", code="AGENT_SILENT")

        # Smart Logic while speaking:
        # 1. Check if any interrupt words are present
        interrupt_list = [w.lower() if not self.config.case_sensitive else w for w in self.config.interrupt_words]
        if any(word in interrupt_list for word in words):
            return InterruptionDecision(should_interrupt=True, reason=f"Hard interrupt detected: {transcript}", code="INTERRUPT_WORD")

        # 2. Check if all words are in the ignore list
        ignore_list = [w.lower() if not self.config.case_sensitive else w for w in self.config.ignore_words]
        if all(word in ignore_list for word in words):
            return InterruptionDecision(should_interrupt=False, reason=f"Ignored feedback: {transcript}", code="IGNORE")

        # 3. Substantive input (words that are not ignored but not hard stops)
        return InterruptionDecision(should_interrupt=True, reason=f"Substantive input: {transcript}", code="SUBSTANTIVE")
