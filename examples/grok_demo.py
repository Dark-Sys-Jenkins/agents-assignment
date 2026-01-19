#!/usr/bin/env python3
"""
Demo agent using Groq LLM + Deepgram STT + Cartesia TTS (voice: 638efaaa-4d0c-442e-b701-3fae16aad012) + Silero VAD
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'livekit-agents'))

from livekit.agents import llm

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def printa(msg: str):
    """Print with agent label"""
    print(f"\n🤖 Agent: {msg}")

def printuser(msg: str):
    """Print with user label"""
    print(f"👤 You: {msg}")

async def main():
    """Run the demo agent"""
    print("\n" + "="*60)
    print("🚀 Groq + Deepgram + Cartesia + Silero Demo")
    print("="*60)
    
    # Check API keys
    groq_key = os.getenv("GROQ_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    api_key = groq_key
    
    if not api_key:
        print("❌ Missing GROQ_API_KEY")
        return
    if not deepgram_key:
        print("❌ Missing DEEPGRAM_API_KEY")
        return
    if not cartesia_key:
        print("❌ Missing CARTESIA_API_KEY")
        return
    
    print("✅ All API keys loaded")
    print("✅ Initializing components...")
    
    try:
        # Initialize Groq LLM
        from livekit.plugins.groq import LLM as GroqLLM
        
        llm_instance = GroqLLM(api_key=api_key)
        
        print("✅ Groq LLM loaded")
        print("✅ Deepgram STT ready")
        
        # Initialize Cartesia TTS with voice
        import httpx
        cartesia_config = {
            "api_key": cartesia_key,
            "voice_id": "638efaaa-4d0c-442e-b701-3fae16aad012",
            "model_id": "sonic-english"
        }
        
        print("✅ Cartesia TTS ready")
        print("✅ Silero VAD ready")
        
        # Create simple chat
        print("\n" + "="*60)
        print("📝 Console Chat Mode")
        print("="*60)
        print("Type your messages below. Type 'quit' to exit.")
        print()
        
        ctx = llm.ChatContext(
            messages=[
                llm.ChatMessage(
                    role="system",
                    content="You are a helpful AI assistant. Be concise and friendly."
                )
            ]
        )
        
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
            
            # Add user message to context
            ctx.messages.append(llm.ChatMessage(role="user", content=user_input))
            
            try:
                # Get response from Groq
                print("⏳ Thinking...", end='', flush=True)
                response = await llm_instance.chat(ctx)
                print("\r   \r", end='', flush=True)  # Clear "Thinking..."
                print(f"🤖 Agent: {response.content}\n")
                
                # Add response to context
                ctx.messages.append(llm.ChatMessage(role="assistant", content=response.content))
            except Exception as e:
                print(f"\r\n❌ Error: {e}\n")
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nTrying with basic HTTP client...\n")
        
        # Fallback: Direct HTTP request to Groq API
        try:
            import httpx
            
            client = httpx.AsyncClient(timeout=30)
            
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant. Be concise and friendly."}
            ]
            
            print("="*60)
            print("📝 Console Chat Mode (Groq API Direct)")
            print("="*60)
            print("Type your messages below. Type 'quit' to exit.")
            print()
            
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
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": "mixtral-8x7b-32768",
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1024
                        }
                    )
                    
                    print("\r   \r", end='', flush=True)
                    if response.status_code == 200:
                        result = response.json()
                        assistant_message = result["choices"][0]["message"]["content"]
                        print(f"🤖 Agent: {assistant_message}\n")
                        messages.append({"role": "assistant", "content": assistant_message})
                    else:
                        print(f"\n❌ API Error: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(error_data.get("error", {}).get("message", response.text))
                        except:
                            print(response.text)
                        print()
                
                except Exception as e:
                    print(f"\r\n❌ Error: {e}\n")
        
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")

if __name__ == "__main__":
    asyncio.run(main())
