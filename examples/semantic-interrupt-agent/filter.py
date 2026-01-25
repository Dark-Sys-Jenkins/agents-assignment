import string
from config import get_ignore_words

class SemanticFilter:
    def __init__(self):
        self.ignore_words = get_ignore_words()

    def should_ignore_input(self, text: str) -> bool:
        if not text:
            return True

        # Normalize text: lowercase and remove punctuation
        clean_text = text.lower().translate(str.maketrans('', '', string.punctuation))
        words = clean_text.split()

        if not words:
            return True

        # Returns True ONLY if all words are in the ignore list
        return set(words).issubset(self.ignore_words)