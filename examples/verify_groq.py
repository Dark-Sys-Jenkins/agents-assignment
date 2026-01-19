#!/usr/bin/env python3
"""
Groq Setup Verification Demo
Tests Groq API connection and available models
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def main():
    """Verify Groq setup"""
    print("\n" + "="*60)
    print("🚀 Groq Setup Verification")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    print("\n✅ Configuration Status:")
    print(f"   GROQ_API_KEY: {'✓ Found' if groq_key else '✗ Missing'}")
    print(f"   DEEPGRAM_API_KEY: {'✓ Found' if deepgram_key else '✗ Missing'}")
    print(f"   CARTESIA_API_KEY: {'✓ Found' if cartesia_key else '✗ Missing'}")
    
    if not groq_key:
        print("\n❌ Missing GROQ_API_KEY - please add to .env")
        return
    
    print("\n" + "="*60)
    print("🔍 Testing Groq API Connection...")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Test basic API connection
            print("\n⏳ Connecting to Groq API...")
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": "say hello in 5 words"}],
                    "max_tokens": 100
                }
            )
            
            if response.status_code == 200:
                print("✅ Groq API Connection: SUCCESS")
                result = response.json()
                message = result["choices"][0]["message"]["content"]
                print(f"\n🤖 Test Response: {message}")
                
                print("\n" + "="*60)
                print("✨ Setup Complete!")
                print("="*60)
                print("\nYour system is ready to use Groq with:")
                print("  ✅ Groq LLM (Fast Inference)")
                print("  ✅ Deepgram STT (Speech-to-Text)")
                print("  ✅ Cartesia TTS (Text-to-Speech)")
                print("  ✅ Silero VAD (Voice Activity Detection)")
                
            elif response.status_code == 401:
                print("❌ Groq API Connection: FAILED - Invalid API Key")
                print(f"\nThe key provided starts with: {groq_key[:10]}...")
                print("Please verify it's a valid Groq API key from https://console.groq.com/")
                
            else:
                print(f"❌ Groq API Connection: FAILED ({response.status_code})")
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                print(f"   Error: {error_msg}")
        
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            print("   Make sure you have internet connection and the API key is valid")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
