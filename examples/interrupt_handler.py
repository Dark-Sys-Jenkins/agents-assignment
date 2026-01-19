#!/usr/bin/env python3
"""
LiveKit Intelligent Interruption Handling
Distinguishes between passive acknowledgement and active interruption
"""

import asyncio
from enum import Enum
from typing import Optional, List, Set
from dataclasses import dataclass
from datetime import datetime


class AgentState(Enum):
    """Agent state during conversation"""
    SILENT = "silent"  # Listening, not speaking
    SPEAKING = "speaking"  # Currently generating TTS
    PLAYING = "playing"  # Currently playing TTS audio


class InterruptAction(Enum):
    """Action to take on user input"""
    IGNORE = "ignore"  # Continue speaking (backchanneling)
    INTERRUPT = "interrupt"  # Stop and listen
    RESPOND = "respond"  # Process as normal input


@dataclass
class InterruptConfig:
    """Configuration for interrupt handling"""
    # Backchanneling words - ignored when agent is speaking
    ignore_list: List[str] = None
    # Commands that force interruption even during agent speech
    force_interrupt_keywords: List[str] = None
    # Wait time for STT confirmation before cutting off (milliseconds)
    sttt_confirmation_wait_ms: int = 500
    
    def __post_init__(self):
        if self.ignore_list is None:
            self.ignore_list = [
                'yeah', 'yep', 'yes', 'ok', 'okay', 'alright', 'all right',
                'hmm', 'hm', 'uh-huh', 'uh huh', 'mm-hmm', 'mm hmm',
                'right', 'sure', 'uh', 'um', 'like', 'you know',
                'i see', 'i understand', 'got it', 'gotcha',
                'cool', 'nice', 'good'
            ]
        
        if self.force_interrupt_keywords is None:
            self.force_interrupt_keywords = [
                'stop', 'wait', 'hold on', 'pause', 'no', 'nope', 'no no',
                'incorrect', 'wrong', 'halt', 'abort', 'cancel', 'quit',
                'never mind', 'nevermind', 'forget it'
            ]


class InterruptHandler:
    """
    Intelligent interruption handler for LiveKit agents.
    
    Handles the logic matrix:
    ┌──────────────┬──────────────┬────────────────────┐
    │ User Input   │ Agent State  │ Desired Behavior   │
    ├──────────────┼──────────────┼────────────────────┤
    │ "Yeah/Ok"    │ Speaking     │ IGNORE (continue)  │
    │ "Yeah/Ok"    │ Silent       │ RESPOND (process)  │
    │ "Stop/Wait"  │ Speaking     │ INTERRUPT (stop)   │
    │ "Stop/Wait"  │ Silent       │ RESPOND (process)  │
    └──────────────┴──────────────┴────────────────────┘
    """
    
    def __init__(self, config: InterruptConfig = None):
        self.config = config or InterruptConfig()
        self.agent_state = AgentState.SILENT
        self.last_interrupt_time = None
        self.pending_transcription = None
        
        # Normalize all words in config lists to lowercase
        self.ignore_list: Set[str] = set(w.lower() for w in self.config.ignore_list)
        self.force_keywords: Set[str] = set(w.lower() for w in self.config.force_interrupt_keywords)
        
        print(f"✅ InterruptHandler initialized")
        print(f"   Ignore List: {sorted(self.ignore_list)}")
        print(f"   Force Interrupt: {sorted(self.force_keywords)}")
    
    def set_agent_state(self, state: AgentState):
        """Update agent's current state"""
        if self.agent_state != state:
            print(f"🔄 Agent State: {self.agent_state.value} → {state.value}")
            self.agent_state = state
    
    def analyze_transcription(self, text: str) -> tuple[InterruptAction, str]:
        """
        Analyze transcribed text and decide whether to ignore, interrupt, or respond.
        
        Returns:
            (action, analysis_reason)
        """
        if not text or not text.strip():
            return InterruptAction.IGNORE, "Empty transcription"
        
        text_lower = text.lower().strip()
        
        # Step 1: Check for force-interrupt keywords (these always interrupt)
        for keyword in self.force_keywords:
            if keyword in text_lower:
                return InterruptAction.INTERRUPT, f"Force interrupt keyword detected: '{keyword}'"
        
        # Step 2: Check if it's a single-word backchannel
        words = text_lower.split()
        
        # Single word check
        if len(words) == 1 and words[0] in self.ignore_list:
            if self.agent_state in [AgentState.SPEAKING, AgentState.PLAYING]:
                return InterruptAction.IGNORE, f"Backchanneling ignored while speaking: '{text}'"
            else:
                return InterruptAction.RESPOND, f"Backchanneling response while silent: '{text}'"
        
        # Multi-word check: if all words are in ignore list
        if all(word in self.ignore_list for word in words):
            if self.agent_state in [AgentState.SPEAKING, AgentState.PLAYING]:
                return InterruptAction.IGNORE, f"Backchanneling ignored while speaking: '{text}'"
            else:
                return InterruptAction.RESPOND, f"Backchanneling response while silent: '{text}'"
        
        # Mixed content: contains both ignore-list and non-ignore words
        # This is treated as an actual interruption/command
        return InterruptAction.INTERRUPT, f"Mixed/command input detected: '{text}'"
    
    def should_interrupt(self, transcription: str) -> bool:
        """
        Determine if we should interrupt the agent.
        
        Args:
            transcription: STT output from user
            
        Returns:
            True if agent should stop, False if should continue
        """
        action, reason = self.analyze_transcription(transcription)
        
        print(f"📝 Transcription Analysis:")
        print(f"   Text: '{transcription}'")
        print(f"   Agent State: {self.agent_state.value}")
        print(f"   Action: {action.value}")
        print(f"   Reason: {reason}")
        
        return action == InterruptAction.INTERRUPT
    
    def get_action(self, transcription: str) -> InterruptAction:
        """Get the action to take based on transcription"""
        action, _ = self.analyze_transcription(transcription)
        return action
    
    # Configuration management
    def add_ignore_word(self, word: str):
        """Add a word to the ignore list"""
        self.ignore_list.add(word.lower())
        print(f"✅ Added '{word}' to ignore list")
    
    def add_force_keyword(self, word: str):
        """Add a word to force-interrupt list"""
        self.force_keywords.add(word.lower())
        print(f"✅ Added '{word}' to force-interrupt list")
    
    def remove_ignore_word(self, word: str):
        """Remove a word from ignore list"""
        self.ignore_list.discard(word.lower())
        print(f"✅ Removed '{word}' from ignore list")
    
    def print_config(self):
        """Print current configuration"""
        print("\n" + "="*60)
        print("INTERRUPT HANDLER CONFIGURATION")
        print("="*60)
        print(f"Ignore List ({len(self.ignore_list)} words):")
        print(f"  {sorted(self.ignore_list)}")
        print(f"\nForce Interrupt Keywords ({len(self.force_keywords)} words):")
        print(f"  {sorted(self.force_keywords)}")
        print(f"\nSTT Confirmation Wait: {self.config.sttt_confirmation_wait_ms}ms")
        print("="*60 + "\n")


# Test scenarios
async def test_interrupt_handler():
    """Test the interrupt handler with example scenarios"""
    
    handler = InterruptHandler()
    handler.print_config()
    
    test_cases = [
        # (transcription, agent_state, expected_action, scenario_name)
        ("yeah", AgentState.SPEAKING, InterruptAction.IGNORE, "Scenario 1: Backchannel while speaking"),
        ("yeah", AgentState.SILENT, InterruptAction.RESPOND, "Scenario 2: Backchannel while silent"),
        ("okay", AgentState.PLAYING, InterruptAction.IGNORE, "Scenario 3: 'Okay' while playing audio"),
        ("stop", AgentState.SPEAKING, InterruptAction.INTERRUPT, "Scenario 4: 'Stop' command interrupts"),
        ("wait", AgentState.SPEAKING, InterruptAction.INTERRUPT, "Scenario 5: 'Wait' command interrupts"),
        ("yeah but wait", AgentState.SPEAKING, InterruptAction.RESPOND, "Scenario 6: Mixed input - contains 'but wait'"),
        ("yeah okay alright", AgentState.SPEAKING, InterruptAction.IGNORE, "Scenario 7: Multiple backchannels"),
        ("no stop", AgentState.SPEAKING, InterruptAction.INTERRUPT, "Scenario 8: 'No stop' contains force keyword"),
        ("hmm", AgentState.SILENT, InterruptAction.RESPOND, "Scenario 9: 'Hmm' while silent"),
        ("uh-huh", AgentState.SPEAKING, InterruptAction.IGNORE, "Scenario 10: 'Uh-huh' while speaking"),
    ]
    
    print("\n" + "="*70)
    print("TEST SCENARIOS")
    print("="*70 + "\n")
    
    for transcription, state, expected, scenario_name in test_cases:
        print(f"🧪 {scenario_name}")
        print(f"   Input: '{transcription}' | State: {state.value}")
        
        handler.set_agent_state(state)
        action, reason = handler.analyze_transcription(transcription)
        
        status = "✅ PASS" if action == expected else "❌ FAIL"
        print(f"   Expected: {expected.value} | Got: {action.value}")
        print(f"   {status}")
        print()


if __name__ == "__main__":
    asyncio.run(test_interrupt_handler())
