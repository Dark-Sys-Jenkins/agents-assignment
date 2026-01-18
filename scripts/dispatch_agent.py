import asyncio
import os
import sys
from livekit import api

async def main():
    room = sys.argv[1] if len(sys.argv) > 1 else "interrupt-demo"

    lk = api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )

    # Create room if it doesn't exist (safe to call; server may ignore if already exists)
    try:
        await lk.room.create_room(api.CreateRoomRequest(name=room))
    except Exception:
        pass

    # If your worker uses automatic dispatch (agent_name is empty), this may not be required.
    # But dispatching is the reliable way when agent_name is configured.
    agent_name = os.environ.get("AGENT_NAME", "")
    if agent_name:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(room=room, agent_name=agent_name)
        )
        print(f"Dispatched agent '{agent_name}' to room '{room}'")
    else:
        print(f"Room '{room}' created. (No AGENT_NAME set; relying on automatic dispatch)")

    await lk.aclose()

asyncio.run(main())
