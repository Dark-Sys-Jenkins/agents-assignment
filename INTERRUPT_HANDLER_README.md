# LiveKit Intelligent Interruption Handler

## Overview

This feature adds context-aware interruption handling to LiveKit voice agents. It allows the agent to distinguish between passive acknowledgements (backchanneling) like "yeah", "ok", "hmm" and active interruptions like "stop", "wait", "no".

## The Problem

LiveKit's default VAD is too sensitive to user feedback. When a user says "yeah" or "ok" to show they're listening, the agent interprets this as an interruption and stops speaking abruptly.

## The Solution

A logic layer that filters interruptions based on:
- **Agent State**: Is the agent currently speaking or silent?
- **Transcript Content**: Is this a filler word or meaningful content?

## Logic Matrix

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE** - Agent continues speaking |
| "Wait / Stop / No" | Speaking | **INTERRUPT** - Agent stops immediately |
| "Yeah / Ok / Hmm" | Silent | **RESPOND** - Process as valid input |
| "Yeah but wait" | Speaking | **INTERRUPT** - Contains meaningful content |

## Quick Start

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/agents-assignment.git
cd agents-assignment
pip install -e ./livekit-agents
```

### Basic Usage

```python
from livekit.agents import AgentSession

# Backchannel filter is enabled by default
session = AgentSession(
    stt=your_stt,
    llm=your_llm,
    tts=your_tts,
)
```

### Custom Word Lists

```python
session = AgentSession(
    stt=your_stt,
    llm=your_llm,
    tts=your_tts,
    backchannel_filter_enabled=True,
    backchannel_words=frozenset(["yeah", "ok", "hmm", "sure", "right"]),
    interrupt_words=frozenset(["stop", "wait", "no", "help"]),
)
```

### Environment Variables

```bash
# Add custom backchannel words
export BACKCHANNEL_WORDS="yep,yup,aye,roger"

# Add custom interrupt words
export INTERRUPT_WORDS="cancel,abort,quit"

# Disable the filter
export BACKCHANNEL_FILTER_ENABLED=false
```

## How It Works

### Architecture

```
User Speech Detected (VAD)
        |
        v
  Is agent speaking?
        |
    +---+---+
    No      Yes
    |         |
    v         v
 RESPOND   Has transcript?
              |
          +---+---+
          No      Yes
          |         |
          v         v
       ALLOW    Analyze words
      (normal)      |
              +-----+-----+
              |           |
         Interrupt    Only filler
           word?        words?
              |           |
              v           v
          INTERRUPT    IGNORE
```

### Key Design Decisions

1. **No VAD Modification** - Works as a logic layer, doesn't touch low-level VAD
2. **Real-time Processing** - Minimal latency, decisions made as soon as transcript available
3. **Seamless Continuation** - Agent doesn't pause/stutter, truly continues speaking
4. **Configurable** - Word lists customizable via code or environment variables

## Files Modified

| File | Change |
|------|--------|
| `livekit-agents/livekit/agents/voice/interruption_filter.py` | NEW - Filter logic |
| `livekit-agents/livekit/agents/voice/agent_activity.py` | Modified `_interrupt_by_audio_activity()` |
| `livekit-agents/livekit/agents/voice/agent_session.py` | Added configuration options |

## Testing

### Run the Demo

```bash
python demo_interruption_filter.py
```

This generates a log transcript showing all filter decisions.

### Test Scenarios

1. **Long Explanation Test**: Ask agent to explain something, say "yeah, okay, uh-huh" while it speaks. Agent should continue without stopping.

2. **Passive Affirmation Test**: Let agent ask a question and go silent, say "yeah". Agent should respond.

3. **Interruption Test**: While agent is speaking, say "stop". Agent should stop immediately.

4. **Mixed Input Test**: While agent is speaking, say "yeah but wait". Agent should stop (contains "but wait").

## Default Word Lists

**Backchannel Words** (ignored while speaking):
```
yeah, yes, yep, yup, ok, okay, hmm, mhm, uh-huh, right,
alright, sure, ah, aha, oh, uh, um, gotcha, cool, nice,
great, good, fine, true, exactly, absolutely, indeed
```

**Interrupt Words** (always trigger interruption):
```
stop, wait, hold, pause, no, nope, wrong, actually, what,
why, how, when, where, who, can, could, please, help,
explain, repeat, but, however, let, tell, hello, hi, hey
```

## Proof of Implementation

See `PROOF_TRANSCRIPT.txt` for a log demonstrating:
- Agent ignoring "yeah" while talking
- Agent responding to "yeah" when silent
- Agent stopping for "stop"
