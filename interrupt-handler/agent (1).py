"""
LiveKit Intelligent Interruption Handler
==========================================

Main agent implementation with context-aware interruption handling.

Author: TJ ABHIRAM
Date: 2026-01-31
Challenge: LiveKit Intelligent Interruption Handling
"""

import asyncio
import logging
import os
import time
import re
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Dict, Callable

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, deepgram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class InterruptConfig:
    """
    Configurable settings for intelligent interruption handling.
    All lists can be modified via environment variables or direct editing.
    """
    
    # FILLER WORDS - Ignored when agent is SPEAKING, processed when agent is SILENT
    FILLER_WORDS: Set[str] = {
        # Acknowledgments
        'yeah', 'yep', 'yes', 'yup', 'uh-huh', 'uhhuh', 'uh huh',
        # Agreement
        'ok', 'okay', 'k', 'alright', 'sure', 'right',
        # Listening sounds
        'hmm', 'hm', 'mm', 'mhm', 'mmm',
        'aha', 'ah', 'oh', 'ooh',
        # Understanding
        'i see', 'got it', 'gotcha', 'understood', 'cool',
    }
    
    # INTERRUPT WORDS - Always cause immediate interruption when agent is SPEAKING
    INTERRUPT_WORDS: Set[str] = {
        # Stop commands
        'stop', 'wait', 'hold', 'hold on', 'hold up', 'hang on',
        # Negation
        'no', 'nope', 'nah',
        # Control
        'pause', 'interrupt', 'cancel',
        # Correction indicators
        'actually', 'but', 'however', 'instead', 'rather',
    }
    
    # TIMING CONFIGURATION
    INTERRUPT_BUFFER_MS: int = 200  # Wait time for STT before deciding
    MIN_SPEECH_DURATION_MS: int = 500  # Minimum time to consider "speaking"
    MAX_BUFFER_AGE_SEC: float = 1.0  # Max age for buffered events
    
    # SEMANTIC ANALYSIS
    MIXED_INPUT_THRESHOLD: int = 2  # Min words to check for mixed input
    
    @classmethod
    def load_from_env(cls):
        """Load custom configuration from environment variables"""
        # Custom filler words: export CUSTOM_FILLER_WORDS="word1,word2,word3"
        custom_fillers = os.getenv('CUSTOM_FILLER_WORDS', '')
        if custom_fillers:
            new_words = {w.strip().lower() for w in custom_fillers.split(',') if w.strip()}
            cls.FILLER_WORDS.update(new_words)
            logger.info(f"Added custom filler words: {new_words}")
        
        # Custom interrupt words: export CUSTOM_INTERRUPT_WORDS="word1,word2"
        custom_interrupts = os.getenv('CUSTOM_INTERRUPT_WORDS', '')
        if custom_interrupts:
            new_words = {w.strip().lower() for w in custom_interrupts.split(',') if w.strip()}
            cls.INTERRUPT_WORDS.update(new_words)
            logger.info(f"Added custom interrupt words: {new_words}")
        
        # Timing configuration
        if os.getenv('INTERRUPT_BUFFER_MS'):
            cls.INTERRUPT_BUFFER_MS = int(os.getenv('INTERRUPT_BUFFER_MS'))
        
        if os.getenv('MIN_SPEECH_DURATION_MS'):
            cls.MIN_SPEECH_DURATION_MS = int(os.getenv('MIN_SPEECH_DURATION_MS'))


# Load configuration on import
InterruptConfig.load_from_env()


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class AgentState(Enum):
    """Agent's current operational state"""
    IDLE = "idle"          # Not speaking, not generating
    THINKING = "thinking"  # LLM generating response
    SPEAKING = "speaking"  # Actively playing audio
    LISTENING = "listening" # Waiting for user input


@dataclass
class InterruptEvent:
    """Represents a potential interruption from VAD"""
    timestamp: float
    vad_triggered: bool
    agent_state_at_trigger: AgentState
    transcribed_text: Optional[str] = None
    should_interrupt: Optional[bool] = None
    decision_reason: Optional[str] = None
    processing_time_ms: float = 0.0


class AgentStateTracker:
    """Thread-safe agent state tracking"""
    
    def __init__(self):
        self.current_state = AgentState.IDLE
        self.speech_start_time: Optional[float] = None
        self.last_state_change: float = time.time()
        self._lock = asyncio.Lock()
        self.state_history: deque = deque(maxlen=100)
    
    async def set_state(self, new_state: AgentState, context: str = ""):
        """Update agent state with logging"""
        async with self._lock:
            old_state = self.current_state
            if old_state == new_state:
                return
            
            self.current_state = new_state
            self.last_state_change = time.time()
            
            # Track when speech starts/ends
            if new_state == AgentState.SPEAKING:
                self.speech_start_time = time.time()
            elif old_state == AgentState.SPEAKING:
                self.speech_start_time = None
            
            # Log state change
            self.state_history.append({
                'timestamp': time.time(),
                'from': old_state.value,
                'to': new_state.value,
                'context': context
            })
            
            logger.info(f"🔄 State: {old_state.value} → {new_state.value} {f'({context})' if context else ''}")
    
    async def get_state(self) -> AgentState:
        """Get current state (thread-safe)"""
        async with self._lock:
            return self.current_state
    
    async def is_speaking(self) -> bool:
        """Check if agent is actively speaking"""
        async with self._lock:
            if self.current_state != AgentState.SPEAKING:
                return False
            
            # Check minimum speech duration
            if self.speech_start_time:
                duration_ms = (time.time() - self.speech_start_time) * 1000
                return duration_ms >= InterruptConfig.MIN_SPEECH_DURATION_MS
            
            return False
    
    def get_speech_duration_ms(self) -> float:
        """Get current speech duration in milliseconds"""
        if self.speech_start_time:
            return (time.time() - self.speech_start_time) * 1000
        return 0.0


# ============================================================================
# TEXT INTENT ANALYSIS
# ============================================================================

class TextIntentAnalyzer:
    """
    Analyzes transcribed text to determine user intent:
    - Pure filler ("yeah", "ok")
    - Pure interrupt ("stop", "wait")
    - Mixed input ("yeah but wait")
    """
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for analysis"""
        if not text:
            return ""
        # Convert to lowercase and remove extra whitespace
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation
        text = re.sub(r'[.,!?;:]', '', text)
        return text
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Split text into words and phrases"""
        normalized = TextIntentAnalyzer.normalize_text(text)
        words = normalized.split()
        
        # Also check for multi-word phrases
        phrases = []
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                phrases.append(phrase)
        
        return words + phrases
    
    @staticmethod
    def analyze_intent(text: str) -> Dict:
        """
        Analyze user intent from transcribed text.
        
        Returns:
            dict with:
            - is_filler: bool (pure filler words only)
            - is_interrupt: bool (contains interrupt words)
            - is_mixed: bool (contains both)
            - confidence: float (0-1)
            - matched_words: list of matched words
        """
        if not text:
            return {
                'is_filler': False,
                'is_interrupt': False,
                'is_mixed': False,
                'confidence': 0.0,
                'matched_words': [],
                'original_text': text
            }
        
        tokens = TextIntentAnalyzer.tokenize(text)
        words = TextIntentAnalyzer.normalize_text(text).split()
        
        # Find matches
        filler_matches = [t for t in tokens if t in InterruptConfig.FILLER_WORDS]
        interrupt_matches = [t for t in tokens if t in InterruptConfig.INTERRUPT_WORDS]
        
        # Determine intent
        has_filler = len(filler_matches) > 0
        has_interrupt = len(interrupt_matches) > 0
        
        # Pure filler: ONLY filler words, nothing else
        is_pure_filler = (
            has_filler and 
            not has_interrupt and 
            all(word in InterruptConfig.FILLER_WORDS for word in words)
        )
        
        # Pure interrupt: contains ANY interrupt word
        is_pure_interrupt = has_interrupt
        
        # Mixed: contains both types OR non-filler content
        is_mixed = (
            (has_filler and has_interrupt) or
            (has_filler and not is_pure_filler and not has_interrupt)
        )
        
        # Calculate confidence
        total_words = len(words)
        matched_words = len(set(filler_matches + interrupt_matches))
        confidence = matched_words / total_words if total_words > 0 else 0.0
        
        result = {
            'is_filler': is_pure_filler,
            'is_interrupt': is_pure_interrupt,
            'is_mixed': is_mixed,
            'confidence': confidence,
            'matched_words': list(set(filler_matches + interrupt_matches)),
            'original_text': text,
            'word_count': total_words
        }
        
        return result


# ============================================================================
# INTERRUPT BUFFER
# ============================================================================

class InterruptBuffer:
    """
    Buffers VAD interruption events for 100-300ms to wait for STT transcription.
    This allows us to decide whether to interrupt BEFORE actually interrupting.
    """
    
    def __init__(self, buffer_ms: int = 200):
        self.buffer_ms = buffer_ms
        self.pending_events: deque = deque()
        self._lock = asyncio.Lock()
        self.processed_count = 0
        self.ignored_count = 0
        self.interrupted_count = 0
    
    async def add_event(self, event: InterruptEvent):
        """Add a new interruption event to buffer"""
        async with self._lock:
            self.pending_events.append(event)
            logger.debug(f"📥 Buffered VAD event (queue size: {len(self.pending_events)})")
    
    async def get_pending_events(self) -> List[InterruptEvent]:
        """Get all pending events (non-destructive)"""
        async with self._lock:
            return list(self.pending_events)
    
    async def remove_event(self, event: InterruptEvent):
        """Remove a processed event from buffer"""
        async with self._lock:
            try:
                self.pending_events.remove(event)
                self.processed_count += 1
            except ValueError:
                pass
    
    async def clear_old_events(self, max_age_sec: float = 1.0):
        """Remove events older than max_age_sec"""
        async with self._lock:
            current_time = time.time()
            initial_count = len(self.pending_events)
            
            self.pending_events = deque([
                e for e in self.pending_events
                if (current_time - e.timestamp) < max_age_sec
            ])
            
            removed = initial_count - len(self.pending_events)
            if removed > 0:
                logger.debug(f"🧹 Cleared {removed} old events from buffer")
    
    def get_stats(self) -> Dict:
        """Get buffer statistics"""
        return {
            'pending': len(self.pending_events),
            'processed': self.processed_count,
            'ignored': self.ignored_count,
            'interrupted': self.interrupted_count
        }


# ============================================================================
# AGENT STATE GATEKEEPER
# ============================================================================

class AgentStateGatekeeper:
    """
    Core decision logic: Should we interrupt the agent or not?
    
    Decision Matrix:
    | User Input    | Agent State | Action              |
    |---------------|-------------|---------------------|
    | Filler (yeah) | SPEAKING    | IGNORE (continue)   |
    | Interrupt (stop)| SPEAKING  | INTERRUPT (stop now)|
    | Filler (yeah) | SILENT      | RESPOND (process)   |
    | Anything      | SILENT      | RESPOND (process)   |
    """
    
    def __init__(self, state_tracker: AgentStateTracker):
        self.state_tracker = state_tracker
        self.decision_history: deque = deque(maxlen=1000)
    
    async def should_interrupt(self, transcribed_text: str) -> Dict:
        """
        Main decision function: Should this input interrupt the agent?
        
        Returns:
            dict with:
            - should_interrupt: bool
            - reason: str (explanation)
            - confidence: float
        """
        decision_start = time.time()
        
        # Get current agent state
        agent_state = await self.state_tracker.get_state()
        is_speaking = await self.state_tracker.is_speaking()
        speech_duration = self.state_tracker.get_speech_duration_ms()
        
        # Analyze user intent
        intent = TextIntentAnalyzer.analyze_intent(transcribed_text)
        
        # DECISION LOGIC
        should_interrupt = False
        reason = ""
        
        if is_speaking:
            # Agent is SPEAKING - apply filtering logic
            
            if intent['is_filler'] and not intent['is_mixed']:
                # PURE FILLER while speaking → IGNORE
                should_interrupt = False
                reason = f"IGNORE: Pure filler '{transcribed_text}' while speaking (duration: {speech_duration:.0f}ms)"
            
            elif intent['is_interrupt']:
                # INTERRUPT WORD detected → INTERRUPT IMMEDIATELY
                should_interrupt = True
                reason = f"INTERRUPT: Interrupt word detected in '{transcribed_text}' (matched: {intent['matched_words']})"
            
            elif intent['is_mixed']:
                # MIXED INPUT (e.g., "yeah but wait") → INTERRUPT
                should_interrupt = True
                reason = f"INTERRUPT: Mixed input '{transcribed_text}' contains non-filler content"
            
            else:
                # Any other input while speaking → INTERRUPT (user wants to say something)
                should_interrupt = True
                reason = f"INTERRUPT: Non-filler input '{transcribed_text}' while speaking"
        
        else:
            # Agent is NOT SPEAKING (idle/listening) → ALWAYS RESPOND
            should_interrupt = False  # Not an "interrupt" but valid input to process
            reason = f"RESPOND: Valid input '{transcribed_text}' while agent silent (state: {agent_state.value})"
        
        # Calculate processing time
        processing_time_ms = (time.time() - decision_start) * 1000
        
        # Build decision result
        decision = {
            'should_interrupt': should_interrupt,
            'reason': reason,
            'confidence': intent['confidence'],
            'agent_state': agent_state.value,
            'is_speaking': is_speaking,
            'speech_duration_ms': speech_duration,
            'intent_analysis': intent,
            'processing_time_ms': processing_time_ms,
            'timestamp': time.time()
        }
        
        # Log decision
        self.decision_history.append(decision)
        
        # Log with appropriate emoji
        emoji = "🛑" if should_interrupt else "✅" if is_speaking else "💬"
        logger.info(f"{emoji} {reason}")
        
        return decision
    
    def get_statistics(self) -> Dict:
        """Get decision statistics"""
        if not self.decision_history:
            return {}
        
        total = len(self.decision_history)
        interrupted = sum(1 for d in self.decision_history if d['should_interrupt'])
        ignored = sum(1 for d in self.decision_history if not d['should_interrupt'] and d['is_speaking'])
        responded = sum(1 for d in self.decision_history if not d['should_interrupt'] and not d['is_speaking'])
        
        return {
            'total_decisions': total,
            'interrupted': interrupted,
            'ignored': ignored,
            'responded': responded,
            'interrupt_rate': interrupted / total if total > 0 else 0,
            'avg_processing_time_ms': sum(d['processing_time_ms'] for d in self.decision_history) / total
        }


# ============================================================================
# INTELLIGENT INTERRUPTION HANDLER
# ============================================================================

class IntelligentInterruptionHandler:
    """
    Main handler that integrates all components:
    VAD → Buffer → STT → Intent Analysis → State Gatekeeper → Decision
    """
    
    def __init__(self):
        self.state_tracker = AgentStateTracker()
        self.interrupt_buffer = InterruptBuffer(InterruptConfig.INTERRUPT_BUFFER_MS)
        self.gatekeeper = AgentStateGatekeeper(self.state_tracker)
        self.intent_analyzer = TextIntentAnalyzer()
        
        # Callbacks
        self.on_interrupt_callback: Optional[Callable] = None
        self.on_ignore_callback: Optional[Callable] = None
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._processing_task: Optional[asyncio.Task] = None
        
        logger.info("🚀 Intelligent Interruption Handler initialized")
    
    async def start(self):
        """Start background processing tasks"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("▶️  Background tasks started")
    
    async def stop(self):
        """Stop background tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._processing_task:
            self._processing_task.cancel()
        logger.info("⏹️  Background tasks stopped")
    
    async def _cleanup_loop(self):
        """Periodically clean up old buffered events"""
        while True:
            try:
                await asyncio.sleep(0.5)  # Run every 500ms
                await self.interrupt_buffer.clear_old_events(
                    InterruptConfig.MAX_BUFFER_AGE_SEC
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _processing_loop(self):
        """Process buffered events that have received transcriptions"""
        while True:
            try:
                await asyncio.sleep(0.05)  # Check every 50ms
                
                pending = await self.interrupt_buffer.get_pending_events()
                current_time = time.time()
                
                for event in pending:
                    # Check if event has waited long enough
                    wait_time_ms = (current_time - event.timestamp) * 1000
                    
                    if wait_time_ms >= InterruptConfig.INTERRUPT_BUFFER_MS:
                        # Event has waited long enough
                        if event.transcribed_text:
                            # We have transcription - make decision
                            await self._process_event(event)
                            await self.interrupt_buffer.remove_event(event)
                        elif wait_time_ms >= InterruptConfig.INTERRUPT_BUFFER_MS * 2:
                            # Waited too long without transcription - assume interrupt
                            event.should_interrupt = True
                            event.decision_reason = "Timeout: No transcription received"
                            await self._process_event(event)
                            await self.interrupt_buffer.remove_event(event)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
    
    async def _process_event(self, event: InterruptEvent):
        """Process a single interrupt event"""
        if not event.transcribed_text:
            return
        
        # Get decision from gatekeeper
        decision = await self.gatekeeper.should_interrupt(event.transcribed_text)
        
        # Update event
        event.should_interrupt = decision['should_interrupt']
        event.decision_reason = decision['reason']
        event.processing_time_ms = decision['processing_time_ms']
        
        # Execute callbacks
        if event.should_interrupt:
            if self.on_interrupt_callback:
                await self.on_interrupt_callback(event)
            self.interrupt_buffer.interrupted_count += 1
        else:
            if self.on_ignore_callback:
                await self.on_ignore_callback(event)
            if decision['is_speaking']:
                self.interrupt_buffer.ignored_count += 1
    
    # === PUBLIC API ===
    
    async def on_vad_triggered(self):
        """Called when VAD detects speech (before transcription)"""
        agent_state = await self.state_tracker.get_state()
        
        event = InterruptEvent(
            timestamp=time.time(),
            vad_triggered=True,
            agent_state_at_trigger=agent_state
        )
        
        await self.interrupt_buffer.add_event(event)
        logger.debug(f"🎤 VAD triggered (agent: {agent_state.value})")
    
    async def on_transcription_received(self, text: str):
        """Called when STT provides transcription"""
        # Find the most recent pending event without transcription
        pending = await self.interrupt_buffer.get_pending_events()
        
        for event in reversed(pending):
            if not event.transcribed_text:
                event.transcribed_text = text
                logger.debug(f"📝 Transcription: '{text}'")
                break
    
    async def set_agent_speaking(self, speaking: bool):
        """Update agent speaking state"""
        if speaking:
            await self.state_tracker.set_state(AgentState.SPEAKING, "TTS started")
        else:
            await self.state_tracker.set_state(AgentState.IDLE, "TTS stopped")
    
    async def set_agent_thinking(self, thinking: bool):
        """Update agent thinking state"""
        if thinking:
            await self.state_tracker.set_state(AgentState.THINKING, "LLM processing")
        else:
            await self.state_tracker.set_state(AgentState.IDLE, "LLM done")
    
    def print_statistics(self):
        """Print handler statistics"""
        buffer_stats = self.interrupt_buffer.get_stats()
        gatekeeper_stats = self.gatekeeper.get_statistics()
        
        print("\n📊 Handler Statistics:")
        print(f"  Buffer: {buffer_stats['pending']} pending, {buffer_stats['processed']} processed")
        print(f"  Decisions: {buffer_stats['ignored']} ignored, {buffer_stats['interrupted']} interrupted")
        
        if gatekeeper_stats:
            print(f"  Total Decisions: {gatekeeper_stats['total_decisions']}")
            print(f"  Interrupt Rate: {gatekeeper_stats['interrupt_rate']:.1%}")
            print(f"  Avg Processing Time: {gatekeeper_stats['avg_processing_time_ms']:.2f}ms")


# ============================================================================
# LIVEKIT AGENT INTEGRATION
# ============================================================================

class IntelligentVoiceAgent:
    """
    LiveKit VoicePipelineAgent with intelligent interruption handling
    """
    
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.handler = IntelligentInterruptionHandler()
        
        # Setup callbacks
        self.handler.on_interrupt_callback = self._on_interrupt
        self.handler.on_ignore_callback = self._on_ignore
        
        # Create voice pipeline agent
        self.agent = VoicePipelineAgent(
            vad=silero.VAD.load(),  # Voice Activity Detection (UNCHANGED)
            stt=deepgram.STT(),  # Speech-to-Text
            llm=openai.LLM(model="gpt-4o"),  # Language Model
            tts=openai.TTS(),  # Text-to-Speech
            chat_ctx=llm.ChatContext().append(
                role="system",
                text="You are a helpful AI assistant. Keep responses concise."
            )
        )
        
        # Hook into agent events
        self._setup_event_hooks()
        
        logger.info("🤖 Intelligent Voice Agent initialized")
    
    def _setup_event_hooks(self):
        """Hook into VoicePipelineAgent events"""
        
        # Note: The actual event hooking depends on LiveKit's API
        # This is a simplified version - you'll need to adapt to the actual LiveKit API
        
        @self.agent.on("user_speech_committed")
        async def on_user_speech(event):
            """Called when user speech is detected"""
            await self.handler.on_vad_triggered()
        
        @self.agent.on("user_transcript")
        async def on_transcript(event):
            """Called when transcription is received"""
            await self.handler.on_transcription_received(event.text)
        
        @self.agent.on("agent_speech_started")
        async def on_speech_start(event):
            """Called when agent starts speaking"""
            await self.handler.set_agent_speaking(True)
        
        @self.agent.on("agent_speech_stopped")
        async def on_speech_stop(event):
            """Called when agent stops speaking"""
            await self.handler.set_agent_speaking(False)
    
    async def _on_interrupt(self, event: InterruptEvent):
        """Handle validated interruption"""
        logger.warning(f"🛑 INTERRUPTING: {event.decision_reason}")
        # Stop current TTS playback
        await self.agent.interrupt()
    
    async def _on_ignore(self, event: InterruptEvent):
        """Handle ignored filler words"""
        logger.info(f"✅ IGNORING: {event.decision_reason}")
        # Do nothing - let agent continue speaking
        pass
    
    async def start(self):
        """Start the agent"""
        await self.handler.start()
        await self.agent.start(self.ctx.room)
        logger.info("🎙️  Agent started and ready")
    
    async def stop(self):
        """Stop the agent"""
        await self.handler.stop()
        self.handler.print_statistics()
        logger.info("🛑 Agent stopped")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def entrypoint(ctx: JobContext):
    """
    Main entry point for LiveKit agent.
    This function is called when a room is created.
    """
    logger.info(f"🚀 Starting agent for room: {ctx.room.name}")
    
    # Wait for participant to connect
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Create and start intelligent agent
    agent = IntelligentVoiceAgent(ctx)
    await agent.start()
    
    logger.info("✅ Agent running - waiting for voice input")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Print configuration
    print("\n" + "="*80)
    print("LiveKit Intelligent Interruption Handler")
    print("="*80)
    print(f"\nFiller words: {sorted(list(InterruptConfig.FILLER_WORDS)[:10])}...")
    print(f"Interrupt words: {sorted(list(InterruptConfig.INTERRUPT_WORDS)[:10])}...")
    print(f"Buffer time: {InterruptConfig.INTERRUPT_BUFFER_MS}ms")
    print(f"Min speech duration: {InterruptConfig.MIN_SPEECH_DURATION_MS}ms")
    print("\n" + "="*80 + "\n")
    
    # Run with LiveKit CLI
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
