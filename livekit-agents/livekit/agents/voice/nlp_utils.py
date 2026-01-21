import re

def is_backchannel(transcript: str, ignore_list: list[str]) -> bool:
    """
    Determines if a transcript consists ENTIRELY of allowed backchannel phrases.
    """
    if not ignore_list:
        return False

    clean_text = re.sub(r'[^\w\s]', ' ', transcript.lower())
    words = clean_text.split()

    # If input is just noise/silence/empty, IGNORE it (return True)
    if not words:
        return True

    # Prepare Ignore Phrases
    normalized_phrases = []
    for phrase in ignore_list:
        p_clean = re.sub(r'[^\w\s]', ' ', phrase.lower())
        p_words = p_clean.split()
        if p_words:
            normalized_phrases.append(p_words)
    
    # Sort by length (descending) so we match "all right" before "right"
    normalized_phrases.sort(key=len, reverse=True)

    # Greedy Consumption Loop
    while words:
        matched = False
        for phrase_tokens in normalized_phrases:
            phrase_len = len(phrase_tokens)
            
            if words[:phrase_len] == phrase_tokens:
                words = words[phrase_len:]
                matched = True
                break
        
        if not matched:
            return False

    return True