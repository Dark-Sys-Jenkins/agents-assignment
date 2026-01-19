#!/usr/bin/env python3
"""
Simple console demo with Grok LLM + Deepgram STT + ElevenLabs TTS + Silero VAD
This tests all components work together
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 50)
print("Grok + Deepgram + ElevenLabs + Silero Demo Agent")
print("=" * 50)

# Check environment
grok_key = os.getenv("GROK_API_KEY")
if not grok_key:
    print("❌ GROK_API_KEY not found in .env")
    exit(1)

print("✓ Grok API Key loaded")
print("\nInitializing components...\n")

try:
    # Import framework
    from livekit import agents
    print("[1/5] ✓ LiveKit Agents framework loaded")
    
    # Import and initialize Groq LLM
    from livekit.plugins import groq
    grok_llm = groq.LLM(model="mixtral-8x7b-32768", api_key=grok_key)
    print("[2/5] ✓ Grok LLM (mixtral-8x7b-32768) ready")
    
    # Import and initialize Deepgram STT
    from livekit.plugins import deepgram
    deepgram_stt = deepgram.STT()
    print("[3/5] ✓ Deepgram STT (Speech-to-Text) ready")
    
    # Import and initialize ElevenLabs TTS
    from livekit.plugins import elevenlabs
    elevenlabs_tts = elevenlabs.TTS()
    print("[4/5] ✓ ElevenLabs TTS (Text-to-Speech) ready")
    
    # Import and initialize Silero VAD
    from livekit.plugins import silero
    silero_vad = silero.VAD.load()
    print("[5/5] ✓ Silero VAD (Voice Activity Detection) loaded")
    
    print("\n" + "=" * 50)
    print("SUCCESS! All components initialized ✓")
    print("=" * 50)
    print("\nComponent Details:")
    print(f"  • LLM: Groq (mixtral-8x7b-32768)")
    print(f"  • STT: Deepgram")
    print(f"  • TTS: ElevenLabs")
    print(f"  • VAD: Silero (local, no API key needed)")
    print("\nReady to run the agent!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
