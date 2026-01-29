import asyncio
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

from tests.fake_session import FakeActions, create_session, run_session
from tests.test_agent_session import MyAgent

async def main():
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Hello, how are you?", stt_delay=0.2)
    actions.add_llm("I'm doing well, thank you!", ttft=0.1, duration=0.3)
    actions.add_tts(2.0, ttfb=0.2, duration=0.3)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent()
    
    agent_state_events = []
    session.on("agent_state_changed", agent_state_events.append)
    
    try:
        t_origin = await asyncio.wait_for(run_session(session, agent), timeout=60.0)
        print(f"\nAgent state events: {len(agent_state_events)}")
        for ev in agent_state_events:
            print(f"  {ev.old_state} -> {ev.new_state}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
