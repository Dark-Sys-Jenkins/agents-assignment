import jwt
import time
import os
from dotenv import load_dotenv # type: ignore
load_dotenv()

API_KEY = os.getenv("LIVEKIT_API_KEY") or "YOUR_API_KEY"
API_SECRET = os.getenv("LIVEKIT_API_SECRET") or "YOUR_API_SECRET"


payload = {
    "iss": API_KEY,
    "sub": "user-123",
    "nbf": int(time.time()),
    "exp": int(time.time()) + 3600,
    "video": {
        "roomJoin": True,
        "room": "test-room"
    }
}

token = jwt.encode(payload, API_SECRET, algorithm="HS256")
print(token)
