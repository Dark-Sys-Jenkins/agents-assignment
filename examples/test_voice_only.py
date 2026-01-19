#!/usr/bin/env python3
"""
Test only Cartesia TTS voice synthesis
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def main():
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    if not cartesia_key:
        print("❌ Missing CARTESIA_API_KEY")
        return
    
    test_texts = [
        "Hello, this is a test.",
        "I am speaking with your voice.",
        "Speech synthesis is working perfectly."
    ]
    
    print("🎙️ Testing Cartesia Voice: 638efaaa-4d0c-442e-b701-3fae16aad012\n")
    
    async with httpx.AsyncClient(timeout=30) as client:
        for i, text in enumerate(test_texts, 1):
            print(f"Test {i}: \"{text}\"")
            
            try:
                resp = await client.post(
                    "https://api.cartesia.ai/tts/bytes",
                    headers={
                        "X-API-Key": cartesia_key,
                        "Cartesia-Version": "2024-06-10",
                        "Content-Type": "application/json"
                    },
                    json={
                        "transcript": text,
                        "model_id": "sonic-english",
                        "voice": {
                            "mode": "id",
                            "id": "638efaaa-4d0c-442e-b701-3fae16aad012"
                        },
                        "output_format": {
                            "container": "raw",
                            "encoding": "pcm_s16le",
                            "sample_rate": 24000
                        }
                    },
                    timeout=15
                )
                
                if resp.status_code == 200:
                    audio_bytes = resp.content
                    print(f"  ✅ Generated {len(audio_bytes)} bytes")
                    
                    if AUDIO_OK:
                        # Convert bytes to numpy array and play
                        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                        print(f"  ▶️  Playing... ", end='', flush=True)
                        sd.play(audio_data, samplerate=24000)
                        sd.wait()
                        print("✅")
                    print()
                else:
                    print(f"  ❌ {resp.status_code}: {resp.text[:100]}\n")
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:100]}\n")
    
    print("✅ Voice test complete!")

if __name__ == "__main__":
    asyncio.run(main())
