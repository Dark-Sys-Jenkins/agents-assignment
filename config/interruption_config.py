"""
Configuration for intelligent interruption handling
"""

class InterruptionConfig:
    """
    Configuration class for managing interruption behavior.
    Easily customizable through environment variables or direct modification.
    """
    
    # Words to ignore when agent is speaking (backchannel acknowledgments)
    BACKCHANNEL_WORDS = [
        'yeah', 'yes', 'yep', 'yup',
        'ok', 'okay', 'k',
        'hmm', 'hm', 'mhm', 'mm', 'mmm',
        'uh-huh', 'uh huh', 'uhhuh',
        'right', 'sure',
        'got it', 'gotcha', 'i see',
        'alright', 'cool',
        'aha', 'ah', 'oh',
    ]
    
    # Words that always trigger interruption
    COMMAND_WORDS = [
        'stop', 'wait', 'hold', 'pause',
        'no', 'nope', 'nah',
        'but', 'however', 'actually',
        'excuse me', 'sorry',
        'question', 'wait a second', 'wait a minute',
        'hold on', 'hang on', 'one second',
    ]
    
    # Timing parameters (in seconds)
    STT_GRACE_PERIOD = 0.5  # Wait for STT transcription before deciding
    INTERRUPTION_COOLDOWN = 0.3  # Prevent duplicate interruption events
    
    # Threshold for "mixed input" detection
    MIN_WORD_COUNT_FOR_INTENT = 2  # "yeah wait" has 2 words, likely has intent
    
    @classmethod
    def is_backchannel_only(cls, text: str) -> bool:
        """
        Check if text contains ONLY backchannel words.
        
        Args:
            text: User's transcribed speech
            
        Returns:
            True if all words are backchannel, False otherwise
        """
        if not text or not text.strip():
            return False
        
        # Normalize and split into words
        words = text.lower().strip().split()
        
        # Check if all words are in backchannel list
        return all(word in cls.BACKCHANNEL_WORDS for word in words)
    
    @classmethod
    def contains_command(cls, text: str) -> bool:
        """
        Check if text contains any command words.
        
        Args:
            text: User's transcribed speech
            
        Returns:
            True if text contains command words, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for any command word or phrase
        return any(cmd in text_lower for cmd in cls.COMMAND_WORDS)
    
    @classmethod
    def should_interrupt(cls, text: str, is_agent_speaking: bool) -> bool:
        """
        Main decision logic for whether to interrupt the agent.
        
        This implements the core logic matrix:
        - Backchannel + Speaking = Ignore (False)
        - Command + Speaking = Interrupt (True)
        - Any input + Silent = Process (True)
        - Mixed input + Speaking = Interrupt (True)
        
        Args:
            text: User's transcribed speech
            is_agent_speaking: Whether agent is currently generating/playing audio
            
        Returns:
            True if agent should be interrupted, False if input should be ignored
        """
        # Empty text = no interruption
        if not text or not text.strip():
            return False
        
        # If agent is NOT speaking, always process input
        # (User is responding to silence or asking a question)
        if not is_agent_speaking:
            return True
        
        # Agent IS speaking - now we need to determine intent
        
        # Priority 1: Check for command words - always interrupt
        if cls.contains_command(text):
            return True
        
        # Priority 2: Check if it's pure backchannel - ignore
        if cls.is_backchannel_only(text):
            return False
        
        # Priority 3: Mixed or unclear input
        # If user says multiple words and it's not pure backchannel,
        # they're probably trying to say something meaningful
        word_count = len(text.strip().split())
        if word_count >= cls.MIN_WORD_COUNT_FOR_INTENT:
            return True
        
        # Single non-backchannel word while agent is speaking
        # Err on the side of interruption (user might be trying to speak)
        return True
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """
        Get a summary of current configuration.
        Useful for debugging and logging.
        
        Returns:
            Dictionary with current config values
        """
        return {
            "backchannel_words": cls.BACKCHANNEL_WORDS,
            "command_words": cls.COMMAND_WORDS,
            "stt_grace_period": cls.STT_GRACE_PERIOD,
            "interruption_cooldown": cls.INTERRUPTION_COOLDOWN,
            "min_word_count": cls.MIN_WORD_COUNT_FOR_INTENT,
        }
