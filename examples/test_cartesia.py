#!/usr/bin/env python3
"""Test Cartesia TTS endpoint formats"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def test_endpoints():
    """Test different Cartesia endpoint formats"""
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not cartesia_key:
        print("❌ Missing CARTESIA_API_KEY")
        return
    
    text = "Hello, how are you?"
    
    endpoints = [
        ("POST /v1/tts/bytes", "https://api.cartesia.ai/v1/tts/bytes"),
        ("POST /tts/bytes", "https://api.cartesia.ai/tts/bytes"),
        ("POST /v1/audio", "https://api.cartesia.ai/v1/audio"),
        ("POST /audio", "https://api.cartesia.ai/audio"),
        ("POST /v1/tts", "https://api.cartesia.ai/v1/tts"),
        ("POST /tts", "https://api.cartesia.ai/tts"),
    ]
    
    payloads = [
        {"model_id": "sonic-english", "transcript": text, "language": "en"},
        {"model": "sonic-english", "transcript": text, "language": "en"},
        {"text": text, "model": "sonic-english"},
        {"text": text},
    ]
    
    async with httpx.AsyncClient(timeout=10) as client:
        for endpoint_name, url in endpoints:
            for i, payload in enumerate(payloads):
                try:
                    print(f"\n🧪 Testing {endpoint_name} with payload {i+1}...", end='')
                    resp = await client.post(
                        url,
                        headers={"X-API-Key": cartesia_key, "Content-Type": "application/json"},
                        json=payload
                    )
                    if resp.status_code == 200:
                        print(f" ✅ SUCCESS! ({len(resp.content)} bytes)")
                        print(f"   URL: {url}")
                        print(f"   Payload: {payload}")
                        return
                    else:
                        error = resp.text[:60] if resp.text else ""
                        print(f" ❌ {resp.status_code} {error}")
                except Exception as e:
                    print(f" ❌ {str(e)[:40]}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
