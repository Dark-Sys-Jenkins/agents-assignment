import time
import re
from enum import Enum
from typing import Set

class Decision(Enum):
    IGNORE = 0
    INTERRUPT = 1
    NO_DECISION = 2

GRACE_PERIOD_SECONDS = 0.5

class InterruptionController:
    def __init__(self):
        self.state = 'listening'
        self.last_speaking_time = 0

        # O(1) Constant-Time Lookups
        self.IGNORE_WORDS: Set[str] = {
            "yeah", "uh huh", "uh-huh", "ok", "i see", "got it", "mm hmm", "mm-hmm", "right", "sure", "yep"
        }
        self.INTERRUPT_WORDS: Set[str] = {
            "stop", "wait", "no", "pause", "hold", "but", "actually", "what", "huh"
        }

    def update_agent_state(self, state: str):
        """Track agent state for context-aware interrupt decisions."""
        if self.state == 'speaking' and state != 'speaking':
            self.last_speaking_time = time.time()
        self.state = state

    def _normalize(self, text: str) -> str:
        """Custom regex logic converts variations like 'uh-huh' -> 'uh huh' before matching."""
        if not text:
            return ""
        text = text.lower()
        # Handle hyphen normalization
        text = text.replace('-', ' ')
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def decide(self, transcript: str, is_final: bool) -> Decision:
        """
        Process user transcripts through the intelligent interrupt controller.
        
        Logic:
        - Agent Speaking + "Yeah" -> IGNORE (Backchannel)
        - Agent Silent + "Yeah" -> NO_DECISION (User agreement)
        - Any State + "Stop" -> INTERRUPT (Command)
        """
        normalized = self._normalize(transcript)

        if not normalized:
            return Decision.IGNORE

        current_time = time.time()
        # State Transition Grace Period: 500ms safety buffer
        in_grace_period = (current_time - self.last_speaking_time) < GRACE_PERIOD_SECONDS
        is_agent_speaking = self.state == 'speaking' or in_grace_period

        # 1. Check if the entire phrase is a recognized filler (Highest Priority)
        if is_agent_speaking and normalized in self.IGNORE_WORDS:
            return Decision.IGNORE

        words = normalized.split()

        # 2. Check for interrupt commands (Any state)
        if any(word in self.INTERRUPT_WORDS for word in words):
            return Decision.INTERRUPT

        if is_agent_speaking:
            # 3. Check if all words are fillers (e.g. "yeah yeah")
            if all(word in self.IGNORE_WORDS for word in words):
                return Decision.IGNORE

            # 4. If not a recognized filler while speaking, treat as interruption
            return Decision.INTERRUPT
        else:
            # Agent is silent and no interrupt command detected
            # Return NO_DECISION to let the framework handle it normally
            return Decision.NO_DECISION