import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from livekit.plugins.deepgram import TTS

load_dotenv()
deepgram_key = os.getenv("DEEPGRAM_API_KEY")

async def main():
    if not deepgram_key:
        print("No Deepgram API Key")
        return
    
    print(f"Using Deepgram API Key: {deepgram_key[:5]}...")
    
    async with aiohttp.ClientSession() as session:
        tts = TTS(http_session=session, api_key=deepgram_key)
        try:
            print("Synthesizing text...")
            stream = tts.synthesize("Hello world")
            async for audio in stream:
                 print(f"Received audio chunk of size: {len(audio.frame.data)}")
                 break # Just need one chunk to confirm
            print("Success")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
