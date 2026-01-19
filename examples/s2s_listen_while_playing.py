#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S2S Agent Interactive Demo - Listen While Playing
Shows agent detecting interruptions in real-time while speaking
"""

import asyncio
import os
import sys
import numpy as np
import httpx
import io
import threading
import nest_asyncio
from dotenv import load_dotenv

nest_asyncio.apply()

try:
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

sys.path.insert(0, os.path.dirname(__file__))
from dual_layer_interrupt import (
    DualLayerInterruptHandler, 
    InterruptConfig, 
    AgentState,
    InterruptAction
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class S2SInteractiveDemo:
    """S2S Agent that listens while playing"""
    
    def __init__(self):
        self.groq = os.getenv("GROQ_API_KEY")
        self.deepgram = os.getenv("DEEPGRAM_API_KEY")
        self.cartesia = os.getenv("CARTESIA_API_KEY")
        self.history = [{"role": "system", "content": "You are a helpful voice AI. Keep responses short and concise - 1-2 sentences max."}]
        self.client = httpx.AsyncClient(timeout=30)
        
        # Interrupt handler
        config = InterruptConfig(debug=False)
        self.handler = DualLayerInterruptHandler(config)
        self.handler.on_interrupt = self._on_interrupt
        
        self.playback_stopped = False
        self.loop = asyncio.get_event_loop()
        
        print("\n" + "="*80)
        print("🎤 S2S AGENT - REAL-TIME INTERRUPT LISTENING DEMO")
        print("="*80)
        print("\n✅ Features:")
        print("   • Agent listens WHILE PLAYING audio")
        print("   • Detects 'stop', 'wait', 'pause' in real-time")
        print("   • Ignores backchannel like 'yeah', 'ok'")
        print("   • Stops playback immediately on command\n")
        print("="*80 + "\n")
    
    async def _on_interrupt(self):
        print("\n   🛑 INTERRUPT DETECTED! Stopping playback...")
        self.playback_stopped = True
    
    def record_audio(self, duration=5):
        """Record user input"""
        print(f"🎤 Recording ({duration}s)... ", end='', flush=True)
        try:
            audio = sd.rec(int(duration * 16000), 16000, 1, np.float32)
            sd.wait()
            print("✅")
            return audio.flatten(), 16000
        except Exception as e:
            print(f"❌")
            return None, None
    
    async def transcribe(self, audio, sr):
        """STT via Deepgram"""
        print("📝 Transcribing... ", end='', flush=True)
        try:
            audio_clipped = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio_clipped * 32767).astype(np.int16)
            wav_data = self._make_wav(audio_int16, sr)
            
            resp = await self.client.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2",
                headers={"Authorization": f"Token {self.deepgram}"},
                content=wav_data
            )
            
            if resp.status_code == 200:
                text = resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
                print(f"✅ '{text}'")
                return text
            return None
        except Exception as e:
            print(f"❌")
            return None
    
    async def get_response(self, text):
        """LLM response via Groq"""
        print("💭 Thinking... ", end='', flush=True)
        try:
            self.history.append({"role": "user", "content": text})
            
            resp = await self.client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": self.history,
                    "max_tokens": 100
                }
            )
            
            if resp.status_code == 200:
                response = resp.json()["choices"][0]["message"]["content"]
                self.history.append({"role": "assistant", "content": response})
                print("✅")
                return response
            return None
        except Exception as e:
            print(f"❌")
            return None
    
    async def synthesize(self, text):
        """TTS via Cartesia"""
        print("🔊 Generating audio... ", end='', flush=True)
        try:
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
                    "voice": {"mode": "id", "id": "638efaaa-4d0c-442e-b701-3fae16aad012"},
                    "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000}
                },
                timeout=15
            )
            
            if resp.status_code == 200:
                print(f"✅")
                return resp.content
            return None
        except Exception as e:
            print(f"❌")
            return None
    
    def play_with_listening(self, audio_bytes):
        """Play audio while listening for interrupts"""
        if not audio_bytes:
            return
        
        try:
            self.handler.set_agent_state(AgentState.PLAYING)
            self.playback_stopped = False
            
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio.astype(np.float32) / 32768.0
            
            print("▶️  Playing (LISTENING for interrupts)... ", end='', flush=True)
            
            recording_active = [True]
            
            def record_background():
                """Record while playing"""
                try:
                    rec_data = []
                    stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1600)
                    stream.start()
                    
                    while recording_active[0] and not self.playback_stopped:
                        frame, _ = stream.read(1600)
                        rec_data.append(frame.copy())
                        
                        # Check every 500ms
                        if len(rec_data) >= 5:
                            combined = np.concatenate(rec_data[-5:])
                            volume = np.abs(combined).mean()
                            
                            if volume > 0.05:  # Speech threshold
                                # Send to STT
                                self._check_interrupt_sync(combined)
                    
                    stream.stop()
                    stream.close()
                except Exception as e:
                    pass
            
            # Start background recording
            record_thread = threading.Thread(target=record_background, daemon=True)
            record_thread.start()
            
            # Play audio
            chunk_size = 4800  # 200ms at 24kHz
            stream = sd.OutputStream(channels=1, samplerate=24000)
            stream.start()
            
            for i in range(0, len(audio_float), chunk_size):
                if self.playback_stopped:
                    break
                chunk = audio_float[i:i + chunk_size]
                stream.write(chunk)
            
            stream.stop()
            stream.close()
            
            recording_active[0] = False
            record_thread.join(timeout=1)
            
            print("Done!")
            
        except Exception as e:
            print(f" (error: {str(e)[:20]})")
        finally:
            self.handler.set_agent_state(AgentState.SILENT)
    
    def _check_interrupt_sync(self, audio_chunk):
        """Check for interrupts (sync wrapper for async)"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._check_interrupt(audio_chunk),
                self.loop
            )
        except:
            pass
    
    async def _check_interrupt(self, audio_chunk):
        """Analyze audio for interrupt keywords"""
        try:
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
            wav_data = self._make_wav(audio_int16, 16000)
            
            resp = await self.client.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2",
                headers={"Authorization": f"Token {self.deepgram}"},
                content=wav_data,
                timeout=3
            )
            
            if resp.status_code == 200:
                transcript = resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"].lower()
                
                # Force interrupt keywords
                force_keywords = ['stop', 'wait', 'hold', 'pause', 'halt', 'quit', 'cancel']
                if any(kw in transcript for kw in force_keywords):
                    await self._on_interrupt()
                    
        except Exception:
            pass
    
    def _make_wav(self, audio_data, sr):
        """Create WAV format"""
        wav = io.BytesIO()
        wav.write(b'RIFF')
        wav.write(b'\x00\x00\x00\x00')
        wav.write(b'WAVE')
        wav.write(b'fmt ')
        wav.write((16).to_bytes(4, 'little'))
        wav.write((1).to_bytes(2, 'little'))
        wav.write((1).to_bytes(2, 'little'))
        wav.write(sr.to_bytes(4, 'little'))
        wav.write((sr * 2).to_bytes(4, 'little'))
        wav.write((2).to_bytes(2, 'little'))
        wav.write((16).to_bytes(2, 'little'))
        wav.write(b'data')
        wav.write((len(audio_data) * 2).to_bytes(4, 'little'))
        wav.write(audio_data.tobytes())
        
        size = wav.tell() - 8
        wav.seek(4)
        wav.write(size.to_bytes(4, 'little'))
        return wav.getvalue()
    
    async def run(self):
        """Main interaction loop"""
        print("Try these commands while agent is speaking:")
        print("  'stop', 'wait', 'pause' → Agent stops immediately")
        print("  'yeah', 'ok' → Agent ignores and continues")
        print("  Ctrl+C → Exit\n")
        print("─" * 80 + "\n")
        
        try:
            while True:
                # Record user input
                audio, sr = self.record_audio(5)
                if audio is None or len(audio) < 100:
                    print("(No audio)")
                    continue
                
                self.handler.set_agent_state(AgentState.SILENT)
                
                # Transcribe
                text = await self.transcribe(audio, sr)
                if not text:
                    continue
                
                print(f"You: '{text}'\n")
                
                # Check if interrupt should apply
                await self.handler.on_vad_trigger()
                action = await self.handler.on_stt_result(text)
                
                if action == InterruptAction.IGNORE:
                    print("✅ [Bacchanneling - ignoring]\n")
                    continue
                
                # Get response
                response = await self.get_response(text)
                if not response:
                    continue
                
                print(f"Agent: '{response}'\n")
                
                # Synthesize
                audio_bytes = await self.synthesize(response)
                if audio_bytes:
                    self.play_with_listening(audio_bytes)
                    
                    if self.playback_stopped:
                        print("⚠️  Playback stopped by interrupt!\n")
                
                print("\n" + "─" * 80 + "\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
        finally:
            await self.client.aclose()


async def main():
    demo = S2SInteractiveDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
