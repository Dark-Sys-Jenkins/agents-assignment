#!/usr/bin/env python3
"""
Test Cartesia TTS with different voice formats
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def test_voice_format(api_key, payload_name, payload):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": api_key,
                "Cartesia-Version": "2024-06-10",
                "Content-Type": "application/json"
            },
            json=payload
        )
        status = resp.status_code
        if status == 200:
            result = f"✅ SUCCESS ({len(resp.content)} bytes)"
        else:
            try:
                msg = resp.json().get("message", resp.text[:100])
            except:
                msg = resp.text[:100]
            result = f"❌ {status}: {msg}"
        print(f"{payload_name}: {result}")

async def main():
    api_key = os.getenv("CARTESIA_API_KEY")
    
    print("Testing different Cartesia voice formats:\n")
    
    # Format 1: ID mode with default UUID
    await test_voice_format(api_key, "Voice with ID (default UUID)", {
        "transcript": "Hello, this is a test",
        "model_id": "sonic-english",
        "voice": {
            "mode": "id",
            "id": "00000000-0000-0000-0000-000000000000"
        },
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 24000
        }
    })
    
    # Format 2: Embedding with vector and output format
    await test_voice_format(api_key, "Voice with embedding + output", {
        "transcript": "Hello, this is a test",
        "model_id": "sonic-english",
        "voice": {
            "mode": "embedding",
            "embedding": [0.0] * 192
        },
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 24000
        }
    })
    
    # Format 3: Just ID mode with zero UUID
    await test_voice_format(api_key, "Voice ID mode only", {
        "transcript": "Hello, this is a test",
        "model_id": "sonic-english",
        "voice": {
            "mode": "id"
        }
    })

if __name__ == "__main__":
    asyncio.run(main())
