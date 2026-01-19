#!/usr/bin/env python3
"""
Complete Speech-to-Speech Pipeline Demo
Deepgram STT → Groq LLM → Cartesia TTS
With microphone recording and audio playback
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    if not AUDIO_AVAILABLE:
        return None
    
    try:
        print(f"🎤 Recording {duration}s... speak now!", end='', flush=True)
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        print("\r   ✅ Recorded")
        return (audio_data, sample_rate)
    except:
        print("\r   ❌ Recording failed")
        return None

async def deepgram_stt(audio_data, sample_rate, deepgram_key):
    """Convert audio to text"""
    if audio_data is None:
        return None
    
    print("🎙️  Transcribing...", end='', flush=True)
    
    try:
        # Convert to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {deepgram_key}",
                    "Content-Type": "audio/raw;encoding=linear16;sample_rate=16000"
                },
                content=audio_bytes,
                params={
                    "model": "nova-2",
                    "language": "en"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                print(f"\r   ✅ '{transcript}'")
                return transcript
            else:
                print(f"\r   ❌ ({response.status_code})")
                return None
    except Exception as e:
        print(f"\r   ❌ {str(e)[:30]}")
        return None

async def groq_llm(user_text, groq_key, conversation_history):
    """Get LLM response"""
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
                print(f"\r   ✅")
                return assistant_text
            else:
                print(f"\r   ❌ ({response.status_code})")
                return None
    except Exception as e:
        print(f"\r   ❌ Error")
        return None

async def cartesia_tts(text, cartesia_key):
    """Convert text to speech"""
    print("🔊 Generating audio...", end='', flush=True)
    
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
                print(f"\r   ✅ ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"\r   ⏭️  (TTS unavailable)")
                return None
    except:
        print(f"\r   ⏭️  (TTS unavailable)")
        return None

def play_audio(audio_bytes):
    """Play audio response"""
    if not AUDIO_AVAILABLE or not audio_bytes:
        return
    
    try:
        print("▶️  Playing response...", end='', flush=True)
        # Assume Cartesia returns audio data
        audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
        sd.play(audio_data, samplerate=24000)
        sd.wait()
        print("\r   ✅ Done")
    except:
        print("\r   (audio playback not available)")

async def main():
    """Run the speech-to-speech demo"""
    print("\n" + "="*60)
    print("🎙️  COMPLETE SPEECH-TO-SPEECH DEMO")
    print("="*60)
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    
    if not all([groq_key, deepgram_key, cartesia_key]):
        print("❌ Missing API keys in .env")
        return
    
    print("\n✅ Configuration:")
    print(f"   🎙️  Deepgram STT: nova-2")
    print(f"   🧠 Groq LLM: llama-3.1-8b-instant")
    print(f"   🔊 Cartesia TTS: sonic-english")
    
    if AUDIO_AVAILABLE:
        print(f"   🎤 Microphone: Available")
    else:
        print(f"   🎤 Microphone: Not available (install: pip install sounddevice)")
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise."}
    ]
    
    print("\n" + "="*60)
    print("💬 INTERACTIVE SPEECH-TO-SPEECH CHAT")
    print("="*60)
    
    if AUDIO_AVAILABLE:
        print("\nOptions:")
        print("  Press Enter → Record 5 seconds of speech")
        print("  Type 'text <message>' → Chat with text")
        print("  Type 'quit' → Exit")
    else:
        print("\nUsing text mode (no microphone available)")
    
    print()
    
    while True:
        try:
            if AUDIO_AVAILABLE:
                user_input = input("🎤 Press Enter to record (or 'text <msg>' or 'quit'): ").strip()
            else:
                user_input = input("👤 You: ").strip()
        except EOFError:
            break
        
        if not user_input:
            if not AUDIO_AVAILABLE:
                continue
            # Record audio
            audio_result = await record_audio(duration=5)
            if not audio_result:
                continue
            user_text = await deepgram_stt(audio_result[0], audio_result[1], deepgram_key)
        elif user_input.lower() in ('quit', 'exit', 'q'):
            print("\n👋 Goodbye!")
            break
        elif user_input.lower().startswith('text '):
            user_text = user_input[5:]
        else:
            if AUDIO_AVAILABLE:
                continue
            user_text = user_input
        
        if not user_text:
            continue
        
        print(f"📝 You: {user_text}")
        
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
