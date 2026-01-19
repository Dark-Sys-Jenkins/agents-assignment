# Intelligent Interruption Handling for LiveKit Agents

## Overview

This document describes the implementation of **intelligent interruption handling** in the LiveKit Agents framework. The feature distinguishes between **backchannel utterances** (e.g., "yeah", "ok", "hmm") and **real interruption commands** (e.g., "stop", "wait", "no"), allowing the agent to continue speaking seamlessly when users provide encouraging feedback while still responding immediately to genuine interruption requests.

### Example of the Problem

```
Agent: "Once upon a time, there was a brave knight who—"
User: "Yeah"  (just showing engagement)
Agent: [PAUSES] "I see you said something. How can I help?"  ❌ Bad UX
```

### Desired Behavior

```
Agent: "Once upon a time, there was a brave knight who—"
User: "Yeah"  (just showing engagement)
Agent: "—lived in a magnificent castle..."  ✅ Continues seamlessly

Agent: "The knight decided to embark on a quest to—"
User: "Wait!"  (real interruption)
Agent: [STOPS] "Yes? What would you like to know?"  ✅ Responds to command
```
---

## Solution: Two-Phase Interruption Handling

The implementation uses a **two-phase approach** that separates VAD from the actual interruption decision:

### Phase 1: VAD Detection (Soft Gate)
When VAD detects user speech while the agent is speaking:
- **Don't pause audio immediately**
- Set a "pending interruption" flag
- Wait for STT (Speech-to-Text) to provide transcript

### Phase 2: Semantic Classification (Commit/Cancel)
When STT provides the transcript:
- **Classify the utterance** as backchannel, interrupt command, or normal speech
- **Backchannel** → Cancel pending interruption, agent continues seamlessly
- **Interrupt command** → Commit interruption, stop agent immediately
- **Normal speech** → Commit interruption, process as user turn

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Speech Input                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VAD (Voice Activity Detection)               │
│                                                                 │
│  • Detects speech/silence boundaries                            │
│  • If agent speaking → Set pending_interruption = True          │
│  • Does NOT pause audio immediately                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STT (Speech-to-Text)                         │
│                                                                 │
│  • Converts audio to text (interim + final transcripts)         │
│  • Passes transcript to classification logic                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Utterance Classification                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ BACKCHANNEL │  │  INTERRUPT  │  │   NORMAL    │             │
│  │             │  │             │  │             │             │
│  │ "yeah"      │  │ "stop"      │  │ "tell me    │             │
│  │ "ok"        │  │ "wait"      │  │  about..."  │             │
│  │ "uh-huh"    │  │ "hold on"   │  │             │             │
│  │ "right"     │  │ "no"        │  │             │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│    Cancel Pending   Commit Interrupt  Commit Interrupt          │
│    (Continue)       (Stop Agent)      (Process Turn)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Key Components

#### 1. Default Word Lists

```python
DEFAULT_BACKCHANNEL_WORDS = [
    "yeah", "yep", "yup", "yes",
    "ok", "okay", "k",
    "hmm", "hm", "mm", "mhm", "uh-huh", "uh huh",
    "right", "sure", "got it",
    "i see", "ah", "oh",
]

DEFAULT_INTERRUPT_WORDS = [
    "stop", "wait", "hold on", "hold", "pause",
    "no", "actually", "but", "however",
    "excuse me", "sorry", "hang on",
    "one moment", "one second", "just a moment",
]
```

#### 2. Utterance Classification (`_classify_utterance`)

The classification logic first checks if the text contains any interrupt words for semantic awareness - "Yeah, but wait" interrupts because of "wait". Then it checks if all words in the utterance are backchannels ("yeah ok" is backchannel, but "yeah tell me more" is normal). Everything else is classified as normal speech that should trigger an interruption.

#### 3. Pending Interruption State

I use simple boolean flags (_pending_interruption and _pending_interruption_time) to track when an interruption is "pending" - detected by VAD but not yet committed. The system can either commit the interruption (actually pause/stop the agent via _commit_pending_interruption()) or cancel it (agent continues seamlessly via _cancel_pending_interruption()). A helper method _is_agent_speaking() checks if there's an active, interruptible speech handle.

#### 4. VAD Hook (`on_vad_inference_done`)

When VAD detects speech and the agent is currently speaking, I set the pending interruption flag instead of interrupting immediately. If the agent isn't speaking, the system follows normal interruption flow with _interrupt_by_audio_activity(). This is the critical branching point for the two-phase approach that prevents immediate audio pauses.

#### 5. Transcript Hooks (`on_interim_transcript`, `on_final_transcript`)

When STT provides interim or final transcripts, I classify the utterance type using _classify_utterance(). For backchannels, I cancel the pending interruption so the agent continues seamlessly without any pause. For interrupt commands or normal speech, I commit the interruption to stop the agent immediately.

#### 6. Turn Skipping (`on_end_of_turn`)

Even if the turn detector fires on a backchannel, I perform a final classification check in the on_end_of_turn callback. If it's a pure backchannel during agent speaking, I return False to skip the entire turn. This prevents the backchannel from being added to chat history and avoids unnecessary LLM API calls, saving costs.

#### 7. Interim Transcript Heuristics

STT sends partial results like "ye" before "yeah", which could cause false decisions. I added _should_defer_interim_interruption() to defer classification on very short tokens (< 3 chars) or tokens that are prefixes of known backchannel words. However, _is_interim_interrupt_prefix() provides a fast-path: if an interim looks like an interrupt command prefix ("sto" → "stop"), I commit immediately for faster response.

---

## Configuration

### AgentSession Options

```python
from livekit.agents import AgentSession
from livekit.agents.voice import DEFAULT_BACKCHANNEL_WORDS, DEFAULT_INTERRUPT_WORDS

session = AgentSession(
    vad=silero.VAD.load(),
    stt=openai.STT(),
    llm=openai.LLM(),
    tts=openai.TTS(),
    
    # Customize word lists (optional - defaults are provided)
    backchannel_words=["yeah", "ok", "uh-huh", "right", "sure"],
    interrupt_words=["stop", "wait", "hold on", "pause", "no"],
)
```

### Default Behavior

- **Intelligent interruption is enabled by default** with sensible word lists
- No configuration required for standard use cases
- Word lists can be customized per session for different languages or use cases

---

## Behavior Matrix

| Scenario | User Says | Agent Action |
|----------|-----------|--------------|
| Agent speaking | "yeah" | ✅ Continues seamlessly (no pause, no LLM call) |
| Agent speaking | "ok, ok" | ✅ Continues seamlessly |
| Agent speaking | "Yeah, but wait" | ⏹️ Stops immediately (contains "wait") |
| Agent speaking | "stop" | ⏹️ Stops immediately |
| Agent speaking | "tell me more" | ⏹️ Stops, processes as new turn |
| Agent silent | "yeah" | 💬 Responds normally |
| Agent silent | "tell me a story" | 💬 Responds normally |

---

## Demo Script

A demo script is provided at `examples/voice_agents/intelligent_interrupt_demo.py`:

```bash
# Run in dev mode
python examples/voice_agents/intelligent_interrupt_demo.py dev

# Required environment variables
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
```

### Testing the Feature

1. **Test backchannel ignoring**: While the agent is speaking, say "yeah", "ok", or "uh-huh". The agent should continue without any pause.

2. **Test interrupt commands**: While the agent is speaking, say "stop" or "wait". The agent should stop immediately and acknowledge.

3. **Test semantic awareness**: Say "Yeah, but wait" - should interrupt because it contains "wait".

---

## Logging

Enable DEBUG logging to see interruption decisions:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Example log output:
```
DEBUG - VAD detected speech while agent speaking - pending interruption set
DEBUG - Final transcript backchannel: 'Yeah, yeah.' - ignoring
DEBUG - Skipping user turn - pure backchannel during agent speaking
```
---

## Technical Notes

### Why Two Phases?

1. **VAD alone can't distinguish speech content** - it only detects audio energy
2. **STT provides semantic content** - needed to classify utterance type
3. **Immediate VAD interruption causes "hiccups"** - pausing on every sound feels jarring
4. **Waiting for full STT is too slow** for real interrupts - interim transcripts provide faster response

### Some Edge Cases Which I Observed

- **Partial transcripts**: "ye" → "yea" → "yeah" - defers until stable
- **Mixed content**: "Yeah but wait" - interrupts due to "wait"
- **Multi-word backchannels**: "uh huh", "got it" - recognized as single units
- **No transcript (noise)**: Speech ends with no STT result - cancels pending

## Summary

The intelligent interruption handling feature provides a significantly improved user experience by:

- ✅ **Eliminating unwanted pauses** when users say "yeah/ok/hmm"
- ✅ **Maintaining responsiveness** to real interruption commands
- ✅ **Providing semantic awareness** ("Yeah, but wait" still interrupts)
- ✅ **Being configurable** with custom word lists
- ✅ **Working out of the box** with sensible defaults

This creates more natural, human-like conversations where users can provide feedback without disrupting the agent's flow.
