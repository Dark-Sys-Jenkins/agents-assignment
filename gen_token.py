import os
from livekit import api
from dotenv import load_dotenv

load_dotenv()

def generate_token():
    url = os.getenv('LIVEKIT_URL')
    api_key = os.getenv('LIVEKIT_API_KEY')
    api_secret = os.getenv('LIVEKIT_API_SECRET')
    
    if not all([url, api_key, api_secret]):
        print("Error: Missing LiveKit credentials in .env file.")
        return

    # Use a generic room name for testing
    room_name = "test-room"
    participant_name = "test-user"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(participant_name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
            )
        )
    )
    
    jwt = token.to_jwt()
    print("\n--- LiveKit Connection Details ---")
    print(f"URL:   {url}")
    print(f"Token: {jwt}")
    print("----------------------------------\n")
    print(f"Use these details at: https://agents-playground.livekit.io/?url={url}&token={jwt}")

if __name__ == "__main__":
    generate_token()
