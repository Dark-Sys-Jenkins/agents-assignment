import os
import asyncio

from livekit.api import LiveKitAPI, AccessToken, VideoGrants
from livekit.api.room_service import CreateRoomRequest
from livekit.api.agent_dispatch_service import CreateAgentDispatchRequest

# --- Configuration --- #

# Must exactly match the LiveKit server API key/secret
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "http://localhost:7880")
API_KEY = os.environ["LIVEKIT_API_KEY"]
API_SECRET = os.environ["LIVEKIT_API_SECRET"]

ROOM_NAME = "test-room"
PARTICIPANT_IDENTITY = "participant1"
AGENT_NAME = ""  # must match the agent registered with your worker

# ---------------------- #

async def main():
    # 1) Connect to the LiveKit server API
    lkapi = LiveKitAPI(LIVEKIT_URL, API_KEY, API_SECRET)

    # 2) Create the room (optional — LiveKit auto‑creates on first join)
    try:
        print(f"Creating room: {ROOM_NAME}")
        room_info = await lkapi.room.create_room(
            CreateRoomRequest(name=ROOM_NAME)
        )
        print("Room created:", room_info.name)
    except Exception as e:
        print("Room might already exist:", e)

    # 3) Generate a join token for your participant
    grants = VideoGrants(
        room_join=True,
        room=ROOM_NAME,
        can_publish=True,
        can_subscribe=True,
    )
    token = (
        AccessToken(API_KEY, API_SECRET)
        .with_identity(PARTICIPANT_IDENTITY)
        .with_grants(grants)
    )
    jwt_token = token.to_jwt()
    print("\nGenerated JWT token:\n", jwt_token)

    # 4) Explicitly dispatch your agent
    dispatch_req = CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=ROOM_NAME)
    dispatch = await lkapi.agent_dispatch.create_dispatch(dispatch_req)
    print("\nDispatch created:\n", dispatch)

    # 5) Print the join URL you can open in browser
    browser_url = f"https://meet.livekit.io/custom?liveKitUrl={LIVEKIT_URL}&token={jwt_token}"
    print("\nOpen this link to join the room:\n", browser_url)

    # Close client
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
