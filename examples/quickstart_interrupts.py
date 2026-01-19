#!/usr/bin/env python3
"""
QUICK START: S2S Agent with Intelligent Interrupts
Copy this script and modify for your needs
"""

import asyncio
import os
from dotenv import load_dotenv
from dual_layer_interrupt import (
    DualLayerInterruptHandler,
    InterruptConfig,
    AgentState,
    InterruptAction
)

load_dotenv()

# Example 1: Basic initialization
print("="*60)
print("EXAMPLE 1: Initialize Interrupt Handler")
print("="*60)

handler = DualLayerInterruptHandler(InterruptConfig())
print(f"✅ Handler ready")
print(f"   - 26 backchannel ignore words")
print(f"   - 16 force interrupt keywords")
print(f"   - 500ms STT wait window")


# Example 2: Using with agent states
print("\n" + "="*60)
print("EXAMPLE 2: Track Agent States")
print("="*60)

async def track_states():
    handler.set_agent_state(AgentState.SILENT)
    print(f"Agent State: {handler.agent_state.value}")
    
    handler.set_agent_state(AgentState.SPEAKING)
    print(f"Agent State: {handler.agent_state.value}")
    
    handler.set_agent_state(AgentState.PLAYING)
    print(f"Agent State: {handler.agent_state.value}")

asyncio.run(track_states())


# Example 3: Handling VAD + STT
print("\n" + "="*60)
print("EXAMPLE 3: Dual-Layer Decision Making")
print("="*60)

async def simulate_interruption():
    handler = DualLayerInterruptHandler(InterruptConfig())
    
    # Setup callbacks
    async def on_interrupt():
        print("   ⚠️  INTERRUPT EXECUTED")
    
    async def on_decision(action, reason):
        print(f"   Decision: {action.value} - {reason}")
    
    handler.on_interrupt = on_interrupt
    handler.on_decision = on_decision
    
    # Scenario: Agent speaking, user says "stop"
    print("\n🎙️  Scenario: Agent speaking, user says 'stop'")
    
    handler.set_agent_state(AgentState.SPEAKING)
    print("Step 1️⃣  (VAD triggers) Set agent state to SPEAKING")
    
    # Layer 1: VAD trigger
    should_process = await handler.on_vad_trigger()
    print(f"Step 2️⃣  (Layer 1) Should process now? {should_process}")
    print(f"         → Since agent speaking, queuing for validation")
    
    # Simulate STT delay
    await asyncio.sleep(0.1)
    print(f"Step 3️⃣  (STT returns) Got transcription: 'stop'")
    
    # Layer 2: STT validation
    action = await handler.on_stt_result("stop")
    print(f"Step 4️⃣  (Layer 2) Final action: {action.value}")

asyncio.run(simulate_interruption())


# Example 4: Customizing word lists
print("\n" + "="*60)
print("EXAMPLE 4: Custom Word Lists")
print("="*60)

custom_config = InterruptConfig(
    ignore_list=[
        # Your custom bacchanneling words
        'yeah', 'yep', 'ok', 'understood', 'go on',
        'mm-hmm', 'sure', 'gotcha', 'absolutely'
    ],
    force_interrupt_keywords=[
        # Your custom interrupt keywords
        'stop', 'wait', 'pause', 'hold on',
        'cancel', 'no', 'quiet'
    ],
    stt_confirmation_wait_ms=600,  # Wait 600ms for STT
    debug=False       # Disable verbose logging
)

custom_handler = DualLayerInterruptHandler(custom_config)
print(f"✅ Custom handler configured")
print(f"   Ignore words: {len(custom_config.ignore_list)}")
print(f"   Force keywords: {len(custom_config.force_interrupt_keywords)}")
print(f"   STT wait: {custom_config.stt_confirmation_wait_ms}ms")


# Example 5: Integration pattern
print("\n" + "="*60)
print("EXAMPLE 5: Integration Pattern")
print("="*60)

print("""
# In your agent class:

class MyVoiceAgent:
    def __init__(self):
        self.handler = DualLayerInterruptHandler(InterruptConfig())
        self.handler.on_interrupt = self._handle_interrupt
    
    async def _handle_interrupt(self):
        # Stop TTS playback
        # Stop LLM generation
        # Clear output buffer
        pass
    
    async def on_vad_trigger(self):
        '''Called when user starts speaking'''
        should_process = await self.handler.on_vad_trigger()
        if not should_process:
            # Waiting for STT validation
            return
        # Process immediately (agent was silent)
    
    async def on_transcription(self, text):
        '''Called when STT returns transcription'''
        action = await self.handler.on_stt_result(text)
        
        if action == InterruptAction.IGNORE:
            # Agent continues speaking
            pass
        elif action == InterruptAction.INTERRUPT:
            # Stop agent, process interrupt
            await self._stop_playback()
        elif action == InterruptAction.RESPOND:
            # Process as normal user input
            await self._generate_response(text)
    
    async def generate_response(self, user_input):
        '''Simulate generating response'''
        self.handler.set_agent_state(AgentState.SPEAKING)
        # ... call LLM ...
        self.handler.set_agent_state(AgentState.PLAYING)
        # ... play audio ...
        self.handler.set_agent_state(AgentState.SILENT)
""")


# Example 6: Testing your configuration
print("\n" + "="*60)
print("EXAMPLE 6: Test Your Configuration")
print("="*60)

async def test_config():
    handler = DualLayerInterruptHandler(InterruptConfig())
    
    test_cases = [
        (AgentState.SPEAKING, "yeah", InterruptAction.IGNORE),
        (AgentState.SPEAKING, "stop", InterruptAction.INTERRUPT),
        (AgentState.SILENT, "yeah", InterruptAction.RESPOND),
        (AgentState.SPEAKING, "yeah but wait", InterruptAction.INTERRUPT),
    ]
    
    for agent_state, text, expected in test_cases:
        handler.set_agent_state(agent_state)
        await handler.on_vad_trigger()
        
        action = await handler.on_stt_result(text)
        
        status = "✅" if action == expected else "❌"
        print(f"{status} {agent_state.value:8} + '{text:20}' = {action.value}")

asyncio.run(test_config())


print("\n" + "="*60)
print("✅ QUICK START COMPLETE")
print("="*60)
print("\nNext steps:")
print("1. Run: python examples/test_s2s_interrupts.py")
print("2. Read: examples/README_INTERRUPTS.md")
print("3. Try: python examples/s2s_with_smart_interrupts.py")
print("="*60 + "\n")
