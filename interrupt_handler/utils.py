def normalize_text(text: str) -> str:
    return text.lower().strip()


def contains_interrupt(text: str, interrupt_words: list) -> bool:
    for word in interrupt_words:
        if word in text:
            return True
    return False


def is_ignore_word(text: str, ignore_words: list) -> bool:
    return text in ignore_words