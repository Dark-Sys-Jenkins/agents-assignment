import re
from typing import List

def should_ignore_interruption(text: str, ignore_words: List[str]) -> bool:
    """
    Determines if the interruption should be ignored based on the content of the text.
    
    Args:
        text: The transcribed text (interim or final).
        ignore_words: A list of words/phrases that should NOT trigger an interruption.
                      Example: ["yeah", "ok", "uh-huh"]
    
    Returns:
        True if the interruption should be IGNORED (agent continues speaking).
        False if the interruption should PROCEED (agent stops speaking).
    """
    if not text or not ignore_words:
        return False
    
    # Normalize text: lowercase and remove punctuation (EXCEPT hyphens for 'uh-huh')
    # [^\w\s\-] means "remove anything that is NOT a word char, whitespace, or hyphen"
    clean_text = re.sub(r'[^\w\s\-]', '', text.lower()).strip()
    
    if not clean_text:
        return True # Empty text (after cleaning) usually means noise or just punctuation

    
    words = clean_text.split()
    
    # Logic: If ALL words in the detected text are in the ignore list, we ignore the interruption.
    # If ANY word is NOT in the ignore list (e.g. "wait"), we must interrupt.
    
    # We do a word-by-word check. 
    # Note: This handles "Yeah ok" (both ignored) -> Ignore.
    # "Yeah wait" ("wait" not ignored) -> Interrupt.
    
    for word in words:
        if word not in ignore_words:
            return False # detected a word that is NOT ignored. Interrupt!
            
    return True # All words were in the ignore list.
