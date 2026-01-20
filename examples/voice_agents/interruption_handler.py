import re
import logging

logger = logging.getLogger("interruption-handler")

class InterruptionFilter:
    def __init__(self, soft_words=None, hard_words=None):
        # Soft words - backchanneling that should be ignored
        if soft_words is None:
            self.soft_words = {
                'yeah', 'ok', 'okay', 'hmm', 'right', 'uh-huh', 'aha', 'mhmm', 'uh',
                'got it', 'sure', 'interesting', 'cool', 'yep', 'yup', 'acha', 
                'alright', 'alri', 'okey', 'ohh', 'is it', 'wow', 'nice', 'oh', 'yes'
            }
        else:
            self.soft_words = set(word.lower() for word in soft_words)
        
        # Hard words - interruption commands
        if hard_words is None:
            self.hard_words = {'wait', 'pause', 'stop', 'hold'}
        else:
            self.hard_words = set(word.lower() for word in hard_words)
        
        # Keep compatibility with old code
        self.ignore_words = self.soft_words

    def should_ignore(self, text, is_agent_speaking):
        """
        Logic for filtering interruptions:
        - If agent is silent, always return False (don't ignore anything).
        - If agent is speaking, check if the input is only "soft" words.
        - If input contains any hard word or unknown word, it's a hard interruption.
        """
        if not is_agent_speaking:
            return False

        clean_text = re.sub(r'[^\w\s]', '', text).lower().strip()
        words = clean_text.split()

        if not words:
            return True

        # Check if all words are soft words
        for word in words:
            if word not in self.soft_words:
                return False

        return True
