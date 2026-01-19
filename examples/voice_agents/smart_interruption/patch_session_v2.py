"""
Smart Interruption Patch V2 - No Pause, Seamless Continuation

This version NEVER pauses the audio. The agent continues speaking seamlessly
when passive words are detected. Only command words trigger interruption.

Key behavior:
- Passive words ("yeah", "okay"): Agent continues speaking WITHOUT ANY PAUSE
- Command words ("stop", "wait"): Agent stops IMMEDIATELY
- When agent is silent: All input is processed normally
"""

import logging
import sys
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from livekit.agents.voice import agent_activity

# Handle imports
try:
    from .handler import SmartInterruptionHandler, InterruptionDecision
    from .config import InterruptionConfig
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from handler import SmartInterruptionHandler, InterruptionDecision
    from config import InterruptionConfig

logger = logging.getLogger("smart-interruption-v2")


def patch_agent_activity_v2(
    activity: "agent_activity.AgentActivity",
) -> SmartInterruptionHandler:
    """Patch AgentActivity with seamless interruption handling.

    NO PAUSE mechanism - agent continues speaking for passive words.
    """
    config = InterruptionConfig()
    smart_handler = SmartInterruptionHandler(config)

    # Store original methods
    original_interrupt = activity._interrupt_by_audio_activity
    original_on_interim = activity.on_interim_transcript
    original_on_final = activity.on_final_transcript
    original_on_vad = activity.on_vad_inference_done

    # Patch AudioRecognition to skip passive transcripts
    if activity._audio_recognition:
        original_on_stt_event = activity._audio_recognition._on_stt_event
    else:
        original_on_stt_event = None
    
    # Track state
    state = {
        "interrupted_speech_id": None,
        "last_command_transcript": "",
        "skip_checks": False,
        "last_transcript": "",
    }

    def is_agent_speaking() -> bool:
        """Check if agent is currently speaking."""
        if activity._current_speech is None:
            return False
        try:
            return (
                not activity._current_speech.interrupted
                and not activity._current_speech.done()
            )
        except AttributeError:
            return False

    def get_speech_id():
        """Get current speech ID."""
        if activity._current_speech:
            return id(activity._current_speech)
        return None

    def get_transcript() -> str:
        """Get current transcript."""
        if activity._audio_recognition:
            return activity._audio_recognition.current_transcript.strip()
        return ""

    def reset_transcript_only():
        """Reset transcript without resetting STT (to avoid restart)."""
        if activity._audio_recognition:
            # Just clear the transcript fields, don't reset STT
            activity._audio_recognition._audio_transcript = ""
            activity._audio_recognition._audio_interim_transcript = ""
            activity._audio_recognition._audio_preflight_transcript = ""
            activity._audio_recognition._final_transcript_confidence = []
    
    def smart_interrupt_by_audio_activity() -> None:
        """ULTRA-FAST interruption check - optimized for ZERO pause.

        Key optimization: Once we identify passive words, SKIP all future
        checks until the transcript changes.
        """
        speech_id = get_speech_id()

        # FAST PATH 1: Already interrupted
        if speech_id and state["interrupted_speech_id"] == speech_id:
            return

        # FAST PATH 2: Skip checks flag is set
        if state["skip_checks"]:
            return

        # FAST PATH 3: Agent not speaking - process normally
        if not is_agent_speaking():
            state["skip_checks"] = False
            original_interrupt()
            return

        # Agent IS speaking - check transcript
        transcript = get_transcript()

        # FAST PATH 4: No transcript yet
        if not transcript:
            return

        # FAST PATH 5: Same transcript as before
        if transcript == state["last_transcript"]:
            return

        # NEW transcript - update and process
        state["last_transcript"] = transcript

        # Analyze transcript
        analysis = smart_handler.analyze_transcript(transcript)

        # Make decision based on content
        if analysis.has_command_word:
            # Command word - INTERRUPT!
            logger.debug(
                "STOP: command word in '%s'", transcript[:50]
            )
            state["interrupted_speech_id"] = speech_id
            state["last_command_transcript"] = transcript
            original_interrupt()
        elif analysis.has_passive_only:
            # Passive only - SET SKIP FLAG and return
            logger.debug(
                "IGNORE: passive '%s' - agent continues", transcript[:30]
            )
            state["skip_checks"] = True
            # DON'T call original_interrupt() - agent keeps speaking!
        else:
            # Substantive content - interrupt
            logger.debug(
                "STOP: substantive content '%s'", transcript[:50]
            )
            state["interrupted_speech_id"] = speech_id
            original_interrupt()
    
    def patched_on_interim_transcript(
        ev, *, speaking: bool | None
    ) -> None:
        """Check interim transcripts - drop passive, interrupt on command.

        KEY: Skip _user_input_transcribed for passive to prevent
        transcript from showing!
        """
        speech_id = get_speech_id()

        # Already interrupted
        if speech_id and state["interrupted_speech_id"] == speech_id:
            original_on_interim(ev, speaking=speaking)
            return

        if ev.alternatives and is_agent_speaking():
            transcript = ev.alternatives[0].text.strip()

            if not transcript:
                original_on_interim(ev, speaking=speaking)
                return

            analysis = smart_handler.analyze_transcript(transcript)

            if analysis.has_command_word:
                # Command detected - INTERRUPT NOW!
                if state["last_command_transcript"] != transcript:
                    logger.debug("FAST STOP: '%s'", transcript[:30])
                    state["interrupted_speech_id"] = speech_id
                    state["last_command_transcript"] = transcript
                    original_interrupt()
                return

            if analysis.has_passive_only:
                # Passive detected - DROP COMPLETELY
                logger.debug(
                    "INTERIM DROP: passive '%s'", transcript[:30]
                )
                state["skip_checks"] = True
                return

        original_on_interim(ev, speaking=speaking)
    
    def patched_on_final_transcript(
        ev, *, speaking: bool | None = None
    ) -> None:
        """Final transcript handling.

        - If passive while agent speaking: DROP completely
        - Otherwise: process normally
        """
        if ev.alternatives and is_agent_speaking():
            transcript = ev.alternatives[0].text.strip()

            if transcript:
                analysis = smart_handler.analyze_transcript(transcript)

                if analysis.has_passive_only:
                    # Passive while speaking - DROP SILENTLY
                    logger.debug(
                        "DROP: '%s' - continuing seamlessly", transcript[:30]
                    )

                    # KEY: Reset transcript state WITHOUT resetting STT
                    reset_transcript_only()

                    # Reset our internal state for next input
                    state["skip_checks"] = False
                    state["last_transcript"] = ""
                    return

        # Reset state when speech ends or for any final transcript
        state["skip_checks"] = False
        state["last_transcript"] = ""
        if not is_agent_speaking():
            state["interrupted_speech_id"] = None
            state["last_command_transcript"] = ""

        original_on_final(ev, speaking=speaking)
    
    def patched_on_vad_inference_done(ev) -> None:
        """Intercept VAD to prevent interruption when agent is speaking.

        Wait for STT transcript before deciding to interrupt.
        """
        # If we already know it's passive, skip entirely
        if state["skip_checks"]:
            return

        # If agent is speaking, check if we have a transcript yet
        if is_agent_speaking():
            transcript = get_transcript()

            # No transcript yet - skip VAD interruption, wait for STT
            if not transcript:
                return

            # Analyze transcript
            analysis = smart_handler.analyze_transcript(transcript)

            # Check if it's a command
            if analysis.has_command_word:
                # Command word detected - allow interruption!
                logger.debug(
                    "VAD+STT: command '%s' - interrupting", transcript[:30]
                )
                original_on_vad(ev)
                return

            # Passive or unknown - skip interruption
            if analysis.has_passive_only:
                state["skip_checks"] = True
                return

            # Substantive content - allow interruption
            logger.debug(
                "VAD+STT: substantive '%s' - interrupting", transcript[:30]
            )
            original_on_vad(ev)
            return

        # Agent not speaking - process normally
        original_on_vad(ev)
    
    async def patched_on_stt_event(ev):
        """Patch AudioRecognition._on_stt_event to drop passive transcripts.

        This prevents the transcript from being logged or added to
        _audio_transcript.
        """
        from livekit.agents import stt

        # Only process FINAL transcripts while agent is speaking
        if (
            ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT
            and is_agent_speaking()
        ):
            if ev.alternatives:
                transcript = ev.alternatives[0].text.strip()

                if transcript:
                    analysis = smart_handler.analyze_transcript(transcript)

                    if analysis.has_passive_only:
                        # Passive transcript - DROP BEFORE processing!
                        logger.debug(
                            "AUDIO DROP: '%s' - skipped at STT level",
                            transcript[:30],
                        )
                        state["skip_checks"] = False
                        state["last_transcript"] = ""
                        return

        # Not passive or not while agent speaking - process normally
        await original_on_stt_event(ev)

    # Apply patches
    activity._interrupt_by_audio_activity = smart_interrupt_by_audio_activity
    activity.on_interim_transcript = patched_on_interim_transcript
    activity.on_final_transcript = patched_on_final_transcript
    activity.on_vad_inference_done = patched_on_vad_inference_done

    # Patch AudioRecognition if available
    if activity._audio_recognition and original_on_stt_event:
        activity._audio_recognition._on_stt_event = patched_on_stt_event

    logger.info(
        "Patched with V2 logic - NO PAUSE, seamless continuation"
    )

    return smart_handler
