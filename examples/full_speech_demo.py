#!/usr/bin/env python3
"""
Complete Speech-to-Speech Demo
🎤 Record Audio → 🎙️ Deepgram STT → 🧠 Groq LLM → 🔊 Cartesia TTS → ▶️ Playback
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx
import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  Audio libraries not available. Use text mode instead.")

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    if not AUDIO_AVAILABLE:
        return None
    
    print(f"🎤 Recording for {duration} seconds... (speak now!)")
    try:
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            device=None
        )
        sd.wait()
        return audio_data, sample_rate
    except Exception as e:
        print(f"❌ Recording error: {e}")
        return None

async def deepgram_stt(audio_data, sample_rate, api_key):
    """Convert speech to text using Deepgram"""
    if audio_data is None:
        return None
    
    print("🎙️  Converting speech to text...", end='', flush=True)
    
    try:
        # Convert to WAV format for Deepgram
        import io
        audio_int16 = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={"Authorization": f"Token {api_key}"},
                content=audio_int16.tobytes(),
                params={
                    "model": "nova-2",
                    "language": "en",
                    "encoding": "linear16",
                    "sample_rate": sample_rate
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                print(f"\r   ✅")
                return transcript
            else:
                print(f"\r   ❌ ({response.status_code})")
                return None
    except Exception as e:
        print(f"\r   ❌ Error: {e}")
        return None

async def groq_llm(user_text, groq_key, conversation_history):
    """Get response from Groq LLM"""
    print("🧠 Thinking...", end='', flush=True)
    
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
                print("\r   ✅")
                return assistant_text
            else:
                print(f"\r   ❌ ({response.status_code})")
                return None
    except Exception as e:
        print(f"\r   ❌ Error: {e}")
        return None

async def cartesia_tts(text, cartesia_key):
    """Convert text to speech using Cartesia"""
    print("🔊 Generating speech...", end='', flush=True)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try the correct Cartesia endpoint
            response = await client.post(
                "https://api.cartesia.ai/v1/tts/bytes",
                headers={"X-API-Key": cartesia_key},
                json={
                    "model_id": "sonic-english",
                    "transcript": text,
                    "language": "en",
                    "voice": {
                        "mode": "id",
                        "id": "default"
                    }
                }
            )
            
            if response.status_code == 200:
                print("\r   ✅")
                return response.content
            else:
                # If TTS fails, just continue without audio
                print(f"\r   ⏭️  (skipping audio)")
                return None
    except Exception as e:
        print(f"\r   ⏭️  (audio unavailable)")
        return None

def play_audio(audio_bytes):
    """Play audio bytes"""
    if not AUDIO_AVAILABLE or audio_bytes is None:
        return
    
    try:
        print("▶️  Playing response...", end='', flush=True)
        # Cartesia returns audio data - try to play it
        # Note: format depends on Cartesia's response type
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        if len(audio_array) > 0:
            sd.play(audio_array, samplerate=24000)
            sd.wait()
            print("\r   ✅")
        else:
            print("\r   (no audio data)")
    except Exception as e:
        print(f"\r   ⚠️  {e}")

async def main():
    """Run full speech-to-speech pipeline"""
    print("\n" + "="*60)
    print("🎙️  Complete Speech-to-Speech Demo")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    if not all([groq_key, deepgram_key, cartesia_key]):
        print("❌ Missing API keys")
        return
    
    print("\n✅ Configuration:")
    print("   🎙️  Deepgram STT: nova-2")
    print("   🧠 Groq LLM: llama-3.1-8b")
    print("   🔊 Cartesia TTS: sonic-english")
    
    if not AUDIO_AVAILABLE:
        print("\n⚠️  Audio support disabled - using text mode")
        mode = "text"
    else:
        print("\n✅ Audio support available")
        mode = "audio"
    
    print("\n" + "="*60)
    print(f"💬 Interactive Chat ({mode.upper()} mode)")
    print("="*60)
    
    if mode == "audio":
        print("Press Enter to record (5 seconds), or type 'text <message>' for text input")
    else:
        print("Type your message:")
    
    print("Type 'quit' to exit.\n")
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise. Keep responses short for natural speech."}
    ]
    
    while True:
        try:
            if mode == "audio":
                user_input = input("🎤 Press Enter to record (or 'text <msg>' or 'quit'): ").strip()
            else:
                user_input = input("👤 You: ").strip()
        except EOFError:
            break
        
        if user_input.lower() in ('quit', 'exit', 'q'):
            print("\n👋 Goodbye!")
            break
        
        user_text = None
        
        if mode == "audio" and not user_input:
            # Record audio
            audio_result = record_audio(duration=5)
            if audio_result:
                audio_data, sample_rate = audio_result
                user_text = await deepgram_stt(audio_data, sample_rate, deepgram_key)
                if user_text:
                    print(f"📝 You said: {user_text}\n")
        elif mode == "audio" and user_input.startswith("text "):
            # Text input
            user_text = user_input[5:].strip()
        elif mode == "text":
            user_text = user_input
        
        if not user_text:
            print()
            continue
        
        # Get LLM response
        response = await groq_llm(user_text, groq_key, conversation_history)
        
        if response:
            print(f"🤖 Agent: {response}\n")
            
            # Convert to speech
            audio_bytes = await cartesia_tts(response, cartesia_key)
            if audio_bytes:
                play_audio(audio_bytes)
                print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
