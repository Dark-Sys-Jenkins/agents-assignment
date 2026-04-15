from interrupt_handler.config import IGNORE_WORDS, INTERRUPT_WORDS
from interrupt_handler.utils import normalize_text, contains_interrupt, is_ignore_word


class InterruptionHandler:
    def __init__(self):
        self.is_agent_speaking = False

    def set_agent_state(self, speaking: bool):
        self.is_agent_speaking = speaking

    def handle_input(self, user_input: str) -> str:
        text = normalize_text(user_input)

        if self.is_agent_speaking:

            # Mixed input → interrupt
            if contains_interrupt(text, INTERRUPT_WORDS):
                return "INTERRUPT"

            # Only filler → ignore
            if is_ignore_word(text, IGNORE_WORDS):
                return "IGNORE"

            # Default → interrupt
            return "INTERRUPT"

        else:
            return "RESPOND"