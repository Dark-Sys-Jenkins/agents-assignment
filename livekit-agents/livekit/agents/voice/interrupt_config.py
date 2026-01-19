"""
Intelligent Interruption Configuration
Defines backchannel words to ignore when agent is speaking.
"""

# Words that should NOT interrupt when agent is speaking
BACKCHANNEL_WORDS = {
    'yeah', 'ok', 'okay', 'hmm', 'right', 'uh-huh',
    'aha', 'mhm', 'gotcha', 'understood', 'yep',
    'sure', 'alright', 'yup', 'uh', 'mhmm'
}

# Words that ALWAYS cause interruption
COMMAND_WORDS = {
    'wait', 'stop', 'no', 'hold', 'but',
    'however', 'actually', 'listen', 'hang'
}


def is_backchannel_only(text: str) -> bool:
    import sys
    """
    Check if text contains only backchannel words.
    
    Args:
        text: Transcribed user input (from STT)
        
    Returns:
        True if ONLY backchannel words, False otherwise
    """
    print(f"[DEBUG] is_backchannel_only called with: '{text}'", file=sys.stderr, flush=True)
    
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # Check for command words first - if ANY present, NOT backchannel
    for cmd in COMMAND_WORDS:
        if cmd in text_lower:
            return False
    
    # Remove punctuation and split into words
    words = text_lower.replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
    
    if len(words) == 0:
        return False
    
    # Check if ALL words are backchannel words
    result = all(word in BACKCHANNEL_WORDS for word in words)
    print(f"[DEBUG] Words: {words}, Is backchannel: {result}", file=sys.stderr, flush=True)
    return result
