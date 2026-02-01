IGNORE_WORDS={
    "yeah", "ok", "okay", "hmm", "uh-huh", "right", "yes", "yep"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "cancel", "hold", "hold on"
}

def _normalize(text: str) -> list[str]:
    return text.lower().strip().replace("-", " ").split()


def is_filler_only(text: str) -> bool:
    tokens = _normalize(text)
    if not tokens:
        return False
    return all(tok in IGNORE_WORDS for tok in tokens)


def is_real_interruption(text: str) -> bool:
    tokens = _normalize(text)
    return any(tok in INTERRUPT_WORDS for tok in tokens)