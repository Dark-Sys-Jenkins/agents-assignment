import os
import asyncio
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants, RoomConfiguration, RoomAgentDispatch

load_dotenv(override=True)

API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "http://localhost:7880")
ROOM_NAME = "test-room"

async def main():
    if not API_KEY or not API_SECRET:
        print("Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env")
        return

    # Create a token for the human user to join
    grants = VideoGrants(
        room_join=True,
        room=ROOM_NAME,
        can_publish=True,
        can_subscribe=True,
    )
    
    # Configure the room to automatically dispatch the agent
    room_config = RoomConfiguration(
        agents=[
            RoomAgentDispatch(
                agent_name="",  # Empty string matches unnamed agents
            )
        ]
    )
    
    token = (
        AccessToken(API_KEY, API_SECRET)
        .with_identity("human-user")
        .with_grants(grants)
        .with_room_config(room_config)
        .to_jwt()
    )

    print(f"\n--- Join {ROOM_NAME} ---")
    print(f"Token: {token}\n")
    
    # Construct the URL for the LiveKit Meet client
    url = f"https://meet.livekit.io/custom?liveKitUrl={LIVEKIT_URL}&token={token}"
    print(f"Join URL: {url}")
    print("------------------------\n")

if __name__ == "__main__":
    asyncio.run(main())
