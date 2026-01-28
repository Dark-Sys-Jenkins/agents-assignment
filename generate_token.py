import os
from livekit.api import AccessToken, VideoGrants

# Load from .env or hard‑code here
API_KEY = os.getenv("LIVEKIT_API_KEY", "testkey")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "testsecret")

room_name = "test-room"
identity = "test-user"

# Build grants
grants = VideoGrants(
    room_join=True,
    room=room_name,
    can_publish=True,
    can_subscribe=True,
)

# Build token
token = (
    AccessToken(API_KEY, API_SECRET)
    .with_identity(identity)
    .with_grants(grants)
)

# Print JWT
print(token.to_jwt())
