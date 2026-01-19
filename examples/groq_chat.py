#!/usr/bin/env python3
"""
Groq LLM Chat Demo
Uses Groq's fast inference API for chat completions
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def main():
    """Run the Groq demo"""
    print("\n" + "="*60)
    print("🚀 Groq LLM Chat Demo")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    
    if not groq_key:
        print("❌ Missing GROQ_API_KEY in .env file")
        return
    
    print("✅ Groq API Key loaded")
    print("📋 Available Models: llama-3.1-70b-versatile, mixtral-8x7b-32768, etc.")
    print("\n" + "="*60)
    print("📝 Chat Mode")
    print("="*60)
    print("Type your messages. Type 'quit' to exit.\n")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Be concise and friendly."}
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
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
            
            messages.append({"role": "user", "content": user_input})
            
            try:
                print("⏳ Thinking...", end='', flush=True)
                
                # Try current models first
                models_to_try = [
                    "llama-3.1-8b-instant",
                    "llama-3.2-90b-vision-preview",
                    "llama-3.1-70b-versatile",
                ]
                
                response = None
                for model in models_to_try:
                    try:
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {groq_key}"},
                            json={
                                "model": model,
                                "messages": messages,
                                "temperature": 0.7,
                                "max_tokens": 512
                            }
                        )
                        
                        if response.status_code == 200:
                            break
                        elif response.status_code == 401:
                            print("\r\n❌ Invalid API Key - please check GROQ_API_KEY in .env")
                            return
                    except:
                        continue
                
                if response and response.status_code == 200:
                    result = response.json()
                    assistant_message = result["choices"][0]["message"]["content"]
                    print("\r   \r", end='', flush=True)
                    print(f"🤖 Agent: {assistant_message}\n")
                    messages.append({"role": "assistant", "content": assistant_message})
                else:
                    print("\r\n❌ API Error")
                    if response:
                        print(f"   Status: {response.status_code}")
                        try:
                            error = response.json()
                            print(f"   Message: {error.get('error', {}).get('message', 'Unknown')}")
                        except:
                            print(f"   Response: {response.text[:200]}")
                    print()
            
            except Exception as e:
                print(f"\r\n❌ Error: {e}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
