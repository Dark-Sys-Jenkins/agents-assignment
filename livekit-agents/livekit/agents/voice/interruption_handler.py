import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class InterruptionResult:
    should_interrupt: bool
    reason: Literal[
        "dsp_ignored", "backchannel_ignored", "command_detected", "valid_input", "agent_idle"
    ]
    debug_info: str


class InterruptHandler:
    def __init__(self):
        self.MIN_SPEECH_DURATION = 0.45

        self.backchannel_words = {
            "yeah",
            "yes",
            "yep",
            "yup",
            "uh-huh",
            "uh huh",
            "uhuh",
            "ok",
            "okay",
            "k",
            "mm-hmm",
            "mmhmm",
            "mm hmm",
            "mhm",
            "hmm",
            "hm",
            "right",
            "sure",
            "got it",
            "gotcha",
            "aha",
            "ah",
            "oh",
            "i see",
            "alright",
            "cool",
        }

        self.interrupt_commands = {
            "stop",
            "wait",
            "hold on",
            "hold up",
            "pause",
            "no",
            "actually",
            "hang on",
            "one second",
            "excuse me",
            "cancel",
        }

    def evaluate(
        self, transcript: str, speech_duration: float, agent_is_speaking: bool
    ) -> InterruptionResult:
        clean_text = self._normalize(transcript)
        words = clean_text.split()

        if not agent_is_speaking:
            return InterruptionResult(True, "agent_idle", "Agent was silent")

        if any(cmd in clean_text for cmd in self.interrupt_commands):
            return InterruptionResult(True, "command_detected", f"Command word found: {clean_text}")

        if speech_duration < self.MIN_SPEECH_DURATION:
            return InterruptionResult(
                False, "dsp_ignored", f"Duration {speech_duration:.2f}s < threshold"
            )

        if not words:
            return InterruptionResult(False, "backchannel_ignored", f"Backchannel: '{clean_text}'")

        is_pure_backchannel = all(w in self.backchannel_words for w in words)

        if is_pure_backchannel and len(words) <= 3:
            return InterruptionResult(False, "backchannel_ignored", f"Backchannel: {clean_text}")

        return InterruptionResult(True, "valid_input", "Valid speech detected")

    def _normalize(self, text: str) -> str:
        return re.sub(r"[^\w\s]", "", text.lower()).strip()
