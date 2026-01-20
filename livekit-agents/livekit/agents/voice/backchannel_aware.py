"""
Implements backchannel contextual awareness interuption handler that filters users input based on the current state its in

This module differentiates between normal conversation and backchannel contexts, allowing the agent to respond appropriately based on the user's input and the ongoing interaction
It ensures it continues speaking when backchannel cues are detected but when active interruptions are made, it pauses and responds accordingly.

"""
import re


class InterruptionSettings:
    def __init__(
        self,
        filler_words=None,
        enabled=True,
        debug=False,
    ):
        # Short responses people say while listening
        if filler_words is None:
            filler_words = [
            "yeah", "ok", "okay", "hmm", "right", "uh-huh", "huh", "uh",
            "mhm", "mhmm", "yep", "yup", "sure", "exactly", "totally", "cool"
        ]

        self.filler_words = filler_words
        self.enabled = enabled
        self.debug = debug


class InterruptionHandler:
    """
    Decides whether incoming user speech should stop the agent
    or be ignored as background acknowledgement.

    The idea is simple:

    - If the user says something meaningful → stop the agent
    - If the user only makes listening sounds while the agent talks → ignore it
    - If the agent is silent → treat all input normally
    """

    def __init__(self, settings=None):
        self.settings = settings or InterruptionSettings()
        self._build_filler_lookup()

    def _build_filler_lookup(self):
        """
        Store filler words in a normalized form so comparisons
        are fast and case-insensitive.
        """
        self._filler_set = {
            word.lower().strip()
            for word in self.settings.filler_words
        }

    def _tokenize(self, text: str) -> list[str]:
        """
        Break text into lowercase word tokens.
        Punctuation and spacing are ignored.
        """
        return re.findall(r"\b\w+\b", text.lower())

    def _contains_meaning(self, words: list[str]) -> bool:
        """
        Returns True if at least one word carries intent
        beyond simple acknowledgement.
        """
        for w in words:
            if w not in self._filler_set:
                return True
        return False

    def should_ignore_interrupt(self, text: str, is_speaking: bool) -> bool:
        """
        Decide whether this user input should be ignored
        while the agent is currently talking.

        Returns:
            True  → ignore input
            False → allow interruption or response
        """

        # Disabled handler → never interfere
        if not self.settings.enabled:
            return False

        # No usable text
        if not text:
            return False

        words = self._tokenize(text)

        if not words:
            return False

        # If the user said anything meaningful, we must interrupt
        if self._contains_meaning(words):
            if self.settings.debug:
                print("semantic input detected → interrupt")
            return False

        # Only filler sounds remain
        if is_speaking:
            if self.settings.debug:
                print("listener acknowledgement while speaking → ignore")
            return True

        # Agent silent → treat acknowledgement normally
        return False

    def explain_decision(self, text: str, is_speaking: bool) -> str:
        """
        Optional helper for debugging or logging.
        Explains *why* a decision was made.
        """

        words = self._tokenize(text)

        if not words:
            return "no_detectable_words"

        if self._contains_meaning(words):
            return "meaningful_speech_detected"

        if is_speaking:
            return "acknowledgement_during_agent_speech"

        return "acknowledgement_while_agent_idle"
