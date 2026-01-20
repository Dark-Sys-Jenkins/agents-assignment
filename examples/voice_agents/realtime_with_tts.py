"""
Voice Agent with Proper Backchannel Filtering
- Soft words NEVER interrupt (prevented, not resumed)
- Hard words (pause/stop) ALWAYS interrupt immediately and pause conversation
- Continue provides semantic continuation
- Stop/Pause immediately acknowledge with "I have paused"/"I have stopped"
"""
import logging
import re
import asyncio
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    StopResponse,
    cli,
)
from livekit.agents.voice import SpeechHandle, SpeechCreatedEvent
from livekit.plugins import deepgram, google, silero

load_dotenv()

from interruption_handler import InterruptionFilter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("backchannel-agent")

class BackchannelAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful AI assistant. Give detailed, engaging responses."
        )
        self.filter = InterruptionFilter()
        self._last_user_text = ""
        self._is_speaking = False
        self._paused = False
        self._stop_requested = False

    async def on_enter(self):
        log.info("=" * 80)
        log.info(" Agent Ready - Backchannel Filtering Active")
        log.info(f"Soft Words (will be IGNORED when agent is speaking):")
        log.info(f"  {sorted(self.filter.soft_words)}")
        log.info(f"Hard Words (will PAUSE conversation):")
        log.info(f"  {sorted(self.filter.hard_words)}")
        log.info("=" * 80)
        
        @self.session.on("speech_created")
        def on_speech(ev: SpeechCreatedEvent):
            self._is_speaking = True
            log.info(" AGENT STARTED SPEAKING")
            self._wrap_speech_handle(ev.speech_handle)
        
        @self.session.on("user_input_transcribed")
        def on_transcript(ev):
            if ev.is_final:
                self._last_user_text = ev.transcript
                log.info(f" User: {ev.transcript}")

    async def on_user_turn_completed(self, chat_ctx, new_message):
        text = new_message.text_content.lower() if new_message else ""
        cleaned = re.sub(r'[^\w\s]', '', text).strip()
        tokens = cleaned.split()
        
        log.info("-" * 80)
        log.info(f" USER TURN COMPLETED: '{text}'")
        log.info(f"   Cleaned: '{cleaned}'")
        log.info(f"   Tokens: {tokens}")
        log.info(f"   Agent speaking: {self._is_speaking}")
        log.info(f"   Paused: {self._paused}")
        log.info(f"   Stop requested: {self._stop_requested}")
        
        # 1. Continue command - exits paused state
        if any(word in cleaned for word in ["continue", "resume", "go on", "keep going"]):
            if self._paused:
                log.info(" CONTINUE detected - exiting paused state")
                self._paused = False
                self._stop_requested = False
                
                await self.session.generate_reply(
                    instructions=(
                        "Continue your previous response naturally from where you were interrupted. "
                        "Do not repeat earlier content."
                    )
                )
                log.info("-" * 80)
                raise StopResponse()
            else:
                # Not paused, treat as normal input
                log.info(" CONTINUE detected but not paused - treating as normal input")
                log.info("-" * 80)
                return

        # 2. Check for explicit STOP command
        if any(word in cleaned for word in ["stop", "enough", "shut up"]):
            if self._is_speaking:
                log.error(" STOP COMMAND - Agent will stop completely")
                self._paused = True
                self._stop_requested = True
                # The interrupt will happen via speech handle wrapper
                # Acknowledgment will be generated there
                log.info("-" * 80)
                raise StopResponse()
            else:
                log.info(" STOP command but not speaking - ignoring")
                log.info("-" * 80)
                raise StopResponse()

        # 3. Check for explicit PAUSE/WAIT command
        if any(word in tokens for word in ["pause", "wait", "hold"]):
            if self._is_speaking:
                log.warning("⏸ PAUSE COMMAND - Agent will pause")
                self._paused = True
                self._stop_requested = False
                # The interrupt will happen via speech handle wrapper
                # Acknowledgment will be generated there
                log.info("-" * 80)
                raise StopResponse()
            else:
                log.info("⏸ PAUSE command but not speaking - ignoring")
                log.info("-" * 80)
                raise StopResponse()

        # 4. If paused, check if this is a new meaningful command
        if self._paused:
            # Ignore repeated hard words while paused
            if any(word in tokens for word in self.filter.hard_words):
                log.info(f"⏸ STILL PAUSED (hard word repeated): {cleaned}")
                log.info("-" * 80)
                raise StopResponse()

            # Ignore soft fillers while paused
            if tokens and all(t in self.filter.soft_words for t in tokens):
                log.info(f"⏸ PAUSED + SOFT WORD: Ignoring '{cleaned}'")
                log.info("-" * 80)
                raise StopResponse()

            # NEW REQUEST while paused - reset context and respond fresh
            log.info(f" NEW REQUEST (unpausing + clearing context): {cleaned}")
            self._paused = False
            self._stop_requested = False
            
            # Clear conversation history to prevent old context from leaking
            self.session.history.items.clear()
            log.info(" Conversation history cleared")
            
            # Generate fresh response to the new question only
            await self.session.generate_reply(user_input=text)
            log.info("-" * 80)
            raise StopResponse()

        # 5. Soft words while speaking → ignore completely
        if self._is_speaking and self.filter.should_ignore(cleaned, is_agent_speaking=True):
            log.info(f" SOFT INTERRUPTION IGNORED: {cleaned}")
            log.info("-" * 80)
            raise StopResponse()

        # 6. Hard words while speaking → pause conversation
        if self._is_speaking and not self.filter.should_ignore(cleaned, is_agent_speaking=True):
            log.warning(f"⏸ HARD INTERRUPT: {cleaned} - entering paused state")
            self._paused = True
            self._stop_requested = False
            log.info("-" * 80)
            raise StopResponse()

        # 7. Normal processing
        log.info(f" PROCESSING NORMALLY: {cleaned}")
        log.info("-" * 80)

    def _wrap_speech_handle(self, handle: SpeechHandle):
        """Wrap interrupt to filter soft words and handle pause/stop acknowledgments"""
        original_interrupt = handle.interrupt
        
        async def filtered_interrupt(**kwargs):
            cleaned = re.sub(r'[^\w\s]', '', self._last_user_text).strip().lower()
            tokens = cleaned.split()
            
            # Check if we should ignore this interrupt (soft words only)
            if self.filter.should_ignore(cleaned, is_agent_speaking=True):
                log.info(f" BLOCKED interrupt for soft words: {self._last_user_text}")
                return  # Block the interrupt completely
            
            # Check for STOP command
            is_stop = any(word in tokens for word in ["stop", "enough", "shut"])
            # Check for PAUSE command
            is_pause = any(word in tokens for word in ["pause", "wait", "hold"])
            
            log.error(f" ALLOWING interrupt for: {self._last_user_text}")
            self._paused = True  #  CRITICAL: Set paused state
            
            # Interrupt first
            await original_interrupt(**kwargs)
            
            # Then generate acknowledgment
            if is_stop:
                log.error(" Generating STOP acknowledgment")
                async def say_stopped():
                    await self.session.generate_reply(
                        instructions="Say only 'I have stopped' in a brief, natural voice."
                    )
                asyncio.create_task(say_stopped())
            elif is_pause:
                log.warning("⏸ Generating PAUSE acknowledgment")
                async def say_paused():
                    await self.session.generate_reply(
                        instructions="Say only 'I have paused' in a brief, natural voice."
                    )
                asyncio.create_task(say_paused())
        
        handle.interrupt = filtered_interrupt
        
        # Track when speech ends
        async def monitor():
            try:
                await handle.wait_for_playout()
                log.info(" AGENT AUDIO COMPLETED")
            except Exception as e:
                log.info(f" AGENT AUDIO INTERRUPTED: {e}")
            finally:
                self._is_speaking = False
        
        asyncio.create_task(monitor())

app = AgentServer()

@app.rtc_session()
async def main(ctx: JobContext):
    log.info("=" * 80)
    log.info(f" NEW SESSION STARTING")
    log.info(f"   Room: {ctx.room.name}")
    log.info(f"   Pipeline: Deepgram STT → Google Gemini LLM → Deepgram TTS")
    log.info("=" * 80)
    
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-2",
            language="en",
            smart_format=True,
            interim_results=False,
        ),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=deepgram.TTS(
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=24000,
        ),
        vad=silero.VAD.load(
            min_speech_duration=0.5,
            min_silence_duration=0.9,
            activation_threshold=0.7,
            max_buffered_speech=60.0,
        ),
        allow_interruptions=True,
    )
    
    log.info("Session configured successfully")
    
    await session.start(agent=BackchannelAgent(), room=ctx.room)
    
    log.info(" Agent started - Ready for conversation")
    
    await session.generate_reply(
        instructions="Greet the user warmly and invite them to ask for a long, detailed story to test the backchannel features."
    )

if __name__ == "__main__":
    cli.run_app(app)
