#!/usr/bin/env python3
"""Quick test of fixed Cartesia TTS"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def test_tts():
    """Test the fixed Cartesia TTS endpoint"""
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        print("❌ Missing CARTESIA_API_KEY")
        return
    
    text = "Hello! I'm working properly now."
    
    print(f"🧪 Testing Cartesia TTS with correct endpoint...")
    print(f"   Text: {text}")
    
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": cartesia_key,
                "Cartesia-Version": "2024-06-10",
                "Content-Type": "application/json"
            },
            json={
                "transcript": text,
                "model_id": "sonic-english"
            }
        )
        
        if resp.status_code == 200:
            print(f"✅ SUCCESS!")
            print(f"   Status: 200")
            print(f"   Audio bytes: {len(resp.content)}")
            print(f"   Ready for playback!")
        else:
            print(f"❌ Error: {resp.status_code}")
            print(f"   {resp.text[:100]}")

if __name__ == "__main__":
    asyncio.run(test_tts())
