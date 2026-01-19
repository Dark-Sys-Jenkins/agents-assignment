import os
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

load_dotenv()

def generate_user_token():
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        print("Error: credentials not found.")
        return

    grant = VideoGrants(
        room_join=True, 
        room="test-room-2",
        can_publish=True, 
        can_subscribe=True
    )
    
    token = (
        AccessToken(api_key, api_secret)
        .with_identity("test-user")
        .with_name("Test User")
        .with_grants(grant)
        .to_jwt()
    )
    
    print(f"User Token:\n{token}")
    with open("user_token.txt", "w") as f:
        f.write(token)

if __name__ == "__main__":
    generate_user_token()
