from __future__ import annotations

import asyncio
import contextvars
import heapq
import json
import time
from collections.abc import AsyncIterable, Coroutine, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Union, cast

from opentelemetry import context as otel_context, trace

from livekit import rtc
from livekit.agents.llm.realtime import MessageGeneration
from livekit.agents.metrics.base import Metadata

from .. import llm, stt, tts, utils, vad
from ..llm.tool_context import (
    StopResponse,
    ToolFlag,
    _FunctionToolInfo,
    _RawFunctionToolInfo,
    get_function_info,
    get_raw_function_info,
    is_function_tool,
    is_raw_function_tool,
)
from ..log import logger
from ..metrics import (
    EOUMetrics,
    LLMMetrics,
    RealtimeModelMetrics,
    STTMetrics,
    TTSMetrics,
    VADMetrics,
)
from ..telemetry import trace_types, tracer, utils as trace_utils
from ..tokenize.basic import split_words
from ..types import NOT_GIVEN, FlushSentinel, NotGivenOr

# =============================================================================
# BACKCHANNEL WORD FILTERING
# These words are ignored when the agent is speaking to prevent unwanted interruptions
# =============================================================================
BACKCHANNEL_WORDS = {
    "yeah", "yea", "yes", "yep", "yup",
    "ok", "okay", "alright", "aight",
    "hmm", "hm", "mhm", "mmhmm", "uh-huh", "uhuh", "uh", "huh",
    "right", "sure", "gotcha",
    "aha", "ah", "oh", "ooh",
    "mm", "mhmm", "mmm", "hey"
}

# Command words that ALWAYS trigger interruption even during agent speech
COMMAND_WORDS = {
    "stop", "wait", "hold", "pause", "no", "nope", "don't"
}

# Track the last processed transcript to extract delta
_last_processed_transcript: str = ""

def _extract_words(text: str) -> list:
    """Extract words from text, removing punctuation."""
    import re
    if not text:
        return []
    normalized = text.lower().strip()
    return [w for w in re.sub(r'[^\w\s-]', ' ', normalized).split() if w]

def _get_transcript_delta(full_transcript: str) -> str:
    """
    Get only the NEW portion of the transcript since the last processed turn.
    This is crucial for detecting backchannel in accumulated transcripts.
    """
    global _last_processed_transcript
    
    if not full_transcript:
        return ""
    
    # Normalize both transcripts
    full_words = _extract_words(full_transcript)
    last_words = _extract_words(_last_processed_transcript)
    
    if not full_words:
        return ""
    
    if not last_words:
        # No previous transcript, return last few words (typical backchannel length)
        return " ".join(full_words[-3:])
    
    # Find where the new words start
    # The new words are whatever comes AFTER the last processed words
    last_len = len(last_words)
    full_len = len(full_words)
    
    if full_len <= last_len:
        # Nothing new or same length, return last few words
        return " ".join(full_words[-3:])
    
    # Extract delta (new words only)
    delta_words = full_words[last_len:]
    return " ".join(delta_words)

def _update_last_transcript(transcript: str) -> None:
    """Update the last processed transcript."""
    global _last_processed_transcript
    _last_processed_transcript = transcript

def _is_backchannel_only(text: str) -> bool:
    """Check if the transcript contains only backchannel words."""
    if not text or not text.strip():
        return True
    
    words = _extract_words(text)
    
    if not words:
        return True
    
    # Check for command words first - these always interrupt
    for word in words:
        if word in COMMAND_WORDS:
            return False  # Contains command, NOT backchannel-only
    
    # Check if ALL words are backchannel
    for word in words:
        if word in BACKCHANNEL_WORDS:
            continue
        # Handle hyphenated words like "uh-huh"
        if '-' in word:
            parts = word.split('-')
            if all(p in BACKCHANNEL_WORDS for p in parts if p):
                continue
        # Word is not backchannel
        return False
    
    return True

def _check_backchannel_delta(full_transcript: str) -> bool:
    """
    Check if the DELTA (new words) in the transcript is backchannel-only.
    Returns True if delta is backchannel, False if it should interrupt.
    """
    delta = _get_transcript_delta(full_transcript)
    
    if not delta:
        # No new words, treat as backchannel (don't interrupt)
        return True
    
    is_bc = _is_backchannel_only(delta)
    
    if is_bc:
        logger.info(
            f"🛡️ [DELTA FILTER] Transcript delta '{delta}' is backchannel - blocking turn"
        )
    else:
        logger.debug(
            f"✅ [DELTA FILTER] Transcript delta '{delta}' is NOT backchannel - allowing turn"
        )
    
    return is_bc

# =============================================================================

@dataclass
class _QueuedGeneration:
    voice_task: VoiceTask
    user_message: llm.ChatMessage
    info: _PreemptiveGenerationInfo
    chat_ctx: llm.ChatContext
    tools: list[llm.FunctionTool | llm.RawFunctionTool]
    tool_choice: llm.ToolChoice | None
    created_at: float

class VoiceAgentCore(RecognitionHooks):
    def __init__(self, agent: Agent, sess: AgentSession) -> None:
        self._agent, self._session = agent, sess
        self._rt_session: llm.RealtimeSession | None = None
        self._realtime_spans: utils.BoundedDict[str, trace.Span] | None = None
        self._audio_processor: AudioRecognition | None = None
        self._lock = asyncio.Lock()
        self._tool_choice: llm.ToolChoice | None = None

        self._started = False
        self._closed = False
        self._scheduling_paused = True

        self._active_voice_task: VoiceTask | None = None
        self._task_queue: list[tuple[int, float, VoiceTask]] = []

        # for false interruption handling
        self._paused_voice_task: VoiceTask | None = None
        self._false_interruption_timer: asyncio.TimerHandle | None = None
        self._interrupt_paused_task: asyncio.Task[None] | None = None

        self._queue_updated = asyncio.Event()

        self._scheduling_task: asyncio.Task[None] | None = None
        self._user_turn_completed_task: asyncio.Task[None] | None = None
        self._voice_tasks: list[asyncio.Task[Any]] = []

        self._queued_generation: _QueuedGeneration | None = None

        self._drain_blocked_tasks: list[asyncio.Task[Any]] = []
        self._mcp_tools: list[mcp.MCPTool] = []

        self._on_enter_task: asyncio.Task | None = None
        self._on_exit_task: asyncio.Task | None = None

        # ... rest of the initialization ...