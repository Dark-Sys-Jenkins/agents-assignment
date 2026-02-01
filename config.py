"""
Configuration file for Intelligent Interruption Handler

Modify this file to customize the behavior of the interruption handler.
"""

# ========== IGNORE WORDS CONFIGURATION ==========
# These words will be IGNORED when the agent is speaking
# (user can say these while agent talks, agent will continue)
IGNORE_WORDS = {
    # Primary backchanneling words
    'yeah',
    'ok',
    'okay',
    'hmm',
    'mhmm',
    'uh-huh',
    'mm-hmm',
    
    # Acknowledgment words
    'right',
    'sure',
    'alright',
    'got it',
    'i see',
    
    # Fillers (common in natural speech)
    'uh',
    'um',
    'ah',
    'er',
    
    # Affirmative variations
    'yep',
    'yup',
    'yes' # Note: might want to remove if "yes" should interrupt
}

# ========== INTERRUPT WORDS CONFIGURATION ==========
# These words will ALWAYS cause the agent to stop speaking immediately
INTERRUPT_WORDS = {
    # Direct commands
    'wait',
    'stop',
    'pause',
    'hold',
    'hold on',
    'hang on',
    
    # Negatives
    'no',
    'nope',
    'nah',
    
    # Attention getters
    'excuse me',
    'sorry',
    'actually',
    
    # Corrections
    'but',
    'however',
    'although',
}

# ========== CONFIDENCE THRESHOLD ==========
# Minimum confidence score for STT transcriptions
# Lower = more responsive but may process uncertain transcriptions
# Higher = more accurate but may miss some inputs
CONFIDENCE_THRESHOLD = 0.6

# ========== LOGGING CONFIGURATION ==========
# Logging level for the interruption handler
# Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_LEVEL = 'INFO'

# ========== ADVANCED SETTINGS ==========

# Should we consider phrase context?
# If True, "yeah but wait" will interrupt (because of "but wait")
# If False, any ignore word makes the entire phrase ignored
CONTEXT_AWARE = True

# Minimum word count for processing
# Helps filter out very short utterances that might be noise
MIN_WORD_COUNT = 1

# Case sensitive matching?
# Usually should be False for better UX
CASE_SENSITIVE = False

# ========== LANGUAGE-SPECIFIC CONFIGURATIONS ==========
# Add language-specific ignore/interrupt words here

# Example: Spanish
IGNORE_WORDS_ES = {
    'sí', 'vale', 'bueno', 'claro', 'hmm'
}

INTERRUPT_WORDS_ES = {
    'espera', 'para', 'no', 'momento'
}

# Example: French  
IGNORE_WORDS_FR = {
    'oui', 'd\'accord', 'hmm', 'bon'
}

INTERRUPT_WORDS_FR = {
    'attends', 'arrête', 'non', 'stop'
}

# ========== MODEL SELECTION ==========
# You can customize which models to use

# Speech-to-Text model
STT_MODEL = "nova-3"  # Deepgram model
# Options: "nova-2", "nova-3", "nova-2-general", "nova-2-meeting"

# Text-to-Speech voice
TTS_VOICE = "alloy"  # OpenAI voice
# Options: "alloy", "echo", "fable", "onyx", "nova", "shimmer"

# Language Model
LLM_MODEL = "gpt-4o-mini"
# Options: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"

# Voice Activity Detection
VAD_MODEL = "silero"
# Options: "silero"

# ========== CUSTOM FUNCTIONS ==========

def should_ignore_custom(text: str, agent_speaking: bool) -> bool:
    """
    Custom logic for determining if text should be ignored.
    
    This function is called BEFORE the standard ignore/interrupt logic.
    Return True to force ignore, False to use standard logic, None to skip.
    
    Args:
        text: The transcribed text
        agent_speaking: Whether the agent is currently speaking
        
    Returns:
        True to ignore, False to use standard logic
    """
    # Example: Always ignore single-letter utterances
    if len(text.strip()) == 1:
        return True
    
    # Example: Ignore repeated words
    words = text.lower().split()
    if len(words) > 1 and len(set(words)) == 1:
        return True  # e.g., "yeah yeah yeah"
    
    # Use standard logic
    return False


def should_interrupt_custom(text: str, agent_speaking: bool) -> bool:
    """
    Custom logic for determining if text should interrupt.
    
    This function is called BEFORE the standard interrupt logic.
    Return True to force interrupt, False to use standard logic.
    
    Args:
        text: The transcribed text
        agent_speaking: Whether the agent is currently speaking
        
    Returns:
        True to interrupt, False to use standard logic
    """
    # Example: Long utterances should always interrupt
    if len(text.split()) > 5 and agent_speaking:
        return True
    
    # Use standard logic
    return False


# ========== ENVIRONMENT VARIABLE OVERRIDES ==========
# These can be overridden via environment variables

import os

# Override ignore words from env
if os.getenv('CUSTOM_IGNORE_WORDS'):
    IGNORE_WORDS = set(os.getenv('CUSTOM_IGNORE_WORDS').split(','))

# Override interrupt words from env
if os.getenv('CUSTOM_INTERRUPT_WORDS'):
    INTERRUPT_WORDS = set(os.getenv('CUSTOM_INTERRUPT_WORDS').split(','))

# Override confidence threshold from env
if os.getenv('CONFIDENCE_THRESHOLD'):
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD'))

# Override log level from env
if os.getenv('LOG_LEVEL'):
    LOG_LEVEL = os.getenv('LOG_LEVEL')


# ========== EXPORT CONFIGURATION ==========

def get_config():
    """
    Get the current configuration as a dictionary.
    Use this in your agent implementation.
    """
    return {
        'ignore_words': IGNORE_WORDS,
        'interrupt_words': INTERRUPT_WORDS,
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'log_level': LOG_LEVEL,
        'context_aware': CONTEXT_AWARE,
        'min_word_count': MIN_WORD_COUNT,
        'case_sensitive': CASE_SENSITIVE,
        'stt_model': STT_MODEL,
        'tts_voice': TTS_VOICE,
        'llm_model': LLM_MODEL,
        'vad_model': VAD_MODEL,
    }


if __name__ == '__main__':
    # Print current configuration
    import json
    config = get_config()
    print("Current Configuration:")
    print(json.dumps({k: list(v) if isinstance(v, set) else v for k, v in config.items()}, indent=2))