#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speech-to-Speech Agent with Intelligent Interruption Handling
Working version with proper interrupt handling during playback
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

# Allow nested event loops
nest_asyncio.apply()

try:
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

# Import the interrupt handler
sys.path.insert(0, os.path.dirname(__file__))
from dual_layer_interrupt import (
    DualLayerInterruptHandler, 
    InterruptConfig, 
    AgentState,
    InterruptAction
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class S2SAgentWithInterrupts:
    """Speech-to-Speech agent with intelligent interruption handling"""
    
    def __init__(self):
        self.groq = os.getenv("GROQ_API_KEY")
        self.deepgram = os.getenv("DEEPGRAM_API_KEY")
        self.cartesia = os.getenv("CARTESIA_API_KEY")
        self.history = [{"role": "system", "content": "You are a helpful voice AI. Be concise."}]
        self.client = httpx.AsyncClient(timeout=30)
        
        # Initialize interrupt handler
        interrupt_config = InterruptConfig(debug=False)
        self.interrupt_handler = DualLayerInterruptHandler(interrupt_config)
        
        # Setup interrupt callbacks
        self.is_interrupted = False
        self.interrupt_handler.on_interrupt = self._on_interrupt
        self.interrupt_handler.on_decision = self._on_decision
        
        # Audio playback control
        self.playback_stream = None
        self.should_stop_playback = False
        self.recording_thread = None
        
        print("\n" + "="*70)
        print("🎙️  SPEECH-TO-SPEECH AI AGENT WITH INTELLIGENT INTERRUPTS")
        print("="*70)
        
        if not all([self.groq, self.deepgram, self.cartesia]):
            print("❌ Missing API keys!")
            sys.exit(1)
        
        if not AUDIO_OK:
            print("❌ sounddevice not installed!")
            sys.exit(1)
        
        print("✅ All systems ready")
        print("✅ Interrupt handler configured")
        print("\nFeatures:")
        print("  • Says 'yeah/ok/hmm' while I'm talking? I'll ignore it")
        print("  • Says 'stop/wait'? I'll interrupt immediately")
        print("  • Mixed input like 'yeah but wait'? I'll stop for 'wait'\n")
    
    async def _on_interrupt(self):
        """Callback when interrupt is executed"""
        print("\n   ⚠️  INTERRUPT EXECUTED - Stopping agent playback")
        self.should_stop_playback = True
        self.is_interrupted = True
    
    async def _on_decision(self, action: InterruptAction, reason: str):
        """Callback when interrupt decision is made"""
        if action == InterruptAction.IGNORE:
            print(f"   ✅ IGNORING backchannel: {reason}")
        elif action == InterruptAction.INTERRUPT:
            print(f"   ⚠️  INTERRUPTING: {reason}")
        elif action == InterruptAction.RESPOND:
            print(f"   📥 RESPONDING: {reason}")
    
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
    
    def record_with_interrupt(self, dur=5, sr=16000):
        """Record audio with interrupt monitoring"""
        print(f"🎤 Listening ({dur}s)... ", end='', flush=True)
        try:
            audio_data = []
            frames_per_buffer = int(sr * 0.1)  # 100ms chunks
            
            stream = sd.InputStream(
                channels=1,
                samplerate=sr,
                dtype=np.float32,
                blocksize=frames_per_buffer
            )
            
            stream.start()
            total_frames = int(dur * sr)
            recorded_frames = 0
            
            while recorded_frames < total_frames:
                frame, _ = stream.read(frames_per_buffer)
                audio_data.append(frame)
                recorded_frames += len(frame)
                
                # Check if we should stop recording due to interrupt
                if self.should_stop_playback:
                    break
            
            stream.stop()
            stream.close()
            
            if audio_data:
                audio = np.concatenate(audio_data)
                print("✅")
                return audio, sr
            return None, None
            
        except Exception as e:
            print(f"❌ {e}")
            return None, None
    
    async def transcribe(self, audio, sr):
        """Deepgram STT"""
        print("🎙️  Transcribing... ", end='', flush=True)
        try:
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
                print(f"✅")
                return text
            else:
                print(f"❌ {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            return None
    
    async def synthesize(self, text):
        """Cartesia TTS"""
        # Update agent state - now SPEAKING
        self.interrupt_handler.set_agent_state(AgentState.SPEAKING)
        
        print("🔊 Generating... ", end='', flush=True)
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
                return None
        except asyncio.TimeoutError:
            print("⏭️  timeout")
            return None
        except Exception as e:
            print(f"⏭️  {str(e)[:30]}")
            return None
    
    def play_with_listening(self, audio_bytes):
        """Play audio while listening for interruptions"""
        if not audio_bytes:
            return
        
        import threading
        
        try:
            self.interrupt_handler.set_agent_state(AgentState.PLAYING)
            self.should_stop_playback = False
            
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio.astype(np.float32) / 32768.0
            
            print("▶️  Playing (listening for interrupts)... ", end='', flush=True)
            
            # Start recording in background thread
            recording_data = []
            recording_active = [True]
            
            def record_background():
                """Record audio in background while agent plays"""
                try:
                    chunk_size = 4800  # 100ms at 16kHz
                    stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1600)
                    stream.start()
                    
                    while recording_active[0] and not self.should_stop_playback:
                        frame, _ = stream.read(1600)
                        recording_data.append(frame.copy())
                        
                        # Process every 500ms of recording
                        if len(recording_data) >= 8:  # 8 frames = ~500ms
                            combined = np.concatenate(recording_data[-8:])
                            # Quick check for voice activity
                            volume = np.abs(combined).mean()
                            if volume > 0.03:  # Threshold for speech
                                asyncio.run_coroutine_threadsafe(
                                    self._check_interrupt(combined),
                                    asyncio.get_event_loop()
                                )
                    
                    stream.stop()
                    stream.close()
                except Exception as e:
                    pass
            
            # Start recording thread
            record_thread = threading.Thread(target=record_background, daemon=True)
            record_thread.start()
            
            # Play audio in chunks
            chunk_size = 4800  # 200ms at 24kHz
            playback_stream = sd.OutputStream(channels=1, samplerate=24000)
            playback_stream.start()
            
            for i in range(0, len(audio_float), chunk_size):
                if self.should_stop_playback:
                    print("\n   🛑 Interrupted by user!")
                    break
                
                chunk = audio_float[i:i + chunk_size]
                playback_stream.write(chunk)
            
            playback_stream.stop()
            playback_stream.close()
            
            recording_active[0] = False
            record_thread.join(timeout=1)
            
            print("✅")
            
        except Exception as e:
            print(f"(error: {str(e)[:20]})")
        finally:
            self.interrupt_handler.set_agent_state(AgentState.SILENT)
    
    async def _check_interrupt(self, audio_chunk):
        """Check if audio chunk contains interrupt keywords"""
        try:
            # Convert audio to transcription
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
            wav_data = self._create_wav(audio_int16, 16000)
            
            resp = await self.client.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2",
                headers={"Authorization": f"Token {self.deepgram}"},
                content=wav_data,
                timeout=5
            )
            
            if resp.status_code == 200:
                transcript = resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
                
                # Check for interrupt keywords
                force_keywords = ['stop', 'wait', 'hold', 'pause', 'no', 'quit', 'cancel', 'halt']
                if any(kw in transcript.lower() for kw in force_keywords):
                    await self._on_interrupt()
                    
        except Exception:
            pass
    
    def play(self, audio_bytes):
        """Play audio with interrupt monitoring - wrapper"""
        self.play_with_listening(audio_bytes)
    
    def _create_wav(self, audio_data, sr):
        """Create WAV file from audio data"""
        num_channels = 1
        bytes_per_sample = 2
        byte_rate = sr * num_channels * bytes_per_sample
        block_align = num_channels * bytes_per_sample
        
        wav_data = io.BytesIO()
        wav_data.write(b'RIFF')
        wav_data.write(b'\x00\x00\x00\x00')
        wav_data.write(b'WAVE')
        
        wav_data.write(b'fmt ')
        wav_data.write((16).to_bytes(4, 'little'))
        wav_data.write((1).to_bytes(2, 'little'))
        wav_data.write((num_channels).to_bytes(2, 'little'))
        wav_data.write((sr).to_bytes(4, 'little'))
        wav_data.write((byte_rate).to_bytes(4, 'little'))
        wav_data.write((block_align).to_bytes(2, 'little'))
        wav_data.write((16).to_bytes(2, 'little'))
        
        wav_data.write(b'data')
        wav_data.write((len(audio_data) * bytes_per_sample).to_bytes(4, 'little'))
        wav_data.write(audio_data.tobytes())
        
        file_size = wav_data.tell() - 8
        wav_data.seek(4)
        wav_data.write(file_size.to_bytes(4, 'little'))
        
        return wav_data.getvalue()
    
    async def run(self):
        """Main loop"""
        print("="*70)
        print("💬 READY - Intelligent Interruption Handling Active")
        print("  Press Enter → Record & process")
        print("  Speak 'stop/wait' while agent talks → Interrupt playback")
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
                
                # Reset interrupt flag
                self.is_interrupted = False
                self.should_stop_playback = False
                
                # Record (with interrupt monitoring)
                audio, sr = self.record(5)
                if audio is None:
                    print()
                    continue
                
                # Update state - now LISTENING
                self.interrupt_handler.set_agent_state(AgentState.SILENT)
                
                # VAD LAYER 1: Check if we should process immediately
                should_process = await self.interrupt_handler.on_vad_trigger()
                
                # Transcribe
                text = await self.transcribe(audio, sr)
                if not text:
                    print()
                    continue
                
                # STT LAYER 2: Validate the interrupt
                action = await self.interrupt_handler.on_stt_result(text)
                
                # If interrupted while agent was speaking, skip LLM call
                if action == InterruptAction.IGNORE:
                    print("  (Bacchanneling ignored, agent continues)")
                    print()
                    continue
                
                print(f"  You: {text}")
                
                # LLM
                response = await self.get_response(text)
                if not response:
                    print()
                    continue
                
                print(f"  Agent: {response}")
                
                # TTS + Play with interrupt handling
                audio_bytes = await self.synthesize(response)
                if audio_bytes:
                    self.play(audio_bytes)
                
                # Back to SILENT
                self.interrupt_handler.set_agent_state(AgentState.SILENT)
                
                if self.is_interrupted:
                    print("\n  [Agent interrupted - ready for next input]\n")
                else:
                    print()
                    
        finally:
            await self.client.aclose()


async def main():
    agent = S2SAgentWithInterrupts()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
