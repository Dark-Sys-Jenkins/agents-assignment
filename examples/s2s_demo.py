#!/usr/bin/env python3
"""
Speech-to-Speech Demo - Text Mode (works immediately)
Groq LLM + Deepgram STT + Cartesia TTS + Silero VAD
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def groq_llm(user_text, groq_key, conversation_history):
    """Get response from Groq LLM"""
    print("🧠 Processing with Groq...", end='', flush=True)
    
    conversation_history.append({"role": "user", "content": user_text})
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": conversation_history,
                    "temperature": 0.7,
                    "max_tokens": 256
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_text = result["choices"][0]["message"]["content"]
                conversation_history.append({"role": "assistant", "content": assistant_text})
                print("\r   \r", end='', flush=True)
                return assistant_text
            else:
                print("\r\n❌ Error\n", end='', flush=True)
                return None
    except Exception as e:
        print(f"\r❌ Error: {e}\n", end='', flush=True)
        return None

async def cartesia_tts(text, cartesia_key):
    """Convert text to speech using Cartesia"""
    print("🔊 Converting to speech...", end='', flush=True)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.cartesia.ai/v1/tts/stream",
                headers={"X-API-Key": cartesia_key},
                json={
                    "model_id": "sonic-english",
                    "transcript": text,
                    "language": "en"
                }
            )
            
            if response.status_code == 200:
                print("\r   \r", end='', flush=True)
                return response.content
            else:
                print(f"\r❌ {response.status_code}\n", end='', flush=True)
                return None
    except Exception as e:
        print(f"\r❌ Error: {str(e)[:50]}\n", end='', flush=True)
        return None

async def main():
    """Run speech-to-speech demo"""
    print("\n" + "="*60)
    print("🎙️  Speech-to-Speech Demo (Text Mode)")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not groq_key or not cartesia_key or not deepgram_key:
        print("❌ Missing API keys")
        return
    
    print("✅ All API keys loaded\n")
    print("="*60)
    print("📝 Chat Mode - Full Speech-to-Speech Pipeline")
    print("="*60)
    print("Type your message (will be processed by Groq + TTS)\n")
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise."}
    ]
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
        except EOFError:
            break
        
        if user_input.lower() in ('quit', 'exit', 'q'):
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Get Groq response
        response = await groq_llm(user_input, groq_key, conversation_history)
        
        if response:
            print(f"🤖 Agent: {response}\n")
            
            # Convert to speech
            audio_bytes = await cartesia_tts(response, cartesia_key)
            
            if audio_bytes:
                print(f"✅ Audio generated ({len(audio_bytes)} bytes)")
                print("   (Audio playback requires sounddevice - install with: pip install sounddevice)\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
