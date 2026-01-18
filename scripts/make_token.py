import os
import sys
from livekit import api

room = sys.argv[1] if len(sys.argv) > 1 else "interrupt-demo"
identity = sys.argv[2] if len(sys.argv) > 2 else "user1"

token = (
    api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
    .with_identity(identity)
    .with_grants(api.VideoGrants(room_join=True, room=room))
    .to_jwt()
)

print(token)
