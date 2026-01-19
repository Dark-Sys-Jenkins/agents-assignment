#!/usr/bin/env python3
"""
Console chat demo with Grok LLM
- No STT/TTS needed (text-based)
- Tests Grok LLM integration
- Ready for voice integration once you get STT/TTS credentials
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Grok Console Chat Demo")
print("=" * 60)

# Check environment
grok_key = os.getenv("GROK_API_KEY")
if not grok_key:
    print("❌ GROK_API_KEY not found in .env")
    exit(1)

print("✓ Grok API Key loaded\n")

try:
    from livekit import agents
    from livekit.agents import llm
    from livekit.plugins import groq
    
    print("✓ LiveKit Agents framework loaded")
    print("✓ Grok plugin imported\n")
    
    # Create Grok LLM
    grok_llm = groq.LLM(
        model="mixtral-8x7b-32768",
        api_key=grok_key
    )
    print("✓ Grok LLM (mixtral-8x7b-32768) initialized\n")
    
    # System prompt
    system_prompt = """You are a helpful AI assistant powered by Grok.
You are concise, friendly, and helpful.
Keep responses short and natural."""
    
    async def chat_with_grok(user_message: str) -> str:
        """Send a message to Grok and get a response"""
        messages = [
            llm.ChatMessage(
                role="system",
                content=system_prompt
            ),
            llm.ChatMessage(
                role="user",
                content=user_message
            )
        ]
        
        response = await grok_llm.chat(messages=messages)
        return response.content
    
    # Run interactive chat
    async def main():
        print("=" * 60)
        print("Interactive Chat with Grok")
        print("Type 'quit' to exit")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("\nGrok: ", end="", flush=True)
                response = await chat_with_grok(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
    
    # Run the chat
    asyncio.run(main())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
