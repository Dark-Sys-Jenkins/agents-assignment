import asyncio
import time
from interrupt_handler import InterruptHandler, AgentState

async def create_demo_transcript():
    handler = InterruptHandler()
    
    print("=== DEMONSTRATION TRANSCRIPT ===\n")
    
    # Scene 1: Agent explaining something
    print("Agent: 'The history of ancient Rome spans over a thousand years...'")
    handler.set_agent_state(AgentState.SPEAKING)
    
    print("User: 'yeah... okay... uh-huh'")
    result = await handler.process_transcription("yeah okay uh-huh")
    print(f"Agent action: {result.value.upper()} (continues speaking)\n")
    
    # Scene 2: Agent asks question
    print("Agent: 'Are you ready to proceed?' (stops speaking)")
    handler.set_agent_state(AgentState.SILENT)
    
    print("User: 'Yeah'")
    result = await handler.process_transcription("yeah")
    print(f"Agent action: {result.value.upper()} (processes as response)\n")
    
    # Scene 3: Agent counting
    print("Agent: 'One, two, three...'")
    handler.set_agent_state(AgentState.SPEAKING)
    
    print("User: 'No stop'")
    result = await handler.process_transcription("no stop")
    print(f"Agent action: {result.value.upper()} (stops immediately)\n")

if __name__ == "__main__":
    asyncio.run(create_demo_transcript())