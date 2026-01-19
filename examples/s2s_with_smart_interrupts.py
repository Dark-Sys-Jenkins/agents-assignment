#!/usr/bin/env python3
"""
Speech-to-Speech Agent with Intelligent Interruption Handling
Integrates dual-layer validation with the S2S agent
"""

import asyncio
import os
import sys
import numpy as np
import httpx
import io
from dotenv import load_dotenv

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
        interrupt_config = InterruptConfig(debug=True)
        self.interrupt_handler = DualLayerInterruptHandler(interrupt_config)
        
        # Setup interrupt callbacks
        self.is_interrupted = False
        self.interrupt_handler.on_interrupt = self._on_interrupt
        self.interrupt_handler.on_decision = self._on_decision
        
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
        print("\n   ⚠️  INTERRUPT EXECUTED - Stopping agent")
        self.is_interrupted = True
    
    async def _on_decision(self, action: InterruptAction, reason: str):
        """Callback when interrupt decision is made"""
        emoji = "✅" if action == InterruptAction.IGNORE else "⚠️ "
        print(f"   {emoji} Decision: {action.value} ({reason})")
    
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
    
    def play(self, audio_bytes):
        """Play audio"""
        if not audio_bytes:
            return
        
        try:
            # Update agent state - now PLAYING
            self.interrupt_handler.set_agent_state(AgentState.PLAYING)
            
            print("▶️  Playing... ", end='', flush=True)
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(audio) > 0:
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
    
    async def handle_vad_trigger(self):
        """Handle VAD (Voice Activity Detection) trigger"""
        # Layer 1: Check agent state immediately
        should_process_now = await self.interrupt_handler.on_vad_trigger()
        return should_process_now
    
    async def handle_stt_completion(self, text: str):
        """Handle STT result - validate interrupt"""
        # Layer 2: Validate interrupt decision
        action = await self.interrupt_handler.on_stt_result(text)
        return action
    
    async def run(self):
        """Main loop"""
        print("="*70)
        print("💬 READY - Intelligent Interruption Handling Active")
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
                
                # Reset interrupt flag
                self.is_interrupted = False
                
                # Record
                audio, sr = self.record(5)
                if audio is None:
                    print()
                    continue
                
                # Update state - now LISTENING
                self.interrupt_handler.set_agent_state(AgentState.SILENT)
                
                # VAD LAYER 1: Check if we should process immediately
                should_process = await self.handle_vad_trigger()
                
                # Transcribe
                text = await self.transcribe(audio, sr)
                if not text:
                    print()
                    continue
                
                # STT LAYER 2: Validate the interrupt
                action = await self.handle_stt_completion(text)
                
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
                
                # TTS
                audio_bytes = await self.synthesize(response)
                if audio_bytes:
                    self.play(audio_bytes)
                
                # Back to SILENT
                self.interrupt_handler.set_agent_state(AgentState.SILENT)
                print()
        finally:
            await self.client.aclose()


async def main():
    agent = S2SAgentWithInterrupts()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
