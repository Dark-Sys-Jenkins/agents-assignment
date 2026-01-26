import re
from typing import List

_WORD_CLEAN_RE = re.compile(r"[^\w\s]+")


def _normalize_text(text: str) -> List[str]:
    """
    Lowercase, strip punctuation, and split into words.
    """
    if not text:
        return []
    cleaned = _WORD_CLEAN_RE.sub(" ", text.lower()).strip()
    return cleaned.split()

def can_ignore(transcript: str, ignore_list: list[str]) -> bool:
    """
    Determines if a transcript consists entirely of ignorable phrases.
    
    Args:
        transcript: The user's speech transcript
        ignore_list: List of phrases to ignore (e.g., ["yeah", "ok", "uh huh"])
    
    Returns:
        True if transcript contains only ignorable phrases, False otherwise
    """
    if not transcript:
        return True
    
    if not ignore_list:
        return False
    
    transcript_tokens = _normalize_text(transcript)
    
    if not transcript_tokens:
        return True
        
    normalized_phrases = []
    for phrase in ignore_list:
        tokens = _normalize_text(phrase)
        if tokens:
            normalized_phrases.append(tokens)

    normalized_phrases.sort(key=len, reverse=True)

    position = 0
    tokens_len = len(transcript_tokens)

    while position < tokens_len:
        for phrase_tokens in normalized_phrases:
            phrase_len = len(phrase_tokens)
            end = position + phrase_len

            if end <= tokens_len and transcript_tokens[position:end] == phrase_tokens:
                position = end
                break
        else:
            return False

    return True