"""
Example: Simple demonstration of the Intelligent Interruption Handler

This script simulates the core logic without requiring a full LiveKit setup.
Use this to understand how the handler works before integrating with LiveKit.
"""
import asyncio
from config.interruption_config import InterruptionConfig
from agent.state_manager import AgentStateManager
from agent.interruption_handler import IntelligentInterruptionHandler


async def simulate_scenario(
    handler: IntelligentInterruptionHandler,
    state_manager: AgentStateManager,
    scenario_name: str,
    is_speaking: bool,
    user_input: str
):
    """
    Simulate a single interaction scenario
    """
    print(f"\n{'='*60}")
    print(f"📋 Scenario: {scenario_name}")
    print(f"{'='*60}")
    print(f"Agent State: {'🗣️  SPEAKING' if is_speaking else '🔇 SILENT'}")
    print(f"User Says: \"{user_input}\"")
    
    # Set agent state
    if is_speaking:
        await state_manager.on_agent_speech_start()
    else:
        await state_manager.on_agent_speech_end()
    
    # Simulate VAD detection
    event_id = await handler.on_user_speech_detected()
    
    # Simulate small delay for STT
    await asyncio.sleep(0.1)
    
    # Get transcription and make decision
    should_interrupt = await handler.on_user_speech_transcribed(event_id, user_input)
    
    # Show result
    print(f"\n📊 Decision: {'⛔ INTERRUPT' if should_interrupt else '✅ IGNORE/CONTINUE'}")
    
    if should_interrupt:
        print("   → Agent will stop and process user input")
        await state_manager.force_stop_speaking()
    else:
        print("   → Agent continues speaking (backchannel ignored)")
    
    # Get detailed explanation
    explanation = handler.get_decision_explanation(user_input, is_speaking)
    print(f"\n💡 Reasoning:")
    for reason in explanation['reasons']:
        print(f"   • {reason}")
    
    # Reset state
    await state_manager.on_agent_speech_end()
    await asyncio.sleep(0.05)


async def main():
    """
    Run demonstration scenarios
    """
    print("\n" + "="*60)
    print("🎯 INTELLIGENT INTERRUPTION HANDLER DEMO")
    print("="*60)
    
    # Initialize components
    config = InterruptionConfig()
    state_manager = AgentStateManager()
    handler = IntelligentInterruptionHandler(state_manager, config)
    
    print(f"\n📚 Loaded Configuration:")
    print(f"   • {len(config.BACKCHANNEL_WORDS)} backchannel words")
    print(f"   • {len(config.COMMAND_WORDS)} command words")
    print(f"   • {config.STT_GRACE_PERIOD}s STT grace period")
    
    # Scenario 1: The Long Explanation (from assignment)
    await simulate_scenario(
        handler, state_manager,
        "The Long Explanation",
        is_speaking=True,
        user_input="yeah"
    )
    
    # Scenario 2: The Passive Affirmation (from assignment)
    await simulate_scenario(
        handler, state_manager,
        "The Passive Affirmation",
        is_speaking=False,
        user_input="yeah"
    )
    
    # Scenario 3: The Correction (from assignment)
    await simulate_scenario(
        handler, state_manager,
        "The Correction",
        is_speaking=True,
        user_input="no stop"
    )
    
    # Scenario 4: The Mixed Input (from assignment)
    await simulate_scenario(
        handler, state_manager,
        "The Mixed Input",
        is_speaking=True,
        user_input="yeah okay but wait"
    )
    
    # Additional scenarios
    await simulate_scenario(
        handler, state_manager,
        "Multiple Backchannels",
        is_speaking=True,
        user_input="ok hmm right"
    )
    
    await simulate_scenario(
        handler, state_manager,
        "Question While Speaking",
        is_speaking=True,
        user_input="what about the other option"
    )
    
    await simulate_scenario(
        handler, state_manager,
        "Polite Interruption",
        is_speaking=True,
        user_input="excuse me"
    )
    
    await simulate_scenario(
        handler, state_manager,
        "Short Answer When Silent",
        is_speaking=False,
        user_input="ok"
    )
    
    print(f"\n{'='*60}")
    print("✅ Demo Complete!")
    print(f"{'='*60}\n")
    
    # Show state info
    state_info = state_manager.get_state_info()
    print("📊 Final State:")
    for key, value in state_info.items():
        print(f"   • {key}: {value}")
    
    # Cleanup
    await handler.cleanup()


if __name__ == "__main__":
    print("\n🚀 Starting demonstration...\n")
    asyncio.run(main())
    print("\n👋 Demo finished. Check the output above to see how decisions are made.\n")
