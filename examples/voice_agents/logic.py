import logging
import re

logger = logging.getLogger("interruption-logic")

class InterruptionHandler:
    def __init__(self, ignore_words: list[str] = None, interrupt_commands: list[str] = None):
        raw_ignore_list = ignore_words or [
            "yeah", "ok", "okay", "hmm", "mhm", "uh-huh", "right", "aha", "m-hm", "got it", "i see",
            "sure", "yup", "yep", "uh", "um", "er", "ah", "cool", "fine", "correct"
        ]
        
        # Explicit commands that SHOULD interrupt
        self.interrupt_commands = set(interrupt_commands or [
            "stop", "wait", "hold", "no stop", "shh", "quiet", "pause"
        ])

        # Pre-process the ignore list to match the cleaning logic
        self.ignore_words = set()
        for item in raw_ignore_list:
            cleaned_item = self._clean_text(item)
            self.ignore_words.add(cleaned_item)
            # Add individual parts if it was a phrase (e.g., "got it" -> "got", "it")
            for part in cleaned_item.split():
                 self.ignore_words.add(part)

    def should_interrupt(self, transcript: str) -> bool:
        """Determines if the transcript should stop the agent."""
        if not transcript:
            return False

        clean_text = self._clean_text(transcript)
        words = clean_text.split()
        
        if not words:
            return False

       
        for cmd in self.interrupt_commands:
            if cmd in clean_text:
                logger.info(f"Interrupting: Explicit command '{cmd}' found.")
                return True

       
        non_ignored_words = [w for w in words if w not in self.ignore_words]
        
        if len(non_ignored_words) == 0:
            logger.info(f"Ignoring: Only filler words detected ('{transcript}')")
            return False

        # Noise Filter: Prevent random stopping on short non-ignore words
        # Requires at least 2 meaningful words OR 1 long word (>5 chars)
        if len(non_ignored_words) < 2 and len(non_ignored_words[0]) < 5:
             logger.info(f"Ignoring: Noise/short word '{non_ignored_words[0]}' detected.")
             return False

        logger.info(f"Interrupting: Semantic content detected ('{transcript}')")
        return True

    def _clean_text(self, text: str) -> str:
        """Removes punctuation and converts to lowercase."""
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower().strip()
