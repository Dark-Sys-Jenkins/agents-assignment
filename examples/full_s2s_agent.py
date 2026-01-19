#!/usr/bin/env python3
"""
COMPLETE SPEECH-TO-SPEECH AI AGENT
Full end-to-end: Microphone → STT → LLM → TTS → Speaker
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import httpx
import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False
    print("Installing audio libraries...")
    os.system(f"{sys.executable} -m pip install sounddevice soundfile -q")
    try:
        import sounddevice as sd
        import soundfile as sf
        AUDIO_OK = True
    except:
        AUDIO_OK = False

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("\n" + "="*70)
print("🎙️  FULL SPEECH-TO-SPEECH AI AGENT")
print("="*70)

if not AUDIO_OK:
    print("❌ Audio support required. Cannot continue.")
    sys.exit(1)

print("✅ Audio system ready\n")

class SpeechToSpeechAgent:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.deepgram_key = os.getenv("DEEPGRAM_API_KEY")
        self.cartesia_key = os.getenv("CARTESIA_API_KEY")
        self.conversation = []
        
        if not all([self.groq_key, self.deepgram_key, self.cartesia_key]):
            print("❌ Missing API keys in .env file")
            sys.exit(1)
        
        print("Configuration:")
        print(f"  🎙️  Deepgram STT: READY")
        print(f"  🧠 Groq LLM: READY")
        print(f"  🔊 Cartesia TTS: READY")
    
    def record_speech(self, duration=5, sr=16000):
        """Record audio from microphone"""
        print(f"\n🎤 Recording {duration}s (speak now!)... ", end='', flush=True)
        try:
            audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype=np.float32)
            sd.wait()
            print("✅")
            return audio.flatten(), sr
        except Exception as e:
            print(f"❌ {e}")
            return None, None
    
    async def transcribe(self, audio, sr):
        """Convert speech to text with Deepgram"""
        print("🎙️  Transcribing... ", end='', flush=True)
        try:
            # Normalize and convert to int16
            audio = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio * 32767).astype(np.int16).tobytes()
            
            async with httpx.AsyncClient(timeout=30) as client:
                # Use multipart form for audio data
                response = await client.post(
                    f"https://api.deepgram.com/v1/listen?model=nova-2&language=en",
                    headers={
                        "Authorization": f"Token {self.deepgram_key}",
                        "Content-Type": "audio/raw"
                    },
                    content=audio_int16
                )
            
            if response.status_code == 200:
                result = response.json()
                text = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                print(f"✅\n  📝 '{text}'")
                return text
            else:
                print(f"❌ ({response.status_code})")
                if response.text:
                    print(f"     Error: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"❌ {e}")
            return None
    
    async def get_response(self, user_text):
        """Get response from Groq LLM"""
        print("🧠 Thinking... ", end='', flush=True)
        try:
            self.conversation.append({"role": "user", "content": user_text})
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_key}"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": "You are a helpful voice AI assistant. Be conversational and concise. Keep responses short for natural speech."}
                        ] + self.conversation,
                        "temperature": 0.7,
                        "max_tokens": 200
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                self.conversation.append({"role": "assistant", "content": text})
                print(f"✅\n  🤖 {text}")
                return text
            else:
                print(f"❌ ({response.status_code})")
                return None
        except Exception as e:
            print(f"❌ {e}")
            return None
    
    async def synthesize(self, text):
        """Convert text to speech with Cartesia"""
        print("🔊 Generating speech... ", end='', flush=True)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.cartesia.ai/v1/tts/stream",
                    headers={"X-API-Key": self.cartesia_key},
                    json={
                        "model_id": "sonic-english",
                        "transcript": text,
                        "language": "en"
                    }
                )
            
            if response.status_code == 200:
                print(f"✅ ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"⏭️  (TTS error: {response.status_code})")
                return None
        except Exception as e:
            print(f"⏭️  (TTS error)")
            return None
    
    def play_audio(self, audio_bytes):
        """Play audio response"""
        if not audio_bytes:
            return
        
        try:
            print("▶️  Playing response... ", end='', flush=True)
            # Try to parse as float32 audio
            audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
            if len(audio_data) > 0:
                sd.play(audio_data, samplerate=24000)
                sd.wait()
                print("✅")
            else:
                print("(no audio data)")
        except:
            print("(playback not available)")
    
    async def run_conversation_loop(self):
        """Main conversation loop"""
        print("\n" + "="*70)
        print("💬 READY - Press Enter to record or type 'quit' to exit")
        print("="*70)
        
        while True:
            try:
                user_input = input("\n🎤 Press Enter to start recording: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("👋 Goodbye!")
                break
            
            if user_input.lower().startswith('text '):
                # Text mode
                user_text = user_input[5:]
            else:
                # Record audio
                audio, sr = self.record_speech(5)
                if audio is None:
                    continue
                
                user_text = await self.transcribe(audio, sr)
                if not user_text:
                    continue
            
            # Get LLM response
            response = await self.get_response(user_text)
            if not response:
                continue
            
            # Generate speech
            audio_bytes = await self.synthesize(response)
            if audio_bytes:
                self.play_audio(audio_bytes)

async def main():
    agent = SpeechToSpeechAgent()
    await agent.run_conversation_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
