#!/usr/bin/env python3
"""
Speech-to-Speech Pipeline Demo
Groq LLM (working) + Deepgram STT (working) + Cartesia TTS (optional)
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def main():
    """Run speech-to-speech pipeline demo"""
    print("\n" + "="*60)
    print("🎙️  Speech-to-Speech Pipeline Demo")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    if not all([groq_key, deepgram_key, cartesia_key]):
        print("❌ Missing API keys")
        return
    
    print("\n✅ Configuration:")
    print("   🧠 Groq LLM: llama-3.1-8b-instant")
    print("   🎙️  Deepgram STT: nova-2")
    print("   🔊 Cartesia TTS: sonic-english")
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise. Keep responses short."}
    ]
    
    print("\n" + "="*60)
    print("💬 Interactive Chat")
    print("="*60)
    print("Type messages to chat with Groq LLM via speech-to-speech pipeline\n")
    
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
        
        print("🧠 Groq thinking...", end='', flush=True)
        
        conversation_history.append({"role": "user", "content": user_input})
        
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
                    print(f"🤖 Agent: {assistant_text}\n")
                else:
                    print(f"\r❌ Error {response.status_code}\n", end='', flush=True)
        
        except Exception as e:
            print(f"\r❌ Error: {e}\n", end='', flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
