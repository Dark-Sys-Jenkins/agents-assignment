# Intelligent Interruption Handler Configuration
# This file contains configurable word lists for the interruption handler

# Words to IGNORE when agent is speaking (backchanneling/acknowledgements)
# These indicate the user is listening but not trying to interrupt
IGNORE_WORDS = [
    # Common acknowledgements
    "yeah",
    "ok",
    "okay",
    "hmm",
    "mhm",
    "uh-huh",
    "mm-hmm",
    "right",
    "aha",
    "sure",
    "yep",
    "yup",
    "gotcha",
    "alright",
    
    # Thinking sounds
    "mmm",
    "uh",
    "um",
    "er",
    "ah",
    
    # Affirmative responses
    "yes",
    "nice",
    "cool",
    "great",
    "good",
    
    # You can add more language-specific words here
    # For example, for Spanish: "sí", "vale", "bueno"
    # For French: "oui", "d'accord", "bon"
]

# Words that should ALWAYS trigger interruption
# These indicate the user wants to stop or change direction
INTERRUPT_WORDS = [
    # Stop commands
    "wait",
    "stop",
    "no",
    "hold on",
    "hold up",
    "hang on",
    
    # Cancel commands
    "pause",
    "cancel",
    "never mind",
    "nevermind",
    
    # Correction commands
    "actually",
    "but",
    "however",
    "sorry",
    
    # Question indicators (often signal intent to speak)
    "question",
    "excuse me",
    
    # You can add more language-specific interrupt words here
]

# Whether word matching should be case-sensitive (usually False for natural speech)
CASE_SENSITIVE = False
