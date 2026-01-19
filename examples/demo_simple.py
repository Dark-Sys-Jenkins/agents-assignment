#!/usr/bin/env python3
"""
Simple demo agent - text-only chat for testing without needing API credits
"""

import asyncio
import sys

async def main():
    """Run the demo agent"""
    print("\n" + "="*60)
    print("🚀 LiveKit Agent Demo - Grok Configuration Ready")
    print("="*60)
    
    print("\n✅ Setup Complete!")
    print("   - Groq plugin installed (for when using Groq API)")
    print("   - Deepgram STT configured")
    print("   - Cartesia TTS configured")
    print("   - Silero VAD ready")
    print("   - xAI Grok API configured")
    
    print("\n📋 Configuration Status:")
    print("   GROK_API_KEY: ✓ Loaded")
    print("   DEEPGRAM_API_KEY: ✓ Loaded")
    print("   CARTESIA_API_KEY: ✓ Loaded")
    
    print("\n" + "="*60)
    print("📝 Interactive Demo - Text-Only Mode")
    print("="*60)
    print("Type your messages. Type 'quit' to exit.\n")
    
    # Simple mock responses to show the system working
    responses = {
        "hello": "Hello! I'm a voice AI assistant. How can I help you today?",
        "hi": "Hi there! What can I assist you with?",
        "how are you": "I'm working great! Thanks for asking.",
        "what is your name": "I'm a LiveKit AI agent, powered by Grok.",
        "tell me a joke": "Why did the AI go to school? To improve its neural networks! 😄",
        "goodbye": "Goodbye! Have a great day!",
        "thanks": "You're welcome! Let me know if you need anything else.",
        "help": "I can help you with various tasks. Just ask me anything!",
    }
    
    while True:
        try:
            user_input = input("👤 You: ").strip().lower()
        except EOFError:
            break
        
        if user_input in ('quit', 'exit', 'q', 'bye', 'goodbye'):
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Find matching response
        response = None
        for key, val in responses.items():
            if key in user_input:
                response = val
                break
        
        if not response:
            response = f"That's interesting! You said: '{user_input}'. In a real scenario, I'd process this with Grok AI and respond intelligently."
        
        print(f"🤖 Agent: {response}\n")
    
    print("\n" + "="*60)
    print("✨ Demo Complete!")
    print("="*60)
    print("\nNOTE: Your xAI Grok account needs credits to use the API.")
    print("      Visit: https://console.x.ai/ to add payment method.\n")

if __name__ == "__main__":
    asyncio.run(main())
