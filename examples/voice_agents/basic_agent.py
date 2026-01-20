import logging
import asyncio
import string
from typing import AsyncIterable, Optional
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    AgentStateChangedEvent,
    cli,
    metrics,
    room_io,
    RunContext,
)
from livekit import rtc
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import stt

logger = logging.getLogger("intelligent-agent")
logger.setLevel(logging.INFO)

load_dotenv()

# --- CONFIGURATION ---
# Backchannel words to IGNORE when agent is speaking
# Include all variations (with hyphens, without hyphens, as separate words)
IGNORE_WORDS = {
    "yeah", "yep", "yes", 
    "uh-huh", "uhhuh", "uh", "huh",  # All variations of "uh-huh"
    "hmm", "hmmm", "mm", "mmm", "mhm",
    "ok", "okay", "k",
    "right", "alright", 
    "sure", 
    "got", "it", "gotit",  # "got it" variations
    "i", "see",  # "I see" as separate words
    "ah", "oh", "ooh",
    "cool", "nice", "good",
    "mhmm", "mmhmm", "aha", "ahh"
}

# Command words that ALWAYS trigger interruption
STOP_WORDS = {
    "stop", "wait", "cancel", "hold", "no", "pause", "question", "but"
}


class IntelligentAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep your responses concise and conversational. "
                "When counting, count slowly and clearly."
            )
        )
        self.is_speaking = False

    async def on_enter(self):
        # Start with a test scenario
        await asyncio.sleep(0.5)
        
        # Test Case 1: Long explanation (user can say "yeah" without ANY effect)
        await self.session.say(
            "Hello! I will now count to twenty slowly. "
            "While I'm counting, try saying 'yeah' or 'okay' - I will completely ignore it and keep counting. "
            "But if you say 'stop' or 'wait', I will stop immediately. "
            "Ready? Here we go: one, two, three, four, five, six, seven, eight, nine, ten, "
            "eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, "
            "eighteen, nineteen, twenty. Done counting!"
        )
        
        # Test Case 2: Question (NOW "yeah" should be processed as a valid answer)
        await asyncio.sleep(1)
        await self.session.say("Did you notice I kept talking when you said yeah? Should I continue with another test?")

    # --- OVERRIDE STT NODE TO FILTER EVENTS ---
    async def stt_node(
        self,
        audio: AsyncIterable[rtc.AudioFrame],
        ctx: RunContext,
    ) -> Optional[AsyncIterable[stt.SpeechEvent]]:
        """
        Override the STT node to filter out backchannel words when agent is speaking.
        This is the key to preventing unwanted interruptions.
        """
        # Call the default STT implementation (returns async generator, don't await)
        stt_stream = Agent.default.stt_node(self, audio, ctx)
        
        if stt_stream is None:
            return None
        
        # Wrap the stream to filter events
        return self._filter_stt_events(stt_stream)
    
    async def _filter_stt_events(
        self, 
        stream: AsyncIterable[stt.SpeechEvent]
    ) -> AsyncIterable[stt.SpeechEvent]:
        """
        Filter STT events based on agent state and content.
        Only yield events that should trigger interruptions or be processed.
        """
        async for event in stream:
            # Filter both INTERIM and FINAL transcripts
            if isinstance(event, stt.SpeechEvent):
                if event.type in (stt.SpeechEventType.INTERIM_TRANSCRIPT, stt.SpeechEventType.FINAL_TRANSCRIPT):
                    text = event.alternatives[0].text if event.alternatives else ""
                    
                    # Analyze the transcript
                    should_filter = self._should_filter_transcript(text)
                    
                    if should_filter:
                        logger.info(f"🛡️  COMPLETELY IGNORING: '{text}' (agent speaking={self.is_speaking})")
                        # DON'T yield this event - it's completely dropped
                        # This prevents both interruption AND LLM processing
                        continue
                    else:
                        logger.info(f"✅ PASSING transcript: '{text}' (agent speaking={self.is_speaking})")
            
            # Yield all other events (including this one if not filtered)
            yield event
    
    def _should_filter_transcript(self, text: str) -> bool:
        """
        Determine if a transcript should be COMPLETELY FILTERED OUT.
        Returns True if this should be ignored (dropped entirely, not processed at all).
        
        Logic:
        - If agent is NOT speaking -> NEVER filter (always process user input)
        - If agent IS speaking:
            - Contains stop words -> NEVER filter (let it interrupt)
            - Pure backchannel only -> FILTER (completely ignore)
            - Mixed/other content -> NEVER filter (let it interrupt)
        """
        # If agent is NOT speaking, never filter - all user input is valid
        if not self.is_speaking:
            return False
        
        # Clean and tokenize
        clean_text = text.lower().translate(
            str.maketrans('', '', string.punctuation)
        ).strip()
        
        # Empty text - filter it out
        if not clean_text:
            return True
            
        words = set(clean_text.split())
        
        # DEBUG: Log the actual words being checked
        logger.debug(f"🔍 Checking words: {words}")
        logger.debug(f"🔍 Words in IGNORE_WORDS: {words & IGNORE_WORDS}")
        logger.debug(f"🔍 Words NOT in IGNORE_WORDS: {words - IGNORE_WORDS}")
        
        # Check for stop words (these should NEVER be filtered, even while speaking)
        has_stop_word = any(word in STOP_WORDS for word in words)
        if has_stop_word:
            logger.debug(f"🔍 Contains stop word - NOT filtering")
            return False  # Don't filter - let it interrupt immediately
        
        # Check if it's PURE backchannel (ONLY contains backchannel words)
        is_pure_backchannel = words.issubset(IGNORE_WORDS) and len(words) > 0
        
        logger.debug(f"🔍 Is pure backchannel: {is_pure_backchannel}")
        
        # Filter ONLY if:
        # 1. Agent is currently speaking AND
        # 2. User said ONLY backchannel words (like "yeah", "ok", "hmm")
        return is_pure_backchannel


server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Session configuration
    session = AgentSession(
        stt="deepgram/nova-3",  # Use string format - no API key needed
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # Keep normal interruption settings
        allow_interruptions=True,
        min_interruption_words=1,  # Require at least 1 word
        min_interruption_duration=0.2,
        
        # Disable automatic false interruption handling
        resume_false_interruption=False,
    )

    # Metrics
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Track agent state
    agent_instance = IntelligentAgent()
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        agent_instance.is_speaking = (ev.new_state == "speaking")
        logger.info(f"🤖 Agent state: {ev.new_state}")
    
    # Additional safety: Log when user speech is committed to verify filtering works
    @session.on("user_speech_committed")
    def on_user_speech_committed(msg):
        logger.info(f"✉️  User speech COMMITTED to conversation: '{msg.content}'")
        # If backchannel words appear here while agent was speaking, filtering failed

    # Start the session
    await session.start(
        agent=agent_instance,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server) 