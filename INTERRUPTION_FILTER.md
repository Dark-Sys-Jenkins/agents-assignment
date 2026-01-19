# Intelligent Interruption Handling - Implementation Documentation

## Overview

This implementation solves the LiveKit Intelligent Interruption Handling Challenge by adding a **context-aware filler word detection layer** that prevents false interruptions during agent speech while maintaining responsiveness to genuine user commands.

### The Problem Solved
When an AI agent is explaining something important, LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. If the user says "yeah," "ok," "aha," or "hmm" (backchanneling) to indicate they are listening, the agent interprets this as an interruption and abruptly stops speaking.

### The Solution
A logic layer that is context-aware - the agent distinguishes between a "passive acknowledgement" and an "active interruption" based on whether the agent is currently speaking or silent.

---

## Core Logic Matrix

| User Input | Agent State | Desired Behavior | Implementation |
|------------|-------------|------------------|----------------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE**: Agent continues without pausing | ✅ Implemented |
| "Wait / Stop / No" | Speaking | **INTERRUPT**: Agent stops immediately | ✅ Implemented |
| "Yeah / Ok / Hmm" | Silent | **RESPOND**: Treat as valid input | ✅ Implemented |
| "Start / Hello" | Silent | **RESPOND**: Normal conversation | ✅ Implemented |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AUDIO PROCESSING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User Speech → VAD (fast) → STT (slower) → InterruptionFilter → Action │
│                     │                              │                     │
│                     │                              ▼                     │
│                     │                    ┌─────────────────┐             │
│                     │                    │ Is Agent        │             │
│                     │                    │ Speaking?       │             │
│                     │                    └────────┬────────┘             │
│                     │                      YES    │   NO                 │
│                     │                        ▼    │    ▼                 │
│                     │               ┌─────────────┴──────────┐           │
│                     │               │ Filter ACTIVE          │           │
│                     │               │ Check each word:       │           │
│                     │               │ - Filler? → WAIT       │           │
│                     │               │ - Non-filler? → INTR   │───────►   │
│                     │               │ - End of speech?       │           │
│                     │               │   All fillers → IGNORE │           │
│                     │               └────────────────────────┘           │
│                     │                              │                     │
│                     └──────► PASS_THROUGH ────────►│                     │
│                         (Process normally)          ▼                    │
│                                              Agent Response              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. `InterruptionFilter` Class
**Location**: `livekit-agents/livekit/agents/voice/interruption_filter.py`

The core filter implementing accumulation-based filler word detection:

```python
from livekit.agents.voice import InterruptionFilter, FilterDecision

# Create filter (uses defaults or custom words)
filter = InterruptionFilter(filler_words={"yeah", "ok", "hmm"})

# When user starts speaking - context-aware activation
filter.on_speech_start(agent_is_speaking=True)  # Activates filter
filter.on_speech_start(agent_is_speaking=False) # PASS_THROUGH mode

# As transcript updates arrive (from STT)
result = filter.on_transcript_update("yeah")        # Returns WAIT
result = filter.on_transcript_update("yeah ok")     # Returns WAIT
result = filter.on_transcript_update("yeah ok but") # Returns INTERRUPT!

# When user stops speaking
result = filter.on_speech_end()  # IGNORE if all fillers, else INTERRUPT
```

### 2. `FilterDecision` Enum
Four possible decisions:
- **WAIT**: Keep accumulating, no decision yet (filler detected)
- **INTERRUPT**: Non-filler word detected, interrupt the agent
- **IGNORE**: All words were fillers, ignore this speech segment
- **PASS_THROUGH**: Filter not active (agent silent), process input normally

### 3. Default Filler Words
A comprehensive list of ~100 filler words including:
- **Affirmations**: yeah, yep, yes, ok, okay, sure, right, alright
- **Backchannels**: hmm, mm, mhm, uh-huh, aha
- **Hesitations**: uh, um, er, eh
- **Continuers**: go on, got it, gotcha, understood, makes sense

### 4. Integration Points

**`audio_recognition.py`**:
- Filters filler words at the STT source level
- Drops filler transcripts completely when agent is speaking
- LLM never sees filtered fillers

**`agent_activity.py`**:
- Tracks agent speaking state via `_is_agent_speaking()`
- Blocks VAD-only pauses when filter is active
- Passes filter decisions to interrupt logic

---

## Running the Demo Agent

```bash
# 1. Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - LIVEKIT_URL
# - LIVEKIT_API_KEY
# - LIVEKIT_API_SECRET
# - OPENAI_API_KEY

# 2. Run the demo agent
python demo_agent.py dev

# 3. Connect via LiveKit Agents Playground
# https://agents-playground.livekit.io/
```

---

## Test Scenarios (Proof of Functionality)

### Scenario 1: The Long Explanation
- **Context**: Agent is reading a long paragraph
- **User Action**: Says "Okay... yeah... uh-huh" while Agent is talking
- **Expected**: Agent audio does NOT break, ignores user input
- **Filter Output**: `WAIT` → `WAIT` → `WAIT` → `IGNORE`

### Scenario 2: The Passive Affirmation
- **Context**: Agent asks "Are you ready?" and goes silent
- **User Action**: Says "Yeah"
- **Expected**: Agent processes "Yeah" as an answer
- **Filter Output**: `PASS_THROUGH` (filter inactive)

### Scenario 3: The Correction
- **Context**: Agent is counting "One, two, three..."
- **User Action**: Says "No stop"
- **Expected**: Agent cuts off immediately
- **Filter Output**: `INTERRUPT` (on "no")

### Scenario 4: The Mixed Input
- **Context**: Agent is speaking
- **User Action**: Says "Yeah okay but wait"
- **Expected**: Agent stops (because "but" is not a filler)
- **Filter Output**: `WAIT` → `WAIT` → `INTERRUPT` (on "but")

---

## Configuration

### Custom Filler Words

Via `AgentSession`:
```python
session = AgentSession(
    vad=silero.VAD.load(),
    stt=openai.STT(),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=openai.TTS(),
    filler_words=["totally", "absolutely", "right", "exactly"],  # Custom list
)
```

Via `create_interruption_filter`:
```python
from livekit.agents.voice import create_interruption_filter

# Extend defaults with custom words
filter = create_interruption_filter(
    filler_words=["custom1", "custom2"],
    extend_defaults=True  # Adds to DEFAULT_FILLER_WORDS
)

# Replace defaults entirely
filter = create_interruption_filter(
    filler_words=["only", "these", "words"],
    extend_defaults=False  # Uses ONLY provided words
)
```

---

## Technical Details

### Why Accumulation-Based?
VAD is faster than STT, creating a timing gap. The filter handles this "false start" by:
1. Activating on VAD START (if agent speaking)
2. Accumulating transcript as STT results arrive
3. Checking each new word - INTERRUPT immediately on non-filler
4. If VAD END reached with only fillers → IGNORE entire segment

### Zero-Pause Behavior
The `should_block_pause` property enables seamless continuation:
```python
@property
def should_block_pause(self) -> bool:
    """True if audio pause should be blocked."""
    return self._is_active and not self._decision_made
```

### Pattern Matching for Variants
Handles real-world transcription variations:
- Case insensitive: "Yeah", "YEAH", "yeah" → all match
- Punctuation stripped: "Yeah.", "Yeah," → both match
- Regex patterns for common variants:
  - `m+h?m*` matches: mm, mmm, mhm, mmhm
  - `y[ae]+h?` matches: ya, yah, yea, yeah, yeaah
  - `o?k+[ae]?y?` matches: ok, okay, okey, okk

---

## Files Modified

| File | Change |
|------|--------|
| `livekit-agents/livekit/agents/voice/interruption_filter.py` | **NEW** - Core filter implementation |
| `livekit-agents/livekit/agents/voice/__init__.py` | Export filter classes |
| `livekit-agents/livekit/agents/voice/agent_session.py` | Add `filler_words` option |
| `livekit-agents/livekit/agents/voice/agent_activity.py` | Integrate filter in hooks |
| `livekit-agents/livekit/agents/voice/audio_recognition.py` | Filter at STT source level |
| `livekit-agents/tests/test_interruption_filter.py` | **NEW** - Comprehensive tests |
| `demo_agent.py` | **NEW** - Demo agent for testing |

---

## Proof Logs

See `proof_log_FINAL_FIX.txt` for logs demonstrating:
- `[PROOF] DROPPED FILLER at source: 'yeah' - Agent continues, LLM unaware`
- `[PROOF] NON-FILLER detected: 'stop' - Proceeding to interrupt agent`
- `[PROOF] Agent silent, processing: 'yeah'`
- `[PROOF] BLOCKED PAUSE - Agent is speaking (VAD-only)`
- `[PROOF] VAD Inference SKIPPING interrupt - Filter IS active`

---

## Run Tests

```bash
cd livekit-agents
python -m pytest tests/test_interruption_filter.py -v
```

All tests verify the four core scenarios plus edge cases:
- Case insensitivity
- Punctuation handling
- Filter reset between speech segments
- Interrupt decision persistence
- Force interrupt capability

---

## Summary

This implementation provides a **zero-latency, context-aware interruption filter** that:

✅ **Ignores fillers during agent speech** - No pause, no stutter, seamless continuation  
✅ **Processes fillers when agent is silent** - "Yeah" becomes valid input  
✅ **Immediately interrupts on commands** - "Stop", "Wait", "No" cut through  
✅ **Handles mixed input** - "Yeah okay but wait" triggers on "but"  
✅ **Configurable word list** - Extend or replace defaults  
✅ **No VAD modification** - Implemented as a logic layer in the event loop  
✅ **Real-time latency** - Simple set lookup + regex, no ML calls  
