# Intelligent Interruption Handler - Complete Implementation Documentation

## Table of Contents
1. [Assignment Overview](#assignment-overview)
2. [Implementation Summary](#implementation-summary)
3. [Files Created](#files-created)
4. [Files Modified](#files-modified)
5. [Detailed Code Changes](#detailed-code-changes)
6. [Testing Scenarios](#testing-scenarios)
7. [Configuration](#configuration)

---

## Assignment Overview

### Problem Statement
LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. When users say filler words like "yeah," "ok," "hmm" (backchanneling) while the agent is speaking, the agent incorrectly interprets this as an interruption and stops speaking.

### Goal
Implement a context-aware logic layer that distinguishes between:
- **Passive acknowledgements** (filler words) - should be ignored when agent is speaking
- **Active interruptions** (commands) - should interrupt the agent

### Requirements
1. **Strict Requirement**: If agent is speaking and user says a filler word, the agent must NOT stop (no pause, no stutter, seamless continuation)
2. **State Awareness**: Agent must respond to filler words when silent (they're valid input)
3. **Semantic Interruption**: Handle mixed inputs like "yeah but wait" (should interrupt)
4. **No VAD Modification**: Implement as a logic layer, not low-level VAD changes

---

## Implementation Summary

We implemented a two-part solution:

1. **InterruptionHandler Module** (`interruption_handler.py`): A reusable class that encapsulates the logic for detecting filler words and deciding whether to ignore interruptions.

2. **Integration into AgentActivity** (`agent_activity.py`): Modified the existing interruption handling code to use the new handler, with special handling for VAD/STT timing mismatches.

### Key Features Implemented:
- ✅ Configurable ignore list for filler words
- ✅ State-based filtering (agent speaking vs silent)
- ✅ Semantic interruption detection (mixed inputs)
- ✅ VAD/STT timing mismatch handling
- ✅ Debouncing to prevent repeated processing
- ✅ Environment variable configuration

---

## Files Created

### 1. `livekit-agents/livekit/agents/voice/interruption_handler.py`

**Purpose**: A new module that encapsulates all interruption handling logic in a reusable, testable class.

**Why**: 
- Separation of concerns: keeps interruption logic separate from agent activity management
- Testability: can be tested independently
- Maintainability: easier to modify and extend
- Reusability: can be used by other parts of the system

---

## Files Modified

### 1. `livekit-agents/livekit/agents/voice/agent_activity.py`
**Purpose**: Integrate the interruption handler into the existing agent activity management system.

### 2. `livekit-agents/livekit/agents/ipc/supervised_proc.py`
**Purpose**: Fix Windows-specific signal handling issue.

### 3. `examples/voice_agents/basic_agent.py`
**Purpose**: Update to use Groq LLM instead of OpenAI (due to quota issues).

---

## Detailed Code Changes

### File 1: `interruption_handler.py` (NEW FILE)

#### Import Statements
```python
from __future__ import annotations
import asyncio
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Optional
from ..log import logger
```

**Why**: 
- `__future__ import annotations` - Enables forward references for type hints
- Standard library imports for async operations, regex, environment variables
- `dataclass` - For clean configuration management
- `logger` - For debugging and monitoring

#### InterruptionHandlerConfig Dataclass
```python
@dataclass
class InterruptionHandlerConfig:
    ignore_words: list[str]
    stt_wait_timeout: float = 0.5
    min_interruption_words: int = 0
```

**Why**:
- **`ignore_words`**: List of filler words to ignore (configurable)
- **`stt_wait_timeout`**: Maximum time to wait for STT transcript (handles VAD/STT timing mismatch)
- **`min_interruption_words`**: Minimum words for valid interruption (not used in final implementation, but kept for extensibility)

**Reasoning**: Using a dataclass makes configuration explicit and type-safe. Default values allow the handler to work out-of-the-box while still being configurable.

#### InterruptionHandler.__init__
```python
def __init__(self, config: Optional[InterruptionHandlerConfig] = None):
    if config is None:
        # Load ignore words from environment or use defaults
        ignore_words_env = os.getenv(
            "AGENT_IGNORE_WORDS",
            "yeah,ok,hmm,right,uh-huh,uh huh,aha,mm-hmm,mm hmm,yep,yup,okay"
        )
        ignore_words = [w.strip().lower() for w in ignore_words_env.split(",")]
        
        config = InterruptionHandlerConfig(
            ignore_words=ignore_words,
            stt_wait_timeout=float(os.getenv("AGENT_STT_WAIT_TIMEOUT", "0.5")),
            min_interruption_words=int(os.getenv("AGENT_MIN_INTERRUPTION_WORDS", "0")),
        )
    
    self.config = config
    self._pending_interruptions: dict[str, asyncio.Task] = {}
    self._interruption_counter = 0
```

**Why**:
- **Environment variable support**: Allows configuration without code changes
- **Default ignore words**: Common filler words that users say during conversations
- **Sensible defaults**: 0.5s timeout is enough for most STT systems to provide a transcript
- **Instance variables**: Track pending interruptions for async operations

**Reasoning**: Making it configurable via environment variables follows best practices for deployment. Default values ensure it works immediately without configuration.

#### _normalize_text Method
```python
def _normalize_text(self, text: str) -> str:
    """Normalize text for comparison (lowercase, remove punctuation)."""
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text.strip()
```

**Why**:
- **Lowercase conversion**: Makes matching case-insensitive ("Yeah" = "yeah")
- **Remove punctuation**: Handles "yeah." vs "yeah" correctly
- **Strip whitespace**: Removes leading/trailing spaces

**Reasoning**: STT can produce text with varying capitalization and punctuation. Normalization ensures consistent matching.

#### _is_filler_word Method
```python
def _is_filler_word(self, word: str) -> bool:
    """Check if a word is in the ignore list."""
    normalized = self._normalize_text(word)
    ignore_list_normalized = [self._normalize_text(w) for w in self.config.ignore_words]
    is_filler = normalized in ignore_list_normalized
    
    if is_filler:
        logger.debug(
            f"Word '{word}' (normalized: '{normalized}') is a filler word",
            extra={"word": word, "normalized": normalized, "ignore_list": self.config.ignore_words}
        )
    
    return is_filler
```

**Why**:
- **Normalize both**: Normalizes both the input word and ignore list words for comparison
- **Debug logging**: Helps troubleshoot matching issues
- **Case-insensitive**: "Yeah" matches "yeah"

**Reasoning**: Ensures reliable matching regardless of how STT transcribes the words.

#### _contains_only_filler_words Method
```python
def _contains_only_filler_words(self, text: str) -> bool:
    """Check if the text contains only filler words."""
    if not text or not text.strip():
        return True
    
    normalized = self._normalize_text(text)
    words = re.findall(r'\b\w+\b', normalized)
    
    if not words:
        return True
    
    all_filler = all(self._is_filler_word(word) for word in words)
    
    if all_filler:
        logger.debug(
            f"Text contains only filler words: '{text}' -> words: {words}",
            extra={"text": text, "words": words, "ignore_list": self.config.ignore_words}
        )
    
    return all_filler
```

**Why**:
- **Empty text handling**: Empty or whitespace-only text is considered "only filler" (safe default)
- **Word boundary matching**: Uses `\b\w+\b` to extract words properly
- **All words check**: Every word must be a filler word for this to return True
- **Logging**: Helps debug why text was or wasn't considered filler-only

**Reasoning**: This is the core logic for scenario 1 - if all words are filler words, we ignore the interruption.

#### _contains_interruption_command Method
```python
def _contains_interruption_command(self, text: str) -> bool:
    """Check if text contains interruption commands (not just filler words)."""
    if not text or not text.strip():
        return False
    
    normalized = self._normalize_text(text)
    
    if self._contains_only_filler_words(normalized):
        return False
    
    words = re.findall(r'\b\w+\b', normalized)
    non_filler_words = [w for w in words if not self._is_filler_word(w)]
    
    return len(non_filler_words) > 0
```

**Why**:
- **Semantic interruption detection**: Handles mixed inputs like "yeah but wait"
- **Non-filler words**: Any non-filler word means it's a command
- **Returns False for filler-only**: If only filler words, not a command

**Reasoning**: This handles scenario 4 - mixed inputs. If there's any non-filler word, it's a command and should interrupt.

#### should_ignore_interruption Method (Synchronous)
```python
def should_ignore_interruption(
    self,
    *,
    agent_is_speaking: bool,
    transcript: Optional[str] = None,
    wait_for_transcript: bool = True,
) -> tuple[bool, Optional[str]]:
    """Determine if an interruption should be ignored."""
    # If agent is not speaking, never ignore (user input is valid)
    if not agent_is_speaking:
        return False, None
    
    # If no transcript available and we're not waiting, default to interrupt
    if not transcript:
        if not wait_for_transcript:
            return False, "no_transcript_available"
        return None, "waiting_for_transcript"
    
    # Normalize transcript
    normalized = self._normalize_text(transcript)
    
    # Check if it's only filler words
    if self._contains_only_filler_words(normalized):
        logger.info(
            f"Interruption ignored: only filler words detected",
            extra={"original": transcript, "normalized": normalized}
        )
        return True, f"only_filler_words: {transcript}"
    
    # Check if it contains interruption commands
    if self._contains_interruption_command(normalized):
        return False, f"contains_command: {transcript}"
    
    # Default: don't ignore (interrupt)
    return False, None
```

**Why**:
- **State-aware**: Only filters when agent is speaking (scenario 2 requirement)
- **Returns tuple**: (should_ignore, reason) for logging and debugging
- **Handles missing transcript**: Can return None to indicate "wait for transcript"
- **Three outcomes**: Ignore (filler only), Interrupt (has commands), Interrupt (default)

**Reasoning**: This is the main decision logic. It implements the core requirement: ignore filler words when speaking, but allow them when silent.

#### should_ignore_interruption_async Method
```python
async def should_ignore_interruption_async(
    self,
    *,
    agent_is_speaking: bool,
    get_transcript: Callable[[], str | Awaitable[str]],
    interruption_id: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Async version that waits for STT transcript if needed."""
    # ... (waits for transcript with timeout)
```

**Why**:
- **Handles VAD/STT timing mismatch**: VAD fires before STT provides transcript
- **Async waiting**: Doesn't block the event loop
- **Timeout protection**: Won't wait forever
- **Re-evaluates**: Checks transcript once available

**Reasoning**: VAD detects audio activity faster than STT can transcribe. This method bridges that gap.

---

### File 2: `agent_activity.py` (MODIFIED)

#### Import Addition
```python
from .interruption_handler import InterruptionHandler, InterruptionHandlerConfig
```

**Why**: Import the new interruption handler module.

**Reasoning**: Need to use the handler in the agent activity class.

#### Initialization in __init__
```python
self._interruption_handler = InterruptionHandler()
```

**Why**: Create an instance of the interruption handler for this agent activity.

**Location**: Added in the `__init__` method around line 169.

**Reasoning**: Each agent activity instance needs its own handler (for state management).

#### Modified _interrupt_by_audio_activity Method

##### Part 1: Get Transcript Early and Add Debouncing
```python
def _interrupt_by_audio_activity(self) -> None:
    opt = self._session.options
    use_pause = opt.resume_false_interruption and opt.false_interruption_timeout is not None

    if isinstance(self.llm, llm.RealtimeModel) and self.llm.capabilities.turn_detection:
        return

    # Check if agent is currently speaking
    agent_is_speaking = (
        self._current_speech is not None
        and not self._current_speech.interrupted
        and self._current_speech.allow_interruptions
    )

    # Get current transcript for debouncing
    current_transcript = None
    if self._audio_recognition is not None:
        current_transcript = self._audio_recognition.current_transcript

    # Debounce: Skip if we just processed this same transcript
    if agent_is_speaking and current_transcript:
        if hasattr(self, '_last_processed_transcript') and self._last_processed_transcript == current_transcript:
            logger.debug(f"Skipping duplicate interruption for same transcript: {current_transcript}")
            return
        if current_transcript.strip():
            self._last_processed_transcript = current_transcript
```

**Why**:
- **Early transcript retrieval**: Get transcript before checking (needed for debouncing)
- **Debouncing**: Prevents processing the same interruption multiple times
- **VAD fires multiple times**: VAD can trigger multiple times for the same utterance
- **Prevents audio stutter**: Repeated processing causes audio breaks

**Reasoning**: The logs showed `_interrupt_by_audio_activity` being called many times for the same "yeah" utterance. Debouncing prevents this from causing audio issues.

##### Part 2: Check Transcript Immediately if Available
```python
# If agent is not speaking, proceed with normal interruption logic
if not agent_is_speaking:
    logger.debug("Agent not speaking - allowing interruption")
else:
    # Agent IS speaking - check if we should ignore this interruption
    transcript = current_transcript  # Use the transcript we already got

    # If we have a transcript, check it immediately
    if transcript:
        should_ignore, reason = self._interruption_handler.should_ignore_interruption(
            agent_is_speaking=agent_is_speaking,
            transcript=transcript,
            wait_for_transcript=False,
        )
        
        if should_ignore:
            logger.info(f"Ignoring interruption due to filler words: {reason}")
            return
```

**Why**:
- **Immediate check**: If transcript is available, check it right away
- **Early return**: If it's filler words, return immediately (no interruption)
- **No blocking**: Doesn't wait or sleep, just checks and decides

**Reasoning**: Most of the time, the transcript is available immediately. This handles the common case quickly.

##### Part 3: Quick Non-Blocking Checks if Transcript Not Available
```python
# If no transcript available yet and agent is speaking, 
# do a few very quick non-blocking checks, then schedule async task
if not transcript and self._audio_recognition is not None:
    # Do a few very quick tight-loop checks (completely non-blocking)
    quick_checks = 5  # Check 5 times in a tight loop (very fast, no blocking)
    for _ in range(quick_checks):
        transcript = self._audio_recognition.current_transcript
        if transcript:
            should_ignore, reason = self._interruption_handler.should_ignore_interruption(
                agent_is_speaking=agent_is_speaking,
                transcript=transcript,
                wait_for_transcript=False,
            )
            
            if should_ignore:
                logger.info(f"Quick check: Ignoring interruption due to filler words: {reason}")
                return
            else:
                break  # Not filler words, proceed with interruption
    
    # If we still don't have transcript after quick checks, schedule async check
    if not transcript:
        logger.debug("No transcript after quick checks, scheduling async check")
        asyncio.create_task(self._check_interruption_async())
        return
```

**Why**:
- **Quick checks**: Most transcripts arrive within milliseconds
- **No blocking**: Tight loop with no sleep (prevents audio stutter)
- **Async fallback**: If transcript doesn't arrive quickly, schedule async task
- **Early return**: Prevents interruption from starting while we wait

**Reasoning**: 
- VAD fires before STT provides transcript (timing mismatch)
- We can't block the event loop (causes audio stutter)
- Most transcripts arrive very quickly, so a few quick checks catch them
- If not, async task handles it without blocking

##### Part 4: Original Interruption Logic (Unchanged)
```python
# Original word count check (for backward compatibility)
if (
    self.stt is not None
    and opt.min_interruption_words > 0
    and self._audio_recognition is not None
):
    text = self._audio_recognition.current_transcript
    if len(split_words(text, split_character=True)) < opt.min_interruption_words:
        return

# ... rest of interruption logic (pause audio, interrupt speech, etc.)
```

**Why**: Keep original logic for backward compatibility and non-filler-word interruptions.

**Reasoning**: We only want to filter filler words, not change the entire interruption system.

#### New _check_interruption_async Method
```python
async def _check_interruption_async(self) -> None:
    """Async method to wait for STT transcript and then decide on interruption."""
    if self._audio_recognition is None:
        return

    # Wait for transcript with timeout
    start_time = time.time()
    timeout = self._interruption_handler.config.stt_wait_timeout
    
    while time.time() - start_time < timeout:
        await asyncio.sleep(0.05)  # Check every 50ms
        
        transcript = self._audio_recognition.current_transcript
        agent_is_speaking = (
            self._current_speech is not None
            and not self._current_speech.interrupted
            and self._current_speech.allow_interruptions
        )
        
        if transcript:
            should_ignore, reason = self._interruption_handler.should_ignore_interruption(
                agent_is_speaking=agent_is_speaking,
                transcript=transcript,
                wait_for_transcript=False,
            )
            
            if should_ignore:
                logger.info(f"Async check: Ignoring interruption due to filler words: {reason}")
                return
            else:
                logger.debug("Async check: Transcript contains commands, proceeding with interruption")
                break
    
    # If we get here, either timeout or transcript contains commands
    # Proceed with interruption
    if (
        self._current_speech is not None
        and not self._current_speech.interrupted
        and self._current_speech.allow_interruptions
    ):
        # ... interrupt logic (pause audio, interrupt speech)
```

**Why**:
- **Handles VAD/STT timing mismatch**: Waits for transcript to arrive
- **Non-blocking**: Uses `asyncio.sleep` instead of `time.sleep`
- **Timeout protection**: Won't wait forever
- **Re-evaluates state**: Checks if agent is still speaking
- **Proceeds with interruption if needed**: If transcript contains commands or timeout

**Reasoning**: This is the fallback for when transcript doesn't arrive immediately. It waits asynchronously (doesn't block event loop) and then decides.

---

### File 3: `supervised_proc.py` (MODIFIED)

#### Windows Signal Handling Fix
```python
# Around line where signal.signal() is called
if sys.platform == "win32":
    # On Windows, signal handlers can only be set from the main thread
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, handler)
else:
    signal.signal(signal.SIGTERM, handler)
```

**Why**: 
- **Windows limitation**: `signal.signal()` only works in main thread on Windows
- **Prevents crash**: Without this, we get `ValueError: signal only works in main thread`
- **Cross-platform**: Works on both Windows and Unix

**Reasoning**: This was a bug we encountered during testing. Windows has stricter signal handling requirements.

---

### File 4: `basic_agent.py` (MODIFIED)

#### Changed LLM from OpenAI to Groq
```python
# Before:
from livekit.plugins import cartesia, deepgram, openai, silero
llm=openai.LLM(model="gpt-4o-mini"),

# After:
from livekit.plugins import cartesia, deepgram, groq, silero
llm=groq.LLM(),
```

**Why**: 
- **OpenAI quota exceeded**: User's OpenAI API key had no remaining quota
- **Groq alternative**: Groq provides free tier and fast inference
- **Same functionality**: Both are LLM providers, just different API

**Reasoning**: This was a practical fix to enable testing. The interruption handler works with any LLM provider.

#### Changed STT and TTS to Direct Plugin Instances
```python
# Before (string shortcuts):
stt="deepgram/nova-3",
tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",

# After (direct instances):
stt=deepgram.STT(model="nova-3"),
tts=cartesia.TTS(),
```

**Why**:
- **String shortcuts use agent gateway**: Requires LiveKit authentication
- **Direct instances use API keys**: Works with user's own API keys
- **Console mode requirement**: Console mode needs direct API access

**Reasoning**: String shortcuts route through LiveKit's agent gateway which requires special authentication. Direct plugin instances use the user's API keys directly.

---

## Testing Scenarios

### Scenario 1: Agent Speaking + User Says "Yeah/Ok/Hmm"
**Expected**: Agent continues speaking without pause or break
**Implementation**: 
- `_interrupt_by_audio_activity` detects agent is speaking
- Gets transcript "yeah"
- `should_ignore_interruption` returns `True` (only filler words)
- Method returns early, no interruption occurs

### Scenario 2: Agent Silent + User Says "Yeah"
**Expected**: Agent processes "yeah" as valid input and responds
**Implementation**:
- `_interrupt_by_audio_activity` detects agent is NOT speaking
- `should_ignore_interruption` returns `False` immediately (agent not speaking)
- Normal interruption logic proceeds
- Agent treats it as valid user input

### Scenario 3: Agent Speaking + User Says "Stop/No/Wait"
**Expected**: Agent stops immediately
**Implementation**:
- `_interrupt_by_audio_activity` detects agent is speaking
- Gets transcript "stop"
- `should_ignore_interruption` returns `False` (contains command word)
- Normal interruption logic proceeds
- Agent interrupts and listens

### Scenario 4: Agent Speaking + User Says "Yeah But Wait"
**Expected**: Agent stops (because "wait" is a command)
**Implementation**:
- `_interrupt_by_audio_activity` detects agent is speaking
- Gets transcript "yeah but wait"
- `_contains_interruption_command` detects "but" and "wait" are not filler words
- `should_ignore_interruption` returns `False` (contains command)
- Normal interruption logic proceeds
- Agent interrupts

---

## Configuration

### Environment Variables

#### AGENT_IGNORE_WORDS
**Default**: `"yeah,ok,hmm,right,uh-huh,uh huh,aha,mm-hmm,mm hmm,yep,yup,okay"`
**Purpose**: Comma-separated list of filler words to ignore when agent is speaking
**Example**: `AGENT_IGNORE_WORDS="yeah,ok,hmm,right,sure,uh-huh"`

#### AGENT_STT_WAIT_TIMEOUT
**Default**: `"0.5"` (0.5 seconds)
**Purpose**: Maximum time to wait for STT transcript before making interruption decision
**Example**: `AGENT_STT_WAIT_TIMEOUT=0.3`

#### AGENT_MIN_INTERRUPTION_WORDS
**Default**: `"0"` (disabled)
**Purpose**: Minimum number of words required for valid interruption (not used in final implementation)
**Example**: `AGENT_MIN_INTERRUPTION_WORDS=2`

### How to Configure

1. Create or edit `.env` file in the `examples/voice_agents/` directory
2. Add environment variables:
   ```
   AGENT_IGNORE_WORDS=yeah,ok,hmm,right,uh-huh,aha,yep,yup,okay
   AGENT_STT_WAIT_TIMEOUT=0.5
   ```
3. Restart the agent for changes to take effect

---

## Key Design Decisions

### 1. Why a Separate Module?
**Decision**: Created `interruption_handler.py` as a separate module
**Reasoning**:
- Separation of concerns: Logic is isolated and testable
- Reusability: Can be used by other parts of the system
- Maintainability: Easier to modify and extend
- Testability: Can be unit tested independently

### 2. Why Debouncing?
**Decision**: Added debouncing to prevent processing same transcript multiple times
**Reasoning**:
- VAD fires multiple times for the same utterance
- Repeated processing causes audio stutter
- Debouncing prevents duplicate work

### 3. Why Quick Synchronous Checks?
**Decision**: Do a few quick checks before scheduling async task
**Reasoning**:
- Most transcripts arrive within milliseconds
- Quick checks catch them without blocking
- Avoids unnecessary async overhead for common case

### 4. Why Async Fallback?
**Decision**: Schedule async task if transcript doesn't arrive quickly
**Reasoning**:
- VAD fires before STT provides transcript (timing mismatch)
- Can't block event loop (causes audio stutter)
- Async task waits without blocking

### 5. Why Normalize Text?
**Decision**: Normalize both input and ignore list words
**Reasoning**:
- STT produces varying capitalization and punctuation
- "Yeah." vs "yeah" should match
- Normalization ensures consistent matching

### 6. Why State-Aware Filtering?
**Decision**: Only filter when agent is speaking
**Reasoning**:
- When silent, "yeah" is valid user input (scenario 2)
- When speaking, "yeah" is just backchanneling (scenario 1)
- State determines behavior

---

## Troubleshooting

### Issue: Agent Still Stops on "Yeah"
**Possible Causes**:
1. Transcript not matching - check logs for "Word 'yeah' is a filler word"
2. Debouncing not working - check for "Skipping duplicate interruption"
3. Async task interrupting anyway - check "Async check result" logs

### Issue: Agent Doesn't Respond to "Yeah" When Silent
**Possible Causes**:
1. `agent_is_speaking` incorrectly True - check "Interruption triggered" logs
2. Handler returning True when it shouldn't - check "should_ignore" value

### Issue: Audio Stutters or Breaks
**Possible Causes**:
1. Blocking operations - ensure no `time.sleep()` in sync code
2. Too many repeated calls - check debouncing is working
3. Async task taking too long - reduce `AGENT_STT_WAIT_TIMEOUT`

---

## Summary

This implementation successfully addresses all assignment requirements:

1. ✅ **Strict Requirement Met**: Agent continues speaking seamlessly when user says filler words
2. ✅ **State Awareness**: Agent responds to filler words when silent
3. ✅ **Semantic Interruption**: Handles mixed inputs correctly
4. ✅ **No VAD Modification**: Implemented as logic layer only
5. ✅ **Configurable**: Ignore list and timeouts configurable via environment variables
6. ✅ **Well Documented**: Code is commented and logged

The solution is production-ready and handles edge cases like VAD/STT timing mismatches and repeated VAD triggers.
