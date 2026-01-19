"""
Test cases for Intelligent Interruption Handler
"""
import asyncio
import pytest
from config.interruption_config import InterruptionConfig
from agent.state_manager import AgentStateManager
from agent.interruption_handler import IntelligentInterruptionHandler


@pytest.fixture
def setup():
    """Setup test environment"""
    config = InterruptionConfig()
    state_manager = AgentStateManager()
    handler = IntelligentInterruptionHandler(state_manager, config)
    return config, state_manager, handler


@pytest.mark.asyncio
async def test_backchannel_during_speech(setup):
    """
    Test Case 1: Backchannel During Speech
    Context: Agent is speaking
    User says: "yeah"
    Expected: Agent continues speaking (does NOT interrupt)
    """
    config, state_manager, handler = setup
    
    # Agent starts speaking
    await state_manager.on_agent_speech_start()
    assert state_manager.is_speaking == True
    
    # User says "yeah" (backchannel)
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(event_id, "yeah")
    
    # Should NOT interrupt
    assert should_interrupt == False
    assert state_manager.is_speaking == True
    
    print("✅ Test 1 passed: Backchannel ignored during speech")


@pytest.mark.asyncio
async def test_backchannel_when_silent(setup):
    """
    Test Case 2: Backchannel When Silent
    Context: Agent is silent
    User says: "yeah"
    Expected: Agent processes as valid input
    """
    config, state_manager, handler = setup
    
    # Agent is silent (not speaking)
    assert state_manager.is_speaking == False
    
    # User says "yeah"
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(event_id, "yeah")
    
    # SHOULD process (not ignored)
    assert should_interrupt == True
    
    print("✅ Test 2 passed: Backchannel processed when silent")


@pytest.mark.asyncio
async def test_command_interrupts_speech(setup):
    """
    Test Case 3: Command Word Interrupts
    Context: Agent is speaking
    User says: "stop"
    Expected: Agent stops immediately
    """
    config, state_manager, handler = setup
    
    # Agent is speaking
    await state_manager.on_agent_speech_start()
    
    # User says "stop" (command word)
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(event_id, "stop")
    
    # Should interrupt
    assert should_interrupt == True
    
    print("✅ Test 3 passed: Command word interrupts speech")


@pytest.mark.asyncio
async def test_mixed_input_interrupts(setup):
    """
    Test Case 4: Mixed Input
    Context: Agent is speaking
    User says: "yeah but wait"
    Expected: Agent stops (contains command words)
    """
    config, state_manager, handler = setup
    
    # Agent is speaking
    await state_manager.on_agent_speech_start()
    
    # User says mixed input with command words
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(event_id, "yeah but wait")
    
    # Should interrupt (contains "but" and "wait")
    assert should_interrupt == True
    
    print("✅ Test 4 passed: Mixed input with command interrupts")


@pytest.mark.asyncio
async def test_multiple_backchannels_during_speech(setup):
    """
    Test Case 5: Multiple Backchannels
    Context: Agent is speaking
    User says: "ok yeah hmm"
    Expected: Agent continues (all backchannel words)
    """
    config, state_manager, handler = setup
    
    # Agent is speaking
    await state_manager.on_agent_speech_start()
    
    # User says multiple backchannel words
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(event_id, "ok yeah hmm")
    
    # Should NOT interrupt
    assert should_interrupt == False
    
    print("✅ Test 5 passed: Multiple backchannels ignored during speech")


@pytest.mark.asyncio
async def test_long_sentence_interrupts(setup):
    """
    Test Case 6: Longer Sentence
    Context: Agent is speaking
    User says: "what about the other option"
    Expected: Agent stops (meaningful input)
    """
    config, state_manager, handler = setup
    
    # Agent is speaking
    await state_manager.on_agent_speech_start()
    
    # User says a longer sentence
    event_id = await handler.on_user_speech_detected()
    should_interrupt = await handler.on_user_speech_transcribed(
        event_id, 
        "what about the other option"
    )
    
    # Should interrupt (meaningful sentence)
    assert should_interrupt == True
    
    print("✅ Test 6 passed: Longer sentence interrupts")


@pytest.mark.asyncio
async def test_command_variations(setup):
    """
    Test Case 7: Various Command Words
    Context: Agent is speaking
    User says various command words
    Expected: All should interrupt
    """
    config, state_manager, handler = setup
    
    command_words = ["stop", "wait", "no", "hold on", "pause", "wait a second"]
    
    for command in command_words:
        # Reset state
        await state_manager.on_agent_speech_start()
        
        # Test command
        event_id = await handler.on_user_speech_detected()
        should_interrupt = await handler.on_user_speech_transcribed(event_id, command)
        
        assert should_interrupt == True, f"Command '{command}' should interrupt"
        
        # Clean up
        await state_manager.on_agent_speech_end()
        await asyncio.sleep(0.01)
    
    print(f"✅ Test 7 passed: All {len(command_words)} command variations interrupt")


@pytest.mark.asyncio
async def test_backchannel_variations(setup):
    """
    Test Case 8: Various Backchannel Words
    Context: Agent is speaking
    User says various backchannel words
    Expected: All should be ignored
    """
    config, state_manager, handler = setup
    
    backchannel_words = ["yeah", "ok", "hmm", "right", "uh-huh", "got it", "cool"]
    
    for backchannel in backchannel_words:
        # Reset state
        await state_manager.on_agent_speech_start()
        
        # Test backchannel
        event_id = await handler.on_user_speech_detected()
        should_interrupt = await handler.on_user_speech_transcribed(event_id, backchannel)
        
        assert should_interrupt == False, f"Backchannel '{backchannel}' should be ignored"
        
        # Clean up
        await state_manager.on_agent_speech_end()
        await asyncio.sleep(0.01)
    
    print(f"✅ Test 8 passed: All {len(backchannel_words)} backchannel variations ignored")


@pytest.mark.asyncio
async def test_state_transitions(setup):
    """
    Test Case 9: State Transitions
    Test that state manager correctly tracks transitions
    """
    config, state_manager, handler = setup
    
    # Initial state
    assert state_manager.is_speaking == False
    
    # Start speaking
    await state_manager.on_agent_speech_start()
    assert state_manager.is_speaking == True
    
    # Stop speaking
    await state_manager.on_agent_speech_end()
    assert state_manager.is_speaking == False
    
    print("✅ Test 9 passed: State transitions work correctly")


@pytest.mark.asyncio
async def test_case_insensitivity(setup):
    """
    Test Case 10: Case Insensitivity
    Test that detection works regardless of case
    """
    config, state_manager, handler = setup
    
    # Agent speaking
    await state_manager.on_agent_speech_start()
    
    # Test uppercase
    event_id1 = await handler.on_user_speech_detected()
    result1 = await handler.on_user_speech_transcribed(event_id1, "YEAH")
    assert result1 == False
    
    # Test mixed case
    event_id2 = await handler.on_user_speech_detected()
    result2 = await handler.on_user_speech_transcribed(event_id2, "YeAh")
    assert result2 == False
    
    # Test command uppercase
    event_id3 = await handler.on_user_speech_detected()
    result3 = await handler.on_user_speech_transcribed(event_id3, "STOP")
    assert result3 == True
    
    print("✅ Test 10 passed: Case insensitivity works")


@pytest.mark.asyncio
async def test_empty_input(setup):
    """
    Test Case 11: Empty Input
    Context: Any state
    User says: "" (empty)
    Expected: No interruption
    """
    config, state_manager, handler = setup
    
    # Test with agent speaking
    await state_manager.on_agent_speech_start()
    event_id1 = await handler.on_user_speech_detected()
    result1 = await handler.on_user_speech_transcribed(event_id1, "")
    assert result1 == False
    
    # Test with agent silent
    await state_manager.on_agent_speech_end()
    event_id2 = await handler.on_user_speech_detected()
    result2 = await handler.on_user_speech_transcribed(event_id2, "")
    assert result2 == False
    
    print("✅ Test 11 passed: Empty input handled correctly")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Running Intelligent Interruption Handler Test Suite")
    print("="*60 + "\n")
    
    # Run pytest
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_all_tests()
