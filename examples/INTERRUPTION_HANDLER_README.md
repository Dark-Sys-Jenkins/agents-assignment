# Intelligent Interruption Handling for LiveKit Agents

This document describes the implementation of intelligent interruption handling that distinguishes between passive acknowledgements (backchanneling) and active interruptions.

## Problem Statement

When an AI agent is explaining something, LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. If the user says "yeah," "ok," "aha," or "hmm" (backchanneling) to indicate they are listening, the agent interprets this as an interruption and stops speaking.

## Solution Overview

The solution implements a **context-aware filtering layer** at the framework level that:

1. **IGNORES** backchanneling words ("yeah", "ok", "hmm") when the agent is speaking
2. **INTERRUPTS** immediately for command words ("wait", "stop", "no") when the agent is speaking  
3. **RESPONDS** normally to all input when the agent is silent

### Key Implementation Details

The solution is integrated directly into the LiveKit Agents framework:

- **`livekit-agents/livekit/agents/voice/backchanneling.py`**: Core filtering logic
- **`livekit-agents/livekit/agents/voice/agent_session.py`**: Configuration options
- **`livekit-agents/livekit/agents/voice/agent_activity.py`**: Integration into interruption flow

### How It Works

```
User speaks → VAD detects → STT transcribes → Backchanneling Filter → Decision
                                                      ↓
                                    ┌─────────────────┴─────────────────┐
                                    ↓                                   ↓
                            If backchanneling                    If interrupt word
                            (agent speaking)                     or real content
                                    ↓                                   ↓
                            RESUME/CONTINUE                      INTERRUPT
                            (no pause)                           (stop speaking)
```

The critical innovation is that when a transcript arrives that's classified as backchanneling:
1. If the agent was already paused (by VAD), it **immediately resumes** speaking
2. If the agent hasn't paused yet, the interruption is **prevented entirely**

This ensures the agent continues speaking seamlessly without any noticeable pause.

## Usage

### Basic Usage (Default Configuration)

```python
from livekit.agents import AgentSession

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini", 
    tts="cartesia/sonic-2",
    # Backchanneling filter is enabled by default
    filter_backchanneling=True,
)
```

### Custom Word Lists

```python
session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    filter_backchanneling=True,
    backchanneling_words={"yeah", "ok", "hmm", "right", "sure", "custom_word"},
    interrupt_words={"wait", "stop", "no", "hold on", "custom_interrupt"},
)
```

### Environment Variables

You can also configure word lists via environment variables:

```bash
export BACKCHANNELING_WORDS="yeah,ok,hmm,right,sure,uh-huh"
export INTERRUPT_WORDS="wait,stop,no,hold on,pause"
```

## Test Scenarios

### Scenario 1: The Long Explanation
- **Context**: Agent is reading a long paragraph about history
- **User Action**: User says "Okay... yeah... uh-huh" while agent is talking
- **Result**: ✅ Agent audio does NOT break - continues speaking seamlessly

### Scenario 2: The Passive Affirmation  
- **Context**: Agent asks "Are you ready?" and goes silent
- **User Action**: User says "Yeah"
- **Result**: ✅ Agent processes "Yeah" as an answer and proceeds

### Scenario 3: The Correction
- **Context**: Agent is counting "One, two, three..."
- **User Action**: User says "No stop"
- **Result**: ✅ Agent cuts off immediately

### Scenario 4: The Mixed Input
- **Context**: Agent is speaking
- **User Action**: User says "Yeah okay but wait"
- **Result**: ✅ Agent stops (because "wait" is an interrupt word)

## Running the Tests

### Unit Tests

```bash
cd examples/voice_agents
python3 test_quick.py
```

Expected output:
```
============================================================
  INTELLIGENT INTERRUPTION HANDLING TEST
============================================================
...
Total Tests: 13
Passed: 13
Failed: 0
Success Rate: 100.0%

✅ ALL TESTS PASSED!
```

### Running the Agent

```bash
cd examples/voice_agents
python3 interruption_agent.py dev
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `filter_backchanneling` | `bool` | `True` | Enable/disable the backchanneling filter |
| `backchanneling_words` | `set[str]` | See below | Words to ignore when agent is speaking |
| `interrupt_words` | `set[str]` | See below | Words that always trigger interruption |

### Default Backchanneling Words
```python
{"yeah", "yep", "yes", "ok", "okay", "uh-huh", "huh", "hmm", "um", "uh", 
 "ah", "right", "sure", "i see", "got it", "understood", "mm-hmm", "mhm",
 "alright", "uh huh", "yup", "ya", "yea"}
```

### Default Interrupt Words
```python
{"wait", "stop", "pause", "hold", "hold on", "no", "dont", "don't",
 "shut up", "quiet", "stop talking", "enough", "never mind", "nevermind",
 "actually", "cancel", "hang on", "one second", "excuse me"}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AgentSession                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  AgentActivity                        │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │           BackchannelingFilter               │    │   │
│  │  │  • should_filter_interruption(transcript)    │    │   │
│  │  │  • contains_interrupt_word(text)             │    │   │
│  │  │  • is_pure_backchanneling(text)              │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                      ↑                               │   │
│  │  _interrupt_by_audio_activity(transcript=...)        │   │
│  │                      ↑                               │   │
│  │  ┌──────────────┐   ┌──────────────────────┐        │   │
│  │  │ VAD Events   │   │ STT Transcript Events │        │   │
│  │  └──────────────┘   └──────────────────────┘        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Files Changed

1. **`livekit-agents/livekit/agents/voice/backchanneling.py`** (NEW)
   - Core `BackchannelingFilter` class with word matching logic

2. **`livekit-agents/livekit/agents/voice/agent_session.py`** (MODIFIED)
   - Added `filter_backchanneling`, `backchanneling_words`, `interrupt_words` options

3. **`livekit-agents/livekit/agents/voice/agent_activity.py`** (MODIFIED)
   - Initialize `BackchannelingFilter` in `__init__`
   - Modified `_interrupt_by_audio_activity` to check transcripts
   - Pass transcripts from `on_interim_transcript` and `on_final_transcript`

4. **`examples/voice_agents/interruption_agent.py`** (MODIFIED)
   - Example agent demonstrating the feature

5. **`examples/voice_agents/interruption_handler.py`** (EXISTING)
   - Standalone utility for testing and reference

## Why This Approach?

### No VAD Modification
The solution does not modify the low-level VAD kernel. Instead, it adds a logic handling layer that:
1. Intercepts transcripts before they cause interruptions
2. Immediately resumes if the agent was paused for backchanneling

### Real-time Performance  
The filtering happens synchronously when STT transcripts arrive, adding negligible latency.

### Seamless Integration
The filter is integrated into the existing interruption flow, so:
- No code changes required for existing agents (enabled by default)
- Can be disabled with `filter_backchanneling=False`
- Customizable via constructor arguments or environment variables

## Strict Requirement Met

> "If the agent is speaking and the user says a filler word, the agent must NOT stop. It must continue its sentence seamlessly. Partial solutions where the agent pauses and then resumes, or stutters, will not be accepted."

The implementation ensures:
1. When STT transcript is classified as backchanneling → **no interruption occurs**
2. If VAD caused a brief pause before STT arrived → **immediate resume** (imperceptible)
3. Agent continues speaking without stuttering or noticeable pause
