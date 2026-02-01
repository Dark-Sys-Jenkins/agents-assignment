import asyncio
from interrupt_handler import InterruptHandler, AgentState

async def test_scenarios():
    handler = InterruptHandler()
    
    # Scenario 1: Agent speaking, user says filler words
    print("Test 1: Agent speaking, user says 'yeah ok hmm'")
    handler.set_agent_state(AgentState.SPEAKING)
    result = await handler.process_transcription("yeah okay hmm")
    assert result.value == "ignore", f"Expected 'ignore', got {result.value}"
    print("✓ Passed: Agent ignores filler words while speaking")
    
    # Scenario 2: Agent silent, user says 'yeah'
    print("\nTest 2: Agent silent, user says 'yeah'")
    handler.set_agent_state(AgentState.SILENT)
    result = await handler.process_transcription("yeah")
    assert result.value == "respond", f"Expected 'respond', got {result.value}"
    print("✓ Passed: Agent responds when silent")
    
    # Scenario 3: Agent speaking, user says 'no stop'
    print("\nTest 3: Agent speaking, user says 'no stop'")
    handler.set_agent_state(AgentState.SPEAKING)
    result = await handler.process_transcription("no stop")
    assert result.value == "interrupt", f"Expected 'interrupt', got {result.value}"
    print("✓ Passed: Agent interrupts on command words")
    
    # Scenario 4: Mixed input
    print("\nTest 4: Agent speaking, user says 'yeah okay but wait'")
    handler.set_agent_state(AgentState.SPEAKING)
    result = await handler.process_transcription("yeah okay but wait")
    assert result.value == "interrupt", f"Expected 'interrupt', got {result.value}"
    print("✓ Passed: Agent interrupts on mixed input with commands")

if __name__ == "__main__":
    asyncio.run(test_scenarios())