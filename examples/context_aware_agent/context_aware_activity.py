"""
Context-Aware Agent Activity with Backchannel Filtering.

This module provides a custom AgentActivity that overrides the interruption
handling to filter out backchannels when the agent is speaking.
"""

import asyncio
import logging
import time
from typing import Optional, TYPE_CHECKING

from livekit.agents import stt, vad
from livekit.agents.voice.agent_activity import AgentActivity
from livekit.agents.voice.audio_recognition import _EndOfTurnInfo, _PreemptiveGenerationInfo
from livekit.agents.voice.events import UserInputTranscribedEvent

from interruption_filter import InterruptionFilter, FilterDecision
from config import InterruptionFilterConfig

if TYPE_CHECKING:
    from livekit.agents.voice.agent import Agent
    from livekit.agents.voice.agent_session import AgentSession

logger = logging.getLogger("context-aware-activity")


class ContextAwareAgentActivity(AgentActivity):
    """
    Custom AgentActivity that implements context-aware backchannel filtering.
    
    This overrides the key hook methods to filter out backchannels when
    the agent is speaking, preventing false interruptions.
    """
    
    def __init__(
        self, 
        agent: "Agent", 
        sess: "AgentSession",
        filter_config: Optional[InterruptionFilterConfig] = None
    ):
        super().__init__(agent, sess)
        
        # Initialize the interruption filter
        self.interruption_filter = InterruptionFilter(filter_config)
        
        # Track state for filtering decisions
        self._pending_transcript = ""
        self._last_filter_decision: Optional[FilterDecision] = None
        self._ignored_count = 0
    
    def _is_agent_speaking(self) -> bool:
        """Check if the agent is currently speaking."""
        # Check multiple conditions to determine if agent is speaking
        
        # 1. Check agent state
        if self._session.agent_state == "speaking":
            return True
        
        # 2. Check if there's an active speech handle
        if self._current_speech is not None and not self._current_speech.interrupted:
            return True
        
        # 3. Check if there's a paused speech (agent was speaking but paused)
        if self._paused_speech is not None:
            return True
        
        return False
    
    def _should_filter_transcript(self, transcript: str) -> bool:
        """
        Determine if the transcript should be filtered (not cause interruption).
        
        Returns True if the transcript should be IGNORED (no interruption).
        Returns False if the transcript should cause an interruption.
        """
        if not transcript or not transcript.strip():
            return True  # Empty transcripts don't cause interruptions
        
        is_speaking = self._is_agent_speaking()
        result = self.interruption_filter.filter(transcript, is_speaking)
        
        self._last_filter_decision = result.decision
        
        if result.decision == FilterDecision.IGNORE:
            self._ignored_count += 1
            logger.debug(
                f"[Filter] IGNORING transcript #{self._ignored_count}: '{transcript}' "
                f"(agent speaking: {is_speaking})"
            )
            return True
        
        return False
    
    def on_interim_transcript(self, ev: stt.SpeechEvent, *, speaking: bool | None) -> None:
        """
        Handle interim (non-final) transcription events.
        
        We filter backchannels here to prevent the default behavior from
        triggering interruptions.
        """
        from livekit.agents import llm
        
        # Skip if using realtime model with user transcription
        if isinstance(self.llm, llm.RealtimeModel) and self.llm.capabilities.user_transcription:
            return
        
        transcript = ev.alternatives[0].text if ev.alternatives else ""
        
        # Check if this should be filtered
        if self._should_filter_transcript(transcript):
            # Still emit the event for logging purposes, but don't trigger interruption
            self._session._user_input_transcribed(
                UserInputTranscribedEvent(
                    language=ev.alternatives[0].language if ev.alternatives else None,
                    transcript=transcript,
                    is_final=False,
                    speaker_id=ev.alternatives[0].speaker_id if ev.alternatives else None,
                ),
            )
            # IMPORTANT: Don't call _interrupt_by_audio_activity for filtered transcripts
            return
        
        # Not filtered - call the parent implementation which will handle interruption
        super().on_interim_transcript(ev, speaking=speaking)
    
    def on_final_transcript(self, ev: stt.SpeechEvent, *, speaking: bool | None = None) -> None:
        """
        Handle final transcription events.
        
        Final transcripts are also filtered to prevent backchannels from
        interrupting the agent.
        """
        from livekit.agents import llm
        
        # Skip if using realtime model with user transcription
        if isinstance(self.llm, llm.RealtimeModel) and self.llm.capabilities.user_transcription:
            return
        
        transcript = ev.alternatives[0].text if ev.alternatives else ""
        
        # Check if this should be filtered
        if self._should_filter_transcript(transcript):
            # Emit the event for logging
            self._session._user_input_transcribed(
                UserInputTranscribedEvent(
                    language=ev.alternatives[0].language if ev.alternatives else None,
                    transcript=transcript,
                    is_final=True,
                    speaker_id=ev.alternatives[0].speaker_id if ev.alternatives else None,
                ),
            )
            # IMPORTANT: Don't trigger interruption for filtered transcripts
            # But we might need to handle the paused speech case
            return
        
        # Not filtered - call the parent implementation
        super().on_final_transcript(ev, speaking=speaking)
    
    def on_vad_inference_done(self, ev: vad.VADEvent) -> None:
        """
        Handle VAD inference completion.
        
        We need to be careful here because VAD can trigger interruptions
        before STT has fully transcribed the speech. We use the pending
        transcript info to make decisions.
        """
        # Check if turn detection allows VAD-based interruption
        if self._turn_detection in ("manual", "realtime_llm"):
            return
        
        # Check speech duration threshold
        if ev.speech_duration < self._session.options.min_interruption_duration:
            return
        
        # If we have recent transcript that was filtered, don't interrupt
        if (
            self._last_filter_decision == FilterDecision.IGNORE 
            and self._is_agent_speaking()
        ):
            logger.debug(
                f"[VAD] Suppressing VAD interruption - last transcript was filtered "
                f"(speech duration: {ev.speech_duration:.2f}s)"
            )
            return
        
        # Otherwise, let the parent handle it
        super().on_vad_inference_done(ev)
    
    def on_start_of_speech(self, ev: vad.VADEvent | None) -> None:
        """Handle start of user speech."""
        # Reset filter decision at start of new speech
        self._last_filter_decision = None
        super().on_start_of_speech(ev)
    
    def on_end_of_speech(self, ev: vad.VADEvent | None) -> None:
        """Handle end of user speech."""
        super().on_end_of_speech(ev)
    
    def on_end_of_turn(self, info: _EndOfTurnInfo) -> bool:
        """
        Handle end of user turn.
        
        If the entire turn was just backchannels, we should not generate a reply.
        """
        # Check if the transcript was a filtered backchannel
        if self._should_filter_transcript(info.new_transcript):
            logger.info(
                f"[EOT] Ignoring end-of-turn for backchannel: '{info.new_transcript}'"
            )
            # Return False to indicate we handled it (don't generate reply)
            return False
        
        # Not filtered - proceed normally
        return super().on_end_of_turn(info)
