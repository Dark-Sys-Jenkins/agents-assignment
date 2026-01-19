#!/usr/bin/env python3
"""
LiveKit Intelligent Interruption Handling - Option 1: Dual-Layer Validation

Strategy:
  LAYER 1: STATE CHECK (Immediate on VAD trigger)
    - Is agent speaking? → Queue interrupt for validation
    - Is agent silent? → Process immediately
  
  LAYER 2: STT VALIDATION (Wait 400-600ms)
    - Get STT result
    - Check against ignore list
    - Discard if backchanneling, execute if command
    
This prevents stuttering/pausing by validating BEFORE interrupting.
"""

import asyncio
from enum import Enum
from typing import Optional, List, Set, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class AgentState(Enum):
    """Agent's current state"""
    SILENT = "silent"      # Listening, not speaking
    SPEAKING = "speaking"  # Generating TTS
    PLAYING = "playing"    # Playing audio


class InterruptAction(Enum):
    """Action to take on user input"""
    IGNORE = "ignore"        # Continue speaking
    INTERRUPT = "interrupt"  # Stop and listen
    RESPOND = "respond"      # Process as normal input


@dataclass
class PendingInterrupt:
    """Queued interrupt waiting for STT validation"""
    vad_timestamp: float
    audio_duration: float = 0.0
    stt_result: Optional[str] = None
    stt_timestamp: Optional[float] = None
    decision: Optional[InterruptAction] = None


@dataclass
class InterruptConfig:
    """Configuration for interrupt handling"""
    ignore_list: List[str] = field(default_factory=list)
    force_interrupt_keywords: List[str] = field(default_factory=list)
    stt_confirmation_wait_ms: int = 500  # Wait for STT before deciding
    debug: bool = False
    
    def __post_init__(self):
        if not self.ignore_list:
            self.ignore_list = [
                'yeah', 'yep', 'yes', 'ok', 'okay', 'alright', 'all right',
                'hmm', 'hm', 'uh-huh', 'uh huh', 'mm-hmm', 'mm hmm',
                'right', 'sure', 'uh', 'um', 'like', 'you know',
                'i see', 'i understand', 'got it', 'gotcha',
                'cool', 'nice', 'good'
            ]
        
        if not self.force_interrupt_keywords:
            self.force_interrupt_keywords = [
                'stop', 'wait', 'hold on', 'pause', 'no', 'nope', 'no no',
                'incorrect', 'wrong', 'halt', 'abort', 'cancel', 'quit',
                'never mind', 'nevermind', 'forget it'
            ]


class DualLayerInterruptHandler:
    """
    Intelligent interruption handler with dual-layer validation.
    
    Flow:
      1. VAD detects user speech (LAYER 1)
         → Check agent state
         → If speaking: Queue interrupt, wait for STT
         → If silent: Process immediately
      
      2. STT returns result (LAYER 2)
         → Analyze transcription
         → Decide: IGNORE/INTERRUPT/RESPOND
         → Execute decision
    
    Key: Agent NEVER pauses. It continues speaking while we validate.
    """
    
    def __init__(self, config: InterruptConfig = None):
        self.config = config or InterruptConfig()
        self.agent_state = AgentState.SILENT
        self.pending_interrupt: Optional[PendingInterrupt] = None
        self.validation_task: Optional[asyncio.Task] = None
        
        # Normalize word lists
        self.ignore_list: Set[str] = set(w.lower() for w in self.config.ignore_list)
        self.force_keywords: Set[str] = set(w.lower() for w in self.config.force_interrupt_keywords)
        
        # Callbacks for external actions
        self.on_interrupt: Optional[Callable[[], Awaitable[None]]] = None
        self.on_decision: Optional[Callable[[InterruptAction, str], Awaitable[None]]] = None
        
        self._debug_log("✅ DualLayerInterruptHandler initialized")
        self._debug_log(f"   Ignore List: {len(self.ignore_list)} words")
        self._debug_log(f"   Force Keywords: {len(self.force_keywords)} words")
        self._debug_log(f"   STT Wait: {self.config.stt_confirmation_wait_ms}ms")
    
    def _debug_log(self, msg: str):
        """Debug logging"""
        if self.config.debug:
            print(msg)
    
    # ========== STATE MANAGEMENT ==========
    
    def set_agent_state(self, state: AgentState):
        """Update agent's current state"""
        if self.agent_state != state:
            self._debug_log(f"🔄 Agent State: {self.agent_state.value} → {state.value}")
            self.agent_state = state
    
    # ========== LAYER 1: VAD TRIGGER ==========
    
    async def on_vad_trigger(self) -> bool:
        """
        Called immediately when VAD detects user speech.
        
        Returns:
            True if interrupt should proceed immediately (agent silent)
            False if interrupt is queued for validation (agent speaking)
        """
        self._debug_log("\n📡 VAD TRIGGER (Layer 1: State Check)")
        
        if self.agent_state in [AgentState.SPEAKING, AgentState.PLAYING]:
            self._debug_log(f"   Agent is {self.agent_state.value}")
            self._debug_log("   → Queuing interrupt for validation")
            
            # Create pending interrupt record
            self.pending_interrupt = PendingInterrupt(
                vad_timestamp=datetime.now().timestamp()
            )
            
            # Return False = don't interrupt immediately
            return False
        else:
            self._debug_log("   Agent is silent → Process immediately")
            # Return True = can process normally
            return True
    
    # ========== LAYER 2: STT VALIDATION ==========
    
    async def on_stt_result(self, transcription: str) -> InterruptAction:
        """
        Called when STT returns the user's speech.
        
        This is where we make the final decision about whether to interrupt.
        
        Args:
            transcription: User's transcribed speech
            
        Returns:
            Action to take: IGNORE/INTERRUPT/RESPOND
        """
        self._debug_log("\n📝 STT RESULT (Layer 2: Semantic Validation)")
        self._debug_log(f"   Transcription: '{transcription}'")
        self._debug_log(f"   Agent State: {self.agent_state.value}")
        self._debug_log(f"   Has Pending Interrupt: {self.pending_interrupt is not None}")
        
        action, reason = self._analyze_transcription(transcription)
        
        self._debug_log(f"   Decision: {action.value}")
        self._debug_log(f"   Reason: {reason}")
        
        # If we had a pending interrupt, this resolves it
        if self.pending_interrupt:
            self.pending_interrupt.stt_result = transcription
            self.pending_interrupt.stt_timestamp = datetime.now().timestamp()
            self.pending_interrupt.decision = action
            
            # Execute callback if provided
            if self.on_decision:
                await self.on_decision(action, reason)
            
            # If interrupt decision made, execute it now
            if action == InterruptAction.INTERRUPT:
                self._debug_log("   ⚠️  EXECUTING INTERRUPT NOW")
                if self.on_interrupt:
                    await self.on_interrupt()
            
            # Clear pending interrupt
            self.pending_interrupt = None
        
        return action
    
    # ========== DECISION LOGIC ==========
    
    def _analyze_transcription(self, text: str) -> tuple[InterruptAction, str]:
        """
        Analyze transcribed text and return action + reason.
        
        Decision Matrix:
        ┌─────────────────────┬──────────────┬────────────────────┐
        │ User Input          │ Agent State  │ Action             │
        ├─────────────────────┼──────────────┼────────────────────┤
        │ Pure backchannel    │ SPEAKING     │ IGNORE (continue)  │
        │ Pure backchannel    │ SILENT       │ RESPOND (process)  │
        │ Force interrupt     │ SPEAKING     │ INTERRUPT (stop)   │
        │ Mixed input         │ SPEAKING     │ INTERRUPT (stop)   │
        └─────────────────────┴──────────────┴────────────────────┘
        """
        if not text or not text.strip():
            return InterruptAction.IGNORE, "Empty transcription"
        
        text_lower = text.lower().strip()
        
        # Step 1: Check for FORCE INTERRUPT keywords (highest priority)
        for keyword in self.force_keywords:
            if keyword in text_lower:
                return InterruptAction.INTERRUPT, f"Force interrupt keyword: '{keyword}'"
        
        # Step 2: Analyze word-by-word
        words = [w for w in text_lower.split() if w.strip()]
        
        # Check if all words are backchanneling
        if words and all(word in self.ignore_list for word in words):
            # Pure bacchanneling - but behavior depends on agent state
            if self.agent_state in [AgentState.SPEAKING, AgentState.PLAYING]:
                return InterruptAction.IGNORE, "Pure backchannel while agent speaking"
            else:
                return InterruptAction.RESPOND, "Pure backchannel while agent silent"
        
        # Mixed content: contains non-backchanneling words
        # This is an actual statement/command that should interrupt
        return InterruptAction.INTERRUPT, f"Mixed/command input: '{text}'"
    
    # ========== CONFIGURATION ==========
    
    def add_ignore_word(self, word: str):
        """Add word to backchannel ignore list"""
        self.ignore_list.add(word.lower())
        self._debug_log(f"✅ Added '{word}' to ignore list")
    
    def add_force_keyword(self, word: str):
        """Add word to force-interrupt keywords"""
        self.force_keywords.add(word.lower())
        self._debug_log(f"✅ Added '{word}' to force-interrupt list")
    
    def print_status(self):
        """Print current handler status"""
        print("\n" + "="*70)
        print("DUAL-LAYER INTERRUPT HANDLER STATUS")
        print("="*70)
        print(f"Agent State: {self.agent_state.value}")
        print(f"Pending Interrupt: {self.pending_interrupt is not None}")
        if self.pending_interrupt:
            elapsed = datetime.now().timestamp() - self.pending_interrupt.vad_timestamp
            print(f"  - Waiting for {elapsed:.2f}s")
            print(f"  - STT Result: {self.pending_interrupt.stt_result}")
        print(f"\nIgnore List: {sorted(self.ignore_list)}")
        print(f"Force Keywords: {sorted(self.force_keywords)}")
        print("="*70 + "\n")


# ============= INTEGRATION EXAMPLE =============

async def test_dual_layer_flow():
    """Test the dual-layer validation flow"""
    
    config = InterruptConfig(debug=True)
    handler = DualLayerInterruptHandler(config)
    
    # Setup callbacks
    async def on_interrupt():
        print("   🛑 [CALLBACK] Executing interrupt - stopping agent!")
    
    async def on_decision(action, reason):
        print(f"   📊 [CALLBACK] Decision made: {action.value} ({reason})")
    
    handler.on_interrupt = on_interrupt
    handler.on_decision = on_decision
    
    print("\n" + "="*70)
    print("TEST: Scenario 1 - Agent speaking, user says 'yeah'")
    print("="*70)
    
    # Agent starts speaking
    handler.set_agent_state(AgentState.SPEAKING)
    print("✓ Agent starts speaking...")
    
    # User says something - VAD triggers immediately
    print("\n📡 User speaks - VAD detects...")
    should_interrupt_now = await handler.on_vad_trigger()
    print(f"   Should interrupt immediately? {should_interrupt_now}")
    
    # Simulate STT delay (400-500ms)
    await asyncio.sleep(0.1)
    
    # STT comes back with "yeah"
    print("\n✓ STT returns: 'yeah'")
    action = await handler.on_stt_result("yeah")
    print(f"✓ Final action: {action.value}")
    
    assert action == InterruptAction.IGNORE, "Should IGNORE when agent speaking"
    print("✅ TEST PASSED: Agent continues speaking over 'yeah'\n")
    
    # ===== Test 2 =====
    print("="*70)
    print("TEST: Scenario 2 - Agent speaking, user says 'stop'")
    print("="*70)
    
    handler.set_agent_state(AgentState.SPEAKING)
    print("✓ Agent starts speaking...")
    
    print("\n📡 User speaks - VAD detects...")
    should_interrupt_now = await handler.on_vad_trigger()
    print(f"   Should interrupt immediately? {should_interrupt_now}")
    
    await asyncio.sleep(0.1)
    
    print("\n✓ STT returns: 'stop'")
    action = await handler.on_stt_result("stop")
    print(f"✓ Final action: {action.value}")
    
    assert action == InterruptAction.INTERRUPT, "Should INTERRUPT on 'stop'"
    print("✅ TEST PASSED: Agent stops on 'stop' command\n")
    
    # ===== Test 3 =====
    print("="*70)
    print("TEST: Scenario 3 - Agent silent, user says 'yeah'")
    print("="*70)
    
    handler.set_agent_state(AgentState.SILENT)
    print("✓ Agent is now silent...")
    
    print("\n📡 User speaks - VAD detects...")
    should_interrupt_now = await handler.on_vad_trigger()
    print(f"   Should interrupt immediately? {should_interrupt_now}")
    
    if should_interrupt_now:
        # When agent is silent, we process immediately
        print("\n✓ STT returns: 'yeah'")
        action = await handler.on_stt_result("yeah")
        print(f"✓ Final action: {action.value}")
        
        assert action == InterruptAction.RESPOND, "Should RESPOND when agent silent"
        print("✅ TEST PASSED: Agent responds to 'yeah' when silent\n")
    
    # ===== Test 4 =====
    print("="*70)
    print("TEST: Scenario 4 - Agent speaking, mixed input 'yeah but wait'")
    print("="*70)
    
    handler.set_agent_state(AgentState.SPEAKING)
    print("✓ Agent starts speaking...")
    
    print("\n📡 User speaks - VAD detects...")
    should_interrupt_now = await handler.on_vad_trigger()
    
    await asyncio.sleep(0.1)
    
    print("\n✓ STT returns: 'yeah but wait'")
    action = await handler.on_stt_result("yeah but wait")
    print(f"✓ Final action: {action.value}")
    
    assert action == InterruptAction.INTERRUPT, "Should INTERRUPT on mixed input with 'wait'"
    print("✅ TEST PASSED: Mixed input containing 'wait' interrupts\n")
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED ✅")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_dual_layer_flow())
