"""
Configuration for intelligent interruption handling.
Manages filler words, interrupt words, and system settings.
"""

import os
from dataclasses import dataclass, field
from typing import Set
import json


@dataclass
class InterruptionConfig:
    """Configuration for interruption handling logic."""
    
    # Words to ignore when agent is speaking (backchanneling)
    filler_words: Set[str] = field(default_factory=lambda: {
        # Assignment minimum (REQUIRED)
        'yeah', 'ok', 'hmm', 'right', 'uh-huh',
        
        # Common variations (RECOMMENDED)
        'okay', 'mhm', 'mm-hmm', 'uh', 'um',
        'yep', 'yup', 'sure', 'aha', 'got it',
    })
    
    # Words that always trigger interruption
    interrupt_words: Set[str] = field(default_factory=lambda: {
        # Assignment minimum (REQUIRED)
        'wait', 'stop', 'no',
        
        # Additional common interrupts (RECOMMENDED)
        'hold', 'pause', 'hold on', 'wait a second',
        'hang on', 'one moment',
    })
    
    # Whether to process partial transcripts (risky but faster)
    use_partial_transcripts: bool = True
    
    # Minimum confidence threshold for STT (if available)
    min_confidence: float = 0.5
    
    # Enable debug logging
    debug: bool = False
    
    def __post_init__(self):
        """Load from environment variables if available."""
        self._load_from_env()
        
        # Convert all words to lowercase for case-insensitive matching
        self.filler_words = {w.lower() for w in self.filler_words}
        self.interrupt_words = {w.lower() for w in self.interrupt_words}
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Load filler words from env
        if 'FILLER_WORDS' in os.environ:
            words = os.environ['FILLER_WORDS'].split(',')
            self.filler_words = {w.strip().lower() for w in words if w.strip()}
        
        # Load interrupt words from env
        if 'INTERRUPT_WORDS' in os.environ:
            words = os.environ['INTERRUPT_WORDS'].split(',')
            self.interrupt_words = {w.strip().lower() for w in words if w.strip()}
        
        # Load debug flag
        if 'INTERRUPTION_DEBUG' in os.environ:
            self.debug = os.environ['INTERRUPTION_DEBUG'].lower() == 'true'
        
        # Load partial transcript setting
        if 'USE_PARTIAL_TRANSCRIPTS' in os.environ:
            self.use_partial_transcripts = os.environ['USE_PARTIAL_TRANSCRIPTS'].lower() == 'true'
    
    @classmethod
    def from_json(cls, filepath: str) -> 'InterruptionConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls(
            filler_words=set(data.get('filler_words', [])),
            interrupt_words=set(data.get('interrupt_words', [])),
            use_partial_transcripts=data.get('use_partial_transcripts', False),
            min_confidence=data.get('min_confidence', 0.5),
            debug=data.get('debug', False)
        )
    
    def to_json(self, filepath: str):
        """Save configuration to JSON file."""
        data = {
            'filler_words': sorted(list(self.filler_words)),
            'interrupt_words': sorted(list(self.interrupt_words)),
            'use_partial_transcripts': self.use_partial_transcripts,
            'min_confidence': self.min_confidence,
            'debug': self.debug
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def __repr__(self):
        """String representation for debugging."""
        return (
            f"InterruptionConfig(\n"
            f"  filler_words={len(self.filler_words)} words,\n"
            f"  interrupt_words={len(self.interrupt_words)} words,\n"
            f"  use_partial_transcripts={self.use_partial_transcripts},\n"
            f"  debug={self.debug}\n"
            f")"
        )


# Default global configuration instance
default_config = InterruptionConfig()
