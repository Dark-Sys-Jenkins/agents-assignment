"""
Voice Agent with Proper Backchannel Filtering
- Soft words NEVER interrupt (prevented, not resumed)
- Hard words ALWAYS interrupt immediately and pause conversation
- Continue provides semantic continuation
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
            instructions="""You are a real-time voice assistant with strict interruption semantics.

CONTINUE BEHAVIOR:
- Resume ONLY if there is a paused response.
- Continue exactly from where you stopped.
- Do NOT restart, summarize, or generate new ideas.
- If nothing is paused, say NOTHING.

NEW QUESTION AFTER STOP:
- Respond ONLY to the new question.
- Never mix old and new content."""
        )
        self.filter = InterruptionFilter()
        self._last_user_text = ""
        self._is_speaking = False
        self._paused = False
        self._has_paused_content = False  # Track if there's actually content to resume

    async def on_enter(self):
        log.info("Agent ready - backchannel filtering active")
        
        @self.session.on("speech_created")
        def on_speech(ev: SpeechCreatedEvent):
            self._is_speaking = True
            self._has_paused_content = False  # New speech = no paused content
            self._wrap_speech_handle(ev.speech_handle)
        
        @self.session.on("user_input_transcribed")
        def on_transcript(ev):
            if ev.is_final:
                self._last_user_text = ev.transcript
                log.info(f"User: {ev.transcript}")

    async def on_user_turn_completed(self, chat_ctx, new_message):
        text = new_message.text_content.lower() if new_message else ""
        cleaned = re.sub(r'[^\w\s]', '', text).strip()
        
        # 1. Continue command - ONLY resume if there's paused content
        if any(word in cleaned for word in ["continue", "resume", "go on", "keep going"]):
            if self._paused and self._has_paused_content:
                log.info("CONTINUE detected - resuming paused content")
                self._paused = False
                self._has_paused_content = False
                
                await self.session.generate_reply(
                    instructions=(
                        "Continue your previous response naturally from where you were interrupted. "
                        "Do not repeat earlier content. Do not start a new topic."
                    )
                )
                raise StopResponse()
            else:
                # Nothing to continue - stay silent
                log.info("CONTINUE detected but nothing to resume - staying silent")
                raise StopResponse()

        # 2. If paused, check if this is a new meaningful command
        if self._paused:
            # Ignore ALL hard interrupt words while paused
            if cleaned in self.filter.hard_words:
                log.info(f"Still paused (hard word repeated): {cleaned}")
                raise StopResponse()

            # Ignore soft fillers while paused (check tokens directly)
            tokens = cleaned.split()
            if tokens and all(t in self.filter.soft_words for t in tokens):
                log.info(f"Paused + soft word: ignoring '{cleaned}'")
                raise StopResponse()

            # NEW REQUEST while paused - ABORT paused content and respond fresh
            log.info(f"New request (aborting paused content + clearing context): {cleaned}")
            self._paused = False
            self._has_paused_content = False  # Permanently discard paused content
            
            # Clear conversation history to prevent old context from leaking
            self.session.history.items.clear()
            log.info("Conversation history cleared")
            
            # Generate fresh response to the new question only
            await self.session.generate_reply(user_input=text)
            raise StopResponse()


        # 3. Soft words while speaking → ignore completely
        if self._is_speaking and self.filter.should_ignore(cleaned, is_agent_speaking=True):
            log.info(f"Soft word ignored: {cleaned}")
            raise StopResponse()

        # 4. Hard words while speaking → pause conversation
        if self._is_speaking and not self.filter.should_ignore(cleaned, is_agent_speaking=True):
            log.warning(f"Hard interrupt: {cleaned} - entering paused state")
            self._paused = True
            raise StopResponse()

        # 5. Normal processing
        log.info(f"Processing user input: {cleaned}")

    def _wrap_speech_handle(self, handle: SpeechHandle):
        """Wrap interrupt to filter soft words immediately"""
        original_interrupt = handle.interrupt
        
        async def filtered_interrupt(**kwargs):
            # Check if we should ignore this interrupt
            if self.filter.should_ignore(self._last_user_text, is_agent_speaking=True):
                log.info(f"Blocked interrupt for: {self._last_user_text}")
                return  # Block the interrupt completely
            
            log.info(f"Allowing interrupt for: {self._last_user_text}")
            self._paused = True
            self._has_paused_content = True  # Mark that there's content to resume
            await original_interrupt(**kwargs)
        
        handle.interrupt = filtered_interrupt
        
        # Track when speech ends
        async def monitor():
            try:
                await handle.wait_for_playout()
            finally:
                self._is_speaking = False
        
        asyncio.create_task(monitor())

app = AgentServer()

@app.rtc_session()
async def main(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-2", interim_results=False),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=deepgram.TTS(model="aura-asteria-en", sample_rate=24000),
        vad=silero.VAD.load(
            min_speech_duration=0.3,
            min_silence_duration=0.6,
            activation_threshold=0.5
        ),
        allow_interruptions=True,
    )
    
    await session.start(agent=BackchannelAgent(), room=ctx.room)
    await session.generate_reply(instructions="Greet the user warmly.")

if __name__ == "__main__":
    cli.run_app(app)
