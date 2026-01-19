"""
Advanced Interruption Handler with Timing Awareness and Urgency Detection

Provides production-grade interruption handling that considers:
- Semantic patterns (regex-based classification)
- Agent speech duration (timing awareness)
- Audio urgency features (volume, pitch, rate)
- Confidence scoring for nuanced decisions
"""

import asyncio
import re
import logging
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent conversation states"""
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"


class InterruptionIntent(Enum):
    """Classification of user interruption intent"""
    IGNORE = "ignore"
    INTERRUPT = "interrupt"


@dataclass
class InterruptionScore:
    """Detailed scoring for interruption decision"""
    semantic_score: float  # 0-1: Pattern matching confidence
    timing_score: float    # 0-1: How timing affects decision
    urgency_score: float   # 0-1: Audio urgency features
    final_score: float     # 0-1: Combined weighted score
    decision: InterruptionIntent
    reason: str
    confidence: float      # 0-1: How confident we are


@dataclass
class AudioFeatures:
    """Extracted audio features for urgency detection"""
    rms_energy: float      # Root mean square energy (volume)
    zero_crossing_rate: float  # Pitch/timbre indicator
    speaking_rate: float   # Estimated words per second
    duration: float        # Audio duration in seconds


class AudioAnalyzer:
    """Analyzes audio features to detect urgency in speech using signal processing."""

    @staticmethod
    def extract_features(audio_data: np.ndarray, sample_rate: int = 16000) -> AudioFeatures:
        """
        Extract audio features from raw PCM data.

        Args:
            audio_data: Numpy array of audio samples
            sample_rate: Sample rate in Hz

        Returns:
            AudioFeatures with extracted metrics
        """
        if len(audio_data) == 0:
            return AudioFeatures(0.0, 0.0, 0.0, 0.0)

        # RMS Energy (volume indicator)
        rms = np.sqrt(np.mean(audio_data ** 2))

        # Zero crossing rate (pitch/timbre)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        zcr = zero_crossings / len(audio_data)

        # Duration
        duration = len(audio_data) / sample_rate

        # Speaking rate estimation (simple heuristic)
        # Higher ZCR usually means faster/more energetic speech
        speaking_rate = zcr * 100  # Normalized estimate

        return AudioFeatures(
            rms_energy=float(rms),
            zero_crossing_rate=float(zcr),
            speaking_rate=float(speaking_rate),
            duration=float(duration)
        )

    @staticmethod
    def calculate_urgency(features: AudioFeatures) -> float:
        """
        Calculate urgency score from audio features.

        High urgency indicators:
        - High RMS energy (loud voice)
        - High zero crossing rate (sharp/harsh tone)
        - Short duration (quick interjection)

        Returns:
            Urgency score from 0.0 (calm) to 1.0 (urgent)
        """
        # Normalize features (these are rough thresholds)
        energy_score = min(features.rms_energy / 0.3, 1.0)  # Loud speech
        zcr_score = min(features.zero_crossing_rate / 0.1, 1.0)  # Sharp tone

        # Short duration = more urgent (quick interjection)
        duration_score = 1.0 - min(features.duration / 2.0, 1.0)

        # Weighted combination
        urgency = (
            energy_score * 0.4 +      # Volume is important
            zcr_score * 0.3 +          # Tone matters
            duration_score * 0.3       # Quick = urgent
        )

        return min(max(urgency, 0.0), 1.0)  # Clamp to [0, 1]


class AdvancedInterruptionClassifier:
    """Advanced semantic classifier with pattern matching and confidence scoring."""

    def __init__(
        self,
        soft_words: list[str] | None = None,
        hard_words: list[str] | None = None,
        polite_phrases: list[str] | None = None,
    ):
        """
        Initialize classifier with configurable word lists.

        Args:
            soft_words: List of words to ignore (e.g., ['yeah', 'ok', 'hmm'])
            hard_words: List of words that trigger interruption (e.g., ['wait', 'stop'])
            polite_phrases: List of polite phrases that trigger interruption
        """
        # Default soft acknowledgments
        default_soft = [
            'yeah', 'yep', 'yes', 'uh-huh', 'mm-hmm', 'mhmm', 'okay', 'ok',
            'right', 'sure', 'got it', 'i see', 'makes sense', 'understood',
            'alright', 'cool', 'nice', 'go on', 'continue', 'keep going',
            'interesting', 'really', 'wow', 'oh', 'ah', 'hmm'
        ]

        # Default hard interruptions
        default_hard = [
            'wait', 'hold on', 'stop', 'hang on', 'but', 'however',
            'actually', 'excuse me', 'sorry', 'one sec', 'one second',
            'no', 'what', 'pardon'  # Removed 'huh' to avoid conflict with 'uh-huh'
        ]

        # Default polite interruptions
        default_polite = [
            'quick question', 'can i ask', 'may i', 'could you',
            'before you', 'let me', 'i want to', 'i need to',
            'just to clarify', 'to be clear', 'one thing'
        ]

        self.soft_words = soft_words or default_soft
        self.hard_words = hard_words or default_hard
        self.polite_phrases = polite_phrases or default_polite

        # Build regex patterns
        self._build_patterns()

        logger.debug("Advanced semantic classifier initialized")

    def _build_patterns(self):
        """Build regex patterns from word lists"""
        # Sort by length (longest first) to match multi-word phrases before single words
        soft_sorted = sorted(self.soft_words, key=len, reverse=True)
        hard_sorted = sorted(self.hard_words, key=len, reverse=True)
        polite_sorted = sorted(self.polite_phrases, key=len, reverse=True)

        # Build patterns - escape but preserve word boundaries
        self.soft_patterns = []
        for word in soft_sorted:
            # Replace hyphens with optional space or hyphen
            pattern = re.escape(word).replace(r'\-', r'[\s\-]')
            self.soft_patterns.append((re.compile(rf'\b{pattern}\b', re.IGNORECASE), 0.9))

        self.hard_patterns = []
        for word in hard_sorted:
            pattern = re.escape(word).replace(r'\-', r'[\s\-]')
            self.hard_patterns.append((re.compile(rf'\b{pattern}\b', re.IGNORECASE), 0.95))

        self.polite_patterns = []
        for phrase in polite_sorted:
            pattern = re.escape(phrase).replace(r'\-', r'[\s\-]')
            self.polite_patterns.append((re.compile(rf'\b{pattern}\b', re.IGNORECASE), 0.9))

    def classify(self, text: str) -> tuple[InterruptionIntent, float, str]:
        """
        Classify text with confidence scoring.

        Returns:
            (intent, confidence, reason)
        """
        if not text or len(text.strip()) < 2:
            return InterruptionIntent.IGNORE, 0.5, "Empty input"

        text_lower = text.lower().strip()

        # CRITICAL: Check hard interruptions FIRST
        # This ensures "Yeah wait a second" interrupts (because of "wait")
        # Even if "yeah" is present, "wait" takes priority
        for pattern, confidence in self.hard_patterns:
            if pattern.search(text_lower):
                return InterruptionIntent.INTERRUPT, confidence, f"Hard interruption pattern matched"

        # Check polite interruptions
        for pattern, confidence in self.polite_patterns:
            if pattern.search(text_lower):
                return InterruptionIntent.INTERRUPT, confidence, f"Polite interruption pattern matched"

        # Check soft acknowledgments (only if no interruptions found)
        for pattern, confidence in self.soft_patterns:
            if pattern.search(text_lower):
                return InterruptionIntent.IGNORE, confidence, f"Soft acknowledgment pattern matched"


        # Word count heuristic
        word_count = len(text_lower.split())
        if word_count <= 3:
            return InterruptionIntent.IGNORE, 0.7, f"Short input ({word_count} words)"

        # Default: longer input = probably wants to interrupt
        return InterruptionIntent.INTERRUPT, 0.6, f"Longer input ({word_count} words)"


class TimingAwareInterruptionHandler:
    """
    Production-grade interruption handler with semantic classification,
    timing awareness, urgency detection, and confidence scoring.
    """

    def __init__(
        self,
        min_speech_duration: float = 1.0,
        short_speech_threshold: float = 3.0,
        long_speech_threshold: float = 8.0,
        base_threshold: float = 0.7,
        soft_words: list[str] | None = None,
        hard_words: list[str] | None = None,
        polite_phrases: list[str] | None = None,
    ):
        """
        Args:
            min_speech_duration: Minimum time before allowing ANY interruptions
            short_speech_threshold: Time below which we're more conservative
            long_speech_threshold: Time above which we're more lenient
            base_threshold: Base confidence threshold for interruption (0-1)
            soft_words: List of words to ignore (e.g., ['yeah', 'ok', 'hmm'])
            hard_words: List of words that trigger interruption
            polite_phrases: List of polite phrases that trigger interruption
        """
        self.min_speech_duration = min_speech_duration
        self.short_speech_threshold = short_speech_threshold
        self.long_speech_threshold = long_speech_threshold
        self.base_threshold = base_threshold

        self.classifier = AdvancedInterruptionClassifier(
            soft_words=soft_words,
            hard_words=hard_words,
            polite_phrases=polite_phrases,
        )
        self.audio_analyzer = AudioAnalyzer()

        self.current_state = AgentState.IDLE
        self.speech_start_time: Optional[float] = None

        logger.info(f"Timing-aware interruption handler initialized (min={min_speech_duration}s, short<{short_speech_threshold}s, long>{long_speech_threshold}s)")

    def _calculate_timing_score(self, speech_duration: float) -> float:
        """
        Calculate timing factor based on how long agent has been speaking.

        Returns:
            0.0-1.0 where higher = more likely to allow interruption
        """
        if speech_duration < self.min_speech_duration:
            # Very short - almost never interrupt
            return 0.0

        elif speech_duration < self.short_speech_threshold:
            # Short speech - be conservative
            # Linear scale from 0.3 to 0.6
            progress = (speech_duration - self.min_speech_duration) / \
                      (self.short_speech_threshold - self.min_speech_duration)
            return 0.3 + (progress * 0.3)

        elif speech_duration < self.long_speech_threshold:
            # Normal speech - neutral
            # Linear scale from 0.6 to 0.8
            progress = (speech_duration - self.short_speech_threshold) / \
                      (self.long_speech_threshold - self.short_speech_threshold)
            return 0.6 + (progress * 0.2)

        else:
            # Long speech - be more lenient
            # Agent talking too long, user probably wants to speak
            return min(0.8 + (speech_duration - self.long_speech_threshold) * 0.02, 1.0)

    def decide(
        self,
        text: str,
        speech_duration: float,
        audio_features: Optional[AudioFeatures] = None
    ) -> InterruptionScore:
        """
        Make interruption decision with full context.

        Args:
            text: Transcribed user speech
            speech_duration: How long agent has been speaking
            audio_features: Optional audio features for urgency

        Returns:
            InterruptionScore with detailed reasoning
        """
        # Stage 1: Semantic classification
        intent, semantic_confidence, reason = self.classifier.classify(text)

        # CRITICAL: Hard interruptions always win, regardless of timing
        # This ensures "wait", "stop", etc. always interrupt
        if intent == InterruptionIntent.INTERRUPT and semantic_confidence >= 0.9:
            return InterruptionScore(
                semantic_score=semantic_confidence,
                timing_score=1.0,  # Override timing
                urgency_score=1.0,  # Override urgency
                final_score=semantic_confidence,
                decision=InterruptionIntent.INTERRUPT,
                reason=f"Hard interruption detected: {reason}",
                confidence=semantic_confidence,
            )

        semantic_score = semantic_confidence if intent == InterruptionIntent.INTERRUPT else (1.0 - semantic_confidence)

        # Stage 2: Timing awareness
        timing_score = self._calculate_timing_score(speech_duration)

        # Stage 3: Urgency detection (if audio available)
        if audio_features:
            urgency_score = self.audio_analyzer.calculate_urgency(audio_features)
        else:
            urgency_score = 0.5  # Neutral if no audio

        # Stage 4: Weighted combination
        # Semantic is most important, timing and urgency are modifiers
        final_score = (
            semantic_score * 0.5 +      # Pattern matching
            timing_score * 0.3 +         # How long agent has spoken
            urgency_score * 0.2          # How urgent user sounds
        )

        # Stage 5: Apply dynamic threshold
        # Adjust threshold based on timing
        dynamic_threshold = self.base_threshold
        if speech_duration < self.short_speech_threshold:
            dynamic_threshold += 0.1  # Higher threshold = harder to interrupt
        elif speech_duration > self.long_speech_threshold:
            dynamic_threshold -= 0.1  # Lower threshold = easier to interrupt

        # Stage 6: Final decision
        should_interrupt = final_score > dynamic_threshold
        final_intent = InterruptionIntent.INTERRUPT if should_interrupt else InterruptionIntent.IGNORE

        # Calculate overall confidence
        confidence = abs(final_score - dynamic_threshold) / dynamic_threshold
        confidence = min(max(confidence, 0.0), 1.0)

        # Build detailed reason
        detailed_reason = (
            f"{reason} | "
            f"Duration: {speech_duration:.1f}s | "
            f"Scores: semantic={semantic_score:.2f}, timing={timing_score:.2f}, urgency={urgency_score:.2f} | "
            f"Final: {final_score:.2f} vs threshold={dynamic_threshold:.2f}"
        )

        logger.info(f"Decision: {final_intent.value.upper()} (confidence={confidence:.2f})")
        logger.debug(f"{detailed_reason}")

        return InterruptionScore(
            semantic_score=semantic_score,
            timing_score=timing_score,
            urgency_score=urgency_score,
            final_score=final_score,
            decision=final_intent,
            reason=detailed_reason,
            confidence=confidence
        )

    def update_agent_state(self, new_state: AgentState):
        """Update current agent state for context tracking"""
        if self.current_state != new_state:
            logger.debug(f"State change: {self.current_state.value} → {new_state.value}")
            self.current_state = new_state

        if new_state == AgentState.SPEAKING:
            self.speech_start_time = time.time()
        else:
            self.speech_start_time = None

    def get_speech_duration(self) -> float:
        """Get current agent speech duration"""
        if self.speech_start_time is None:
            return 0.0
        return time.time() - self.speech_start_time



class SemanticInterruptionHandler(TimingAwareInterruptionHandler):
    """Backward compatible simple handler"""
    pass


class InterruptionManager:
    """Simple manager for basic integration"""

    def __init__(self, handler: TimingAwareInterruptionHandler):
        self.handler = handler

    async def on_vad_detected(self, vad_confidence: float, stt_callback: Callable) -> bool:
        """Simplified interface - returns True/False"""
        if self.handler.current_state != AgentState.SPEAKING:
            return False

        try:
            text = await asyncio.wait_for(stt_callback(), timeout=0.5)
            speech_duration = self.handler.get_speech_duration()
            score = self.handler.decide(text, speech_duration)
            return score.decision == InterruptionIntent.INTERRUPT
        except asyncio.TimeoutError:
            return False