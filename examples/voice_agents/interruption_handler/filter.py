import re
import logging

log = logging.getLogger("filler-detector")

class InterruptionFilter:
    def __init__(self, filler_words=None):
        # Your exact soft words list + common trailing fillers
        self.soft_words = {
            "yeah", "ok", "okay", "hmm", "uh-huh", "right", "aha", "mhm",
            "sure", "gotcha", "yep", "yup", "mhmm", "uh huh", "mm-hmm",
            "alright", "cool", "nice", "yes", "oh", "then", "and", "so"
        }
        
        # Your exact hard words list
        self.hard_words = {
            "stop", "wait", "pause", "no", "hold", "hold on",
            "wait a second", "wait a minute", "but wait", "hang on",
            "actually", "but", "however", "excuse me"
        }
        
        log.info(f"InterruptionFilter initialized: {len(self.soft_words)} soft words, {len(self.hard_words)} hard words")

    def should_ignore(self, text, is_agent_speaking):
        if not is_agent_speaking:
            return False

        cleaned = re.sub(r'[^\w\s]', '', text).lower().strip()
        if not cleaned:
            return True

        # Check for hard phrases first
        for hard_phrase in self.hard_words:
            if hard_phrase in cleaned:
                return False

        # Check if all tokens are soft words
        tokens = cleaned.split()
        for token in tokens:
            if token not in self.soft_words:
                return False

        return True
