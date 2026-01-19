#!/usr/bin/env python3
"""
Local Speech-to-Speech Demo
Records audio from microphone -> Deepgram STT -> Grok LLM -> Cartesia TTS -> Play audio
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'livekit-agents'))

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    HAS_AUDIO = True
except (ImportError, OSError):
    HAS_AUDIO = False
    print("⚠️  Note: sounddevice/soundfile not installed. Using text-only mode.")

import httpx

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

async def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    if not HAS_AUDIO:
        return None
    
    print(f"🎤 Recording for {duration} seconds... (speak now)")
    try:
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32
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
    
    print("🎙️  Sending to Deepgram STT...")
    
    try:
        # Convert float32 to int16 for Deepgram
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {api_key}",
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
                print(f"📝 Transcribed: {transcript}")
                return transcript
            else:
                print(f"❌ STT Error: {response.status_code}")
                return None
    except Exception as e:
        print(f"❌ STT Error: {e}")
        return None

async def grok_llm(user_text, grok_key, conversation_history):
    """Get response from Groq LLM"""
    print("🧠 Processing with Groq...")
    
    conversation_history.append({"role": "user", "content": user_text})
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {grok_key}"},
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
                print(f"🤖 Agent: {assistant_text}")
                return assistant_text
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                print(f"❌ Groq Error: {error_msg}")
                return None
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None

async def cartesia_tts(text, cartesia_key):
    """Convert text to speech using Cartesia"""
    print("🔊 Converting to speech with Cartesia...")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.cartesia.ai/v1/tts/bytes",
                headers={"X-API-Key": cartesia_key},
                json={
                    "model_id": "sonic-english",
                    "transcript": text,
                    "duration": 10.0,
                    "language": "en",
                    "voice": {
                        "mode": "id",
                        "id": "default"
                    }
                }
            )
            
            if response.status_code == 200:
                audio_bytes = response.content
                print(f"✅ Generated {len(audio_bytes)} bytes of audio")
                return audio_bytes
            else:
                print(f"❌ TTS Error: {response.status_code}")
                return None
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return None

def play_audio(audio_bytes, sample_rate=24000):
    """Play audio bytes"""
    if not HAS_AUDIO or audio_bytes is None:
        return
    
    try:
        print("▶️  Playing response...")
        import wave
        import io
        
        # Try to play the audio
        audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
        sd.play(audio_data, samplerate=sample_rate)
        sd.wait()
        print("✅ Playback complete")
    except Exception as e:
        print(f"⚠️  Could not play audio: {e}")

async def main():
    """Run the speech-to-speech demo"""
    print("\n" + "="*60)
    print("🎙️  Speech-to-Speech Demo")
    print("="*60)
    
    # Load credentials
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if not deepgram_key:
        print("❌ Missing DEEPGRAM_API_KEY")
        return
    if not cartesia_key:
        print("❌ Missing CARTESIA_API_KEY")
        return
    if not groq_key:
        print("❌ Missing GROQ_API_KEY")
        print("   Visit: https://console.groq.com/")
        return
    
    print("✅ All API keys loaded\n")
    
    # Check for audio
    if not HAS_AUDIO:
        print("📝 Running in TEXT-ONLY mode (no microphone detected)")
        print("   To use audio, install: pip install sounddevice soundfile")
        text_mode = True
    else:
        text_mode = False
    
    conversation_history = [
        {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise. Keep responses short for natural speech flow."}
    ]
    
    print("="*60)
    print("Commands:")
    print("  Type or speak your message (audio auto-records)")
    print("  Type 'quit' to exit")
    print("="*60 + "\n")
    
    if text_mode:
        # Text-only mode
        while True:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Just use Groq LLM
            response = await grok_llm(user_input, groq_key, conversation_history)
            if response:
                print()
    else:
        # Audio mode
        while True:
            try:
                user_choice = input("\n🎤 Press Enter to record (or type text, or 'quit' to exit): ").strip()
            except EOFError:
                break
            
            if user_choice.lower() in ('quit', 'exit', 'q'):
                print("\n👋 Goodbye!")
                break
            
            if user_choice:
                # Text input
                user_text = user_choice
            else:
                # Record audio
                audio_result = await record_audio(duration=5)
                if not audio_result:
                    print("❌ Recording failed, try again\n")
                    continue
                
                audio_data, sample_rate = audio_result
                user_text = await deepgram_stt(audio_data, sample_rate, deepgram_key)
                
                if not user_text:
                    print("❌ STT failed, try again\n")
                    continue
            
            # Get LLM response
            response = await grok_llm(user_text, groq_key, conversation_history)
            
            if response:
                # Convert to speech
                audio_bytes = await cartesia_tts(response, cartesia_key)
                if audio_bytes:
                    play_audio(audio_bytes)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
