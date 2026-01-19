#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete end-to-end test of S2S agent with intelligent interruption handling
Demonstrates all scenarios working together
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from dual_layer_interrupt import (
    DualLayerInterruptHandler,
    InterruptConfig,
    AgentState,
    InterruptAction
)


class MockAgent:
    """Mock agent for testing without audio"""
    
    def __init__(self):
        self.interrupt_handler = DualLayerInterruptHandler(
            InterruptConfig(debug=True)
        )
        self.interrupt_handler.on_interrupt = self._on_interrupt
        self.interrupt_handler.on_decision = self._on_decision
        self.interrupt_count = 0
    
    async def _on_interrupt(self):
        self.interrupt_count += 1
        print("   ⚠️  INTERRUPT EXECUTED")
    
    async def _on_decision(self, action, reason):
        emoji = "✅" if action == InterruptAction.IGNORE else "⚠️ "
        print(f"   {emoji} Decision: {action.value} ({reason})")
    
    async def simulate_scenario(self, title, agent_state, user_input, expected_action):
        """Simulate a conversation scenario"""
        print(f"\n{'='*70}")
        print(f"📍 {title}")
        print(f"   Agent State: {agent_state.value}")
        print(f"   User says: '{user_input}'")
        print(f"   Expected: {expected_action.value}")
        print(f"{'='*70}")
        
        # Set agent state
        self.interrupt_handler.set_agent_state(agent_state)
        
        # Step 1: VAD triggers (simulated)
        print("\n   [1️⃣  VAD TRIGGER - Layer 1: State Check]")
        should_process = await self.interrupt_handler.on_vad_trigger()
        print(f"   → Process now? {should_process}")
        
        if agent_state in [AgentState.SPEAKING, AgentState.PLAYING]:
            print(f"   → Agent is {agent_state.value}, queueing for validation")
        else:
            print(f"   → Agent is silent, processing immediately")
        
        # Step 2: STT returns (simulated after 500ms)
        print("\n   [2️⃣  STT RESULT - Layer 2: Semantic Validation]")
        print(f"   → STT returned: '{user_input}'")
        
        # Get decision
        action = await self.interrupt_handler.on_stt_result(user_input)
        
        # Verify result
        print(f"\n   ✅ RESULT: {action.value}")
        if action == expected_action:
            print(f"   ✅ PASS - Got expected action: {expected_action.value}")
            return True
        else:
            print(f"   ❌ FAIL - Expected {expected_action.value}, got {action.value}")
            return False


async def main():
    print("\n" + "="*70)
    print("🎯 S2S AGENT WITH INTELLIGENT INTERRUPTS - END-TO-END TEST")
    print("="*70)
    
    agent = MockAgent()
    results = []
    
    # Scenario 1: Agent explaining, user says backchanneling
    print("\n\n" + "█"*70)
    print("SCENARIO 1: Agent Speaking + Bacchanneling")
    print("█"*70)
    
    result = await agent.simulate_scenario(
        "User says 'yeah' while agent is explaining something",
        AgentState.SPEAKING,
        "yeah",
        InterruptAction.IGNORE
    )
    results.append(("Scenario 1", result))
    
    # Scenario 2: Agent silent, user confirms with bacchanneling
    print("\n\n" + "█"*70)
    print("SCENARIO 2: Agent Silent + Bacchanneling")
    print("█"*70)
    
    result = await agent.simulate_scenario(
        "Agent finished speaking, user says 'yeah'",
        AgentState.SILENT,
        "yeah",
        InterruptAction.RESPOND
    )
    results.append(("Scenario 2", result))
    
    # Scenario 3: Agent speaking, user says stop command
    print("\n\n" + "█"*70)
    print("SCENARIO 3: Agent Speaking + Stop Command")
    print("█"*70)
    
    result = await agent.simulate_scenario(
        "Agent is rambling, user says 'stop'",
        AgentState.SPEAKING,
        "stop",
        InterruptAction.INTERRUPT
    )
    results.append(("Scenario 3", result))
    
    # Scenario 4: Agent speaking, user says mixed input
    print("\n\n" + "█"*70)
    print("SCENARIO 4: Agent Speaking + Mixed Input")
    print("█"*70)
    
    result = await agent.simulate_scenario(
        "User says 'yeah but wait' containing both backchannel and command",
        AgentState.SPEAKING,
        "yeah but wait",
        InterruptAction.INTERRUPT
    )
    results.append(("Scenario 4", result))
    
    # Scenario 5: Agent playing audio (TTS), user says interrupt
    print("\n\n" + "█"*70)
    print("SCENARIO 5: Agent Playing Audio + Interrupt")
    print("█"*70)
    
    result = await agent.simulate_scenario(
        "Agent playing TTS output, user says 'hold on'",
        AgentState.PLAYING,
        "hold on",
        InterruptAction.INTERRUPT
    )
    results.append(("Scenario 5", result))
    
    # Summary
    print("\n\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for scenario, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"  {status} - {scenario}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Intelligent interruption handling is working correctly.")
        print("\n📋 Key Features Verified:")
        print("   ✓ Bacchanneling ignored when agent speaking")
        print("   ✓ Bacchanneling processed when agent silent")
        print("   ✓ Force keywords trigger immediate interrupt")
        print("   ✓ Mixed input correctly identified")
        print("   ✓ All agent states handled properly")
        print("   ✓ No VAD kernel modification needed")
        print("   ✓ Logic-layer only solution")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
