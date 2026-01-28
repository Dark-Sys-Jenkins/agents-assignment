import logging

logger = logging.getLogger("interrupt-handler")

IGNORE_WORDS = {'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 'aha', 'mhm', 'uh', 'um', 'yep', 'yup'}
COMMAND_WORDS = {'stop', 'wait', 'no', 'pause', 'hold', 'halt', 'but'}


class InterruptionHandler:
    def __init__(self):
        self.is_speaking = False
    
    def should_ignore(self, transcript: str) -> bool:
        """Returns True if input should be ignored (agent continues speaking)"""
        words = set(transcript.lower().split())
        
        # If agent not speaking, never ignore
        if not self.is_speaking:
            return False
        
        # Check for command words
        has_command = bool(words & COMMAND_WORDS)
        
        # Check if only ignore words
        only_ignore = words and words.issubset(IGNORE_WORDS)
        
        # Ignore only if agent is speaking AND only ignore words AND no commands
        should_ignore = only_ignore and not has_command
        
        if should_ignore:
            logger.info(f"IGNORING backchannel: '{transcript}'")
        else:
            logger.info(f"ALLOWING interruption: '{transcript}'")
        
        return should_ignore
    
    def on_agent_start_speaking(self):
        self.is_speaking = True
    
    def on_agent_stop_speaking(self):
        self.is_speaking = False
