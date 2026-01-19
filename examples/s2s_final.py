#!/usr/bin/env python3
"""
COMPLETE WORKING SPEECH-TO-SPEECH AGENT
Microphone → Deepgram STT → Groq LLM → Cartesia TTS → Speaker
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import httpx
import numpy as np
import io

try:
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class S2SAgent:
    def __init__(self):
        self.groq = os.getenv("GROQ_API_KEY")
        self.deepgram = os.getenv("DEEPGRAM_API_KEY")
        self.cartesia = os.getenv("CARTESIA_API_KEY")
        self.history = [{"role": "system", "content": "You are a helpful voice AI. Be concise."}]
        self.client = httpx.AsyncClient(timeout=30)  # Persistent client
        
        print("\n" + "="*70)
        print("🎙️  SPEECH-TO-SPEECH AI AGENT")
        print("="*70)
        
        if not all([self.groq, self.deepgram, self.cartesia]):
            print("❌ Missing API keys!")
            sys.exit(1)
        
        if not AUDIO_OK:
            print("❌ sounddevice not installed!")
            sys.exit(1)
        
        print("✅ All systems ready\n")
    
    def record(self, dur=5, sr=16000):
        """Record audio from microphone"""
        print(f"🎤 Recording {dur}s... ", end='', flush=True)
        try:
            audio = sd.rec(int(dur * sr), sr, 1, np.float32)
            sd.wait()
            print("✅")
            return audio.flatten(), sr
        except Exception as e:
            print(f"❌ {e}")
            return None, None
    
    async def transcribe(self, audio, sr):
        """Deepgram STT"""
        print("🎙️  Transcribing... ", end='', flush=True)
        try:
            # Normalize audio
            audio = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio * 32767).astype(np.int16)
            wav_data = self._create_wav(audio_int16, sr)
            
            resp = await self.client.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2",
                headers={"Authorization": f"Token {self.deepgram}"},
                content=wav_data
            )
            
            if resp.status_code == 200:
                text = resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
                print(f"✅ '{text}'")
                return text
            else:
                print(f"❌ {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            return None
    
    async def get_response(self, user_text):
        """Groq LLM"""
        print("🧠 Thinking... ", end='', flush=True)
        try:
            self.history.append({"role": "user", "content": user_text})
            
            resp = await self.client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": self.history,
                    "max_tokens": 150
                }
            )
            
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                self.history.append({"role": "assistant", "content": text})
                print(f"✅ '{text}'")
                return text
            else:
                print(f"❌ {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            return None
    
    async def synthesize(self, text):
        """Cartesia TTS - Fixed with correct endpoint and headers"""
        print("🔊 Generating... ", end='', flush=True)
        try:
            # Cartesia requires Cartesia-Version header
            resp = await self.client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "X-API-Key": self.cartesia,
                    "Cartesia-Version": "2024-06-10",
                    "Content-Type": "application/json"
                },
                json={
                    "transcript": text,
                    "model_id": "sonic-english",
                    "voice": {
                        "mode": "id",
                        "id": "638efaaa-4d0c-442e-b701-3fae16aad012"
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000
                    }
                },
                timeout=15
            )
            
            if resp.status_code == 200:
                print(f"✅ ({len(resp.content)} bytes)")
                return resp.content
            else:
                print(f"⏭️  {resp.status_code}")
                # Log error details for debugging
                try:
                    err_text = resp.text[:80]
                    if err_text:
                        print(f"  Error: {err_text}")
                except:
                    pass
                return None
        except asyncio.TimeoutError:
            print("⏭️  timeout")
            return None
        except Exception as e:
            print(f"⏭️  {str(e)[:30]}")
            return None
    
    def play(self, audio_bytes):
        """Play audio"""
        if not audio_bytes:
            return
        
        try:
            print("▶️  Playing... ", end='', flush=True)
            # Cartesia returns PCM s16le at 24kHz
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(audio) > 0:
                # Normalize to float for playback
                audio_float = audio.astype(np.float32) / 32768.0
                sd.play(audio_float, 24000)
                sd.wait()
                print("✅")
            else:
                print("(empty)")
        except Exception as e:
            print(f"(error: {str(e)[:20]})")
    
    def _create_wav(self, audio_data, sr):
        """Create WAV file from audio data"""
        buf = io.BytesIO()
        
        # WAV header
        num_channels = 1
        bytes_per_sample = 2
        byte_rate = sr * num_channels * bytes_per_sample
        block_align = num_channels * bytes_per_sample
        
        # Create WAV file manually
        wav_data = io.BytesIO()
        wav_data.write(b'RIFF')
        wav_data.write(b'\x00\x00\x00\x00')  # Size (will update)
        wav_data.write(b'WAVE')
        
        # fmt subchunk
        wav_data.write(b'fmt ')
        wav_data.write((16).to_bytes(4, 'little'))
        wav_data.write((1).to_bytes(2, 'little'))  # PCM
        wav_data.write((num_channels).to_bytes(2, 'little'))
        wav_data.write((sr).to_bytes(4, 'little'))
        wav_data.write((byte_rate).to_bytes(4, 'little'))
        wav_data.write((block_align).to_bytes(2, 'little'))
        wav_data.write((16).to_bytes(2, 'little'))  # bits per sample
        
        # data subchunk
        wav_data.write(b'data')
        audio_bytes = audio_data.tobytes()
        wav_data.write(len(audio_bytes).to_bytes(4, 'little'))
        wav_data.write(audio_bytes)
        
        # Update RIFF size
        file_size = wav_data.tell() - 8
        wav_data.seek(4)
        wav_data.write(file_size.to_bytes(4, 'little'))
        
        return wav_data.getvalue()
    
    async def run(self):
        """Main loop"""
        print("="*70)
        print("💬 READY")
        print("  Press Enter → Record & process")
        print("  Type 'quit' → Exit")
        print("="*70 + "\n")
        
        try:
            while True:
                try:
                    inp = input("🎤 Press Enter to record: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Bye!")
                    break
                
                if inp in ('quit', 'exit', 'q'):
                    print("👋 Bye!")
                    break
                
                # Record
                audio, sr = self.record(5)
                if audio is None:
                    print()
                    continue
                
                # Transcribe
                text = await self.transcribe(audio, sr)
                if not text:
                    print()
                    continue
                print(f"  You: {text}")
                
                # LLM
                response = await self.get_response(text)
                if not response:
                    print()
                    continue
                print(f"  Agent: {response}")
                
                # TTS
                audio_bytes = await self.synthesize(response)
                if audio_bytes:
                    self.play(audio_bytes)
                
                print()
        finally:
            await self.client.aclose()

async def main():
    agent = S2SAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
