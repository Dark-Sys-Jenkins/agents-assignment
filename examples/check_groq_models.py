#!/usr/bin/env python3
"""
Test which Groq models are available with your API key
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def test_model(client, api_key, model_name):
    """Test if a model is available"""
    try:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 10
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return "✅ AVAILABLE"
        elif response.status_code == 404:
            return "❌ Not found"
        elif "decommissioned" in response.text.lower():
            return "⚠️  Deprecated"
        else:
            return f"❌ {response.status_code}"
    except:
        return "❌ Error"

async def main():
    """Test available Groq models"""
    print("\n" + "="*60)
    print("🔍 Groq Model Availability Check")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("❌ Missing GROQ_API_KEY")
        return
    
    # List of known Groq models (historical and current)
    models = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-text-preview",
        "llama-3.2-1b-preview",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma-7b-it",
        "llama2-70b-4096",
    ]
    
    print(f"\nTesting {len(models)} models with your API key...\n")
    
    async with httpx.AsyncClient() as client:
        for model in models:
            status = await test_model(client, groq_key, model)
            print(f"  {model:40} {status}")
    
    print("\n" + "="*60)
    print("💡 Recommendation:")
    print("="*60)
    print("Your API key appears to have limited model access.")
    print("\nOptions:")
    print("1. Use the LiveKit Agents Groq plugin (recommended)")
    print("2. Get a newer API key from https://console.groq.com/")
    print("3. Use the speech-to-speech demo with available models")

if __name__ == "__main__":
    asyncio.run(main())
