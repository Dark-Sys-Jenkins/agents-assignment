import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

print(os.getenv("LIVEKIT_URL"))
print(os.getenv("OPENAI_API_KEY") is not None)
print(os.getenv("DEEPGRAM_API_KEY") is not None)
