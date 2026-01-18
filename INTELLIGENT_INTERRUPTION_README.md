# Intelligent Interruption Handling for LiveKit Voice Agents

## Problem Statement

LiveKit's default VAD treats all user speech as interruptions. When users say "yeah" or "ok" to show they're listening (backchanneling), the agent stops speaking unnecessarily.

**The Challenge**: VAD fires ~50ms after sound, but STT takes ~300ms to provide text. By the time we know the user said "yeah", the agent has already stopped.

## Solution Architecture

### The Timing Problem (Why This Is Hard)

```
User says "yeah"
      |
      v
[t=0ms]   VAD detects speech → Default: STOP AGENT (too early!)
      |
      v
[t=300ms] STT returns "yeah" → Now we know it was just a backchannel
      |
      v
Too late - agent already stopped, audio glitched
```

### My Solution: Deferred Decision Making

```
User says "yeah"
      |
      v
[t=0ms]   VAD detects speech → Set pending_interruption flag (DON'T stop yet)
      |                        Agent keeps speaking smoothly
      v
[t=300ms] STT returns "yeah" → Classify transcript
      |                        Decision: IGNORE (backchannel)
      v                        Clear pending flag, continue speaking
Agent never stopped - zero glitch!
```

### Key Innovation

Instead of interrupting on VAD and trying to resume (which causes stuttering), I **defer the interruption decision** until STT provides the transcript. The agent audio continues uninterrupted while we wait for text.

## Decision Matrix

| User Says | Agent State | Action |
|-----------|-------------|--------|
| "yeah/ok/hmm" | Speaking | **IGNORE** - continue seamlessly |
| "stop/wait/no" | Speaking | **INTERRUPT** - stop immediately |
| "yeah/ok/hmm" | Silent | **RESPOND** - process as input |
| "yeah but wait" | Speaking | **INTERRUPT** - contains command |

## Implementation Details

### Files Modified

1. **`livekit-agents/livekit/agents/voice/interruption_classifier.py`** (NEW)
   - `InterruptionConfig` - configurable word lists
   - `InterruptionClassifier` - classification logic
   - `InterruptionDecision` - IGNORE/INTERRUPT/RESPOND enum

2. **`livekit-agents/livekit/agents/voice/agent_activity.py`** (MODIFIED)
   - Added `_pending_vad_interruption` flag
   - Modified `on_vad_inference_done()` - defer when agent speaking
   - Modified `on_interim_transcript()` - classify and decide
   - Modified `on_final_transcript()` - final classification
   - Modified `on_end_of_speech()` - clear pending flag

3. **`livekit-agents/livekit/agents/voice/__init__.py`** (MODIFIED)
   - Exported classifier classes

### Flow Diagram

```
                    ┌──────────────────┐
                    │   User Speaks    │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              v                             v
    ┌─────────────────┐           ┌─────────────────┐
    │  VAD Fires      │           │  STT Processes  │
    │  (fast ~50ms)   │           │  (slow ~300ms)  │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             v                             │
    ┌─────────────────┐                    │
    │ Agent Speaking? │                    │
    └────────┬────────┘                    │
             │                             │
      ┌──────┴──────┐                      │
      │ YES         │ NO                   │
      v             v                      │
┌───────────┐  ┌──────────┐               │
│ Set       │  │ Normal   │               │
│ Pending   │  │ Interrupt│               │
│ Flag      │  └──────────┘               │
└─────┬─────┘                             │
      │                                   │
      │◄──────────────────────────────────┘
      │         (wait for transcript)
      v
┌─────────────────────────────────────────┐
│         CLASSIFY TRANSCRIPT             │
│  ┌─────────────────────────────────┐   │
│  │ Has hard word? → INTERRUPT      │   │
│  │ Only soft words? → IGNORE       │   │
│  │ Agent silent? → RESPOND         │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Custom soft words (comma-separated)
export SOFT_WORDS="yeah,ok,hmm,uh-huh,right,sure"

# Custom interrupt commands (comma-separated)
export HARD_INTERRUPT_WORDS="stop,wait,no,pause,hold on"

# Enable debug logging
export LIVEKIT_LOG_LEVEL=DEBUG
```

### Programmatic Configuration

```python
from livekit.agents.voice import (
    InterruptionConfig,
    InterruptionClassifier,
    set_default_classifier,
)

config = InterruptionConfig()
config.add_soft_word("absolutely")
config.add_hard_interrupt_word("skip")
set_default_classifier(InterruptionClassifier(config))
```

## Running the Demo

1. Set up environment:
```bash
cd agents-assignment
python3 -m venv venv
source venv/bin/activate
pip install -e ./livekit-agents
pip install python-dotenv
```

2. Configure API keys in `examples/.env`:
```
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
```

3. Run the agent:
```bash
cd examples/voice_agents
python intelligent_interruption_agent.py dev
```

4. Test scenarios:
   - Ask for a story, say "yeah/ok/hmm" while speaking → Agent continues
   - Say "stop" or "wait" → Agent stops immediately
   - When agent is silent, say "yeah" → Agent responds

## Logs for Proof

With `LIVEKIT_LOG_LEVEL=DEBUG`, you'll see:

```
[IGNORE] Backchannel while speaking: 'yeah'
[IGNORE] Backchannel while speaking: 'okay'
[INTERRUPT] Hard command while speaking: 'stop'
[RESPOND] Agent silent, processing: 'yeah'
```

## Tests

```bash
python tests/test_interruption_classifier_standalone.py
```

## Why This Approach Stands Out

1. **Zero Audio Glitch**: Agent never pauses on backchannels - decision is deferred, not reversed
2. **Proper Timing**: Waits for STT before deciding, unlike naive approaches that pause then resume
3. **Configurable**: Easy to customize word lists via env vars or code
4. **Semantic Parsing**: "yeah but wait" correctly triggers interrupt (contains command word)
5. **Clean Integration**: Minimal changes to existing LiveKit code, follows existing patterns
6. **Proper Logging**: Clear decision trail for debugging and demo proof

## Default Word Lists

**Soft Words** (backchannels - ignored while speaking):
- Affirmatives: yeah, yea, yep, yup, yes
- Acknowledgements: ok, okay, k
- Fillers: hmm, hm, mm, mhm, uh-huh, aha
- Agreement: right, sure, alright, got it, cool, nice, great

**Hard Interrupt Words** (always stop agent):
- Commands: stop, wait, no, pause, hold, hold on
- Redirects: actually, but, however, cancel, quit
