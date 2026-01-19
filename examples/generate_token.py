import os
import asyncio
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

load_dotenv()

API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not API_KEY or not API_SECRET:
    print("Error: LiveKit API Key/Secret not found in environment.")
    exit(1)

def get_token():
    grant = VideoGrants(
        room_join=True,
        room="test-room",
        can_publish=True,
        can_subscribe=True,
    )
    
    token = (
        AccessToken(API_KEY, API_SECRET)
        .with_identity("user-test")
        .with_name("Test User")
        .with_grants(grant)
        .to_jwt()
    )
    
    return token

if __name__ == "__main__":
    print("\n--- COPY THE TOKEN BELOW ---")
    print(get_token())
    print("----------------------------\n")
