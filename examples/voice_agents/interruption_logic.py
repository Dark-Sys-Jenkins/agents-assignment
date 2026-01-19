
# 1. Configurable Ignore List
IGNORE_WORDS = {
    # Variations of Yeah/Yes
    'yeah', 'yeh', 'yah', 'yea', 'ya', 'yes', 'yep', 'yup', 'ye',
    # Variations of Okay
    'ok', 'okay', 'kay', 'k', 'okey', 'oke', 'kk',
    # Soft noises / fillers
    'hmm', 'hmmm', 'mm', 'mhm', 'mhmm', 'um', 'uh', 'er', 'ah', 'oh', 'ooh',
    'uh-huh', 'uhhuh', 'aha', 
    # Agreements
    'right', 'rite', 'alright', 'alrite', 'correct', 'true', 'sure', 'fine',
    # Positive feedback (short)
    'cool', 'great', 'nice', 'sweet', 'awesome', 'wow', 'really',
    'gotcha', 'absolutely', 'exactly', 'understood'
}

def clean_text(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()

def is_backchannel(text: str) -> bool:
    cleaned = clean_text(text)
    if not cleaned:
        return False
    words = cleaned.split()
    # If all words are in ignore list, treat as backchannel
    return all(w in IGNORE_WORDS for w in words)
