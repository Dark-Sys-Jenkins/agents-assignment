# Interruption Handler — Simple Agent Architecture

## Overview

This document describes the basic voice agent implementation in `basic_agent.py`. The agent provides core voice interaction capabilities with agent speech state tracking.

**Key Philosophy:** Enable natural conversational interactions with minimal processing overhead.

---

## Logic Matrix: Agent Session Flow

| **Agent State** | **Transcript Type** | **Action** | **Log Level** |
|---|---|---|---|
| Not speaking | Final | Process normally | INFO |
| Not speaking | Partial | Process | DEBUG |
| Speaking | Any | Allow natural interruption | (handled by session) |
| Any | Empty/whitespace | Skip | (skipped) |

---

## Key Features

### 1. **State Tracking**
- `agent.is_speaking` boolean flag (optional for logging purposes only)
- Updated via `agent_speech_started` and `agent_speech_ended` event handlers

### 2. **Built-in Session Parameters**
- `min_interruption_duration=0.6` — Ignore speech shorter than 600ms (noise)
- `min_interruption_words=2` — Ignore utterances with fewer than 2 words (fragments)
- `allow_interruptions=True` — Enable natural interruptions
- `preemptive_generation=False` — Wait for full turn end before generating response
- `resume_false_interruption=True` — Auto-resume after false positives
- `false_interruption_timeout=1.0` — Timeout window (1 second)

---

## Setup & Run

### 1. Install Dependencies
Ensure the base `agents-assignment` environment has all required packages:
```bash
pip install -e .
pip install python-dotenv livekit-agents livekit-plugins-deepgram livekit-plugins-openai livekit-plugins-cartesia
```

### 2. Configure `.env`
Place a `.env` file in `agents-assignment/` root with your credentials and optional filter customization:

```env
# Required credentials
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
CARTESIA_API_KEY=your_cartesia_key_here
LIVEKIT_URL=your_livekit_url_here
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here

# Optional: customize ignore/force interrupt words (comma-separated, case-insensitive)
# IGNORE_WORDS=um,uh,hmm,yeah,yep,okay,ok,sure,right,like
# FORCE_INTERRUPT_WORDS=stop,wait,hold on,interrupt,interrupt please
```

### 3. Run the Agent in Console Mode
```bash
cd agents-assignment
python examples/voice_agents/basic_agent.py console
```

You will see:
- `[ENV OK]` messages for all required credentials (or `[ENV MISSING]` errors)
- Agent speech state changes at DEBUG level

### 4. Customization
Session parameters can be adjusted in `basic_agent.py` as needed for your use case.

---

## `.env` Configuration Example

```env
# LiveKit credentials
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_123
LIVEKIT_API_SECRET=your_api_secret_xyz

# AI provider keys
DEEPGRAM_API_KEY=d9a8f7e6c5b4a3f2e1d0c9b8a7f6e5d4
OPENAI_API_KEY=sk-proj-abc123xyz789...
CARTESIA_API_KEY=cart_9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d
```

---

## Test Scenarios & Expected Behavior

The agent handles natural conversational interruptions based on built-in session parameters. Users can interrupt at any time, and the agent will pause and handle the interruption accordingly.

---

## Implementation Details

### Files in Use

- **[basic_agent.py](examples/voice_agents/basic_agent.py):**
  - `agent.is_speaking` state tracking (optional)
  - Event handlers: `agent_speech_started`, `agent_speech_ended`
  - Session parameters: `preemptive_generation=False`, `min_interruption_duration`, `min_interruption_words`, `resume_false_interruption`, `false_interruption_timeout`, `allow_interruptions=True`

### Session Flow

```
User Speech (STT)
    ↓
[Min Duration Check] (0.6s)
    ↓
[Min Words Check] (2 words)
    ↓
Interrupt Handler (handled by session)
```

---

## Troubleshooting

| **Issue** | **Cause** | **Solution** |
|---|---|---|
| `[ENV MISSING]` warnings | Missing credentials in `.env` | Copy `.env` to `agents-assignment/` root with all required keys |
| 401 authorization errors | Invalid LiveKit/provider keys | Verify LiveKit project credentials and API keys are correct |

---

## Summary

The agent provides a clean voice interaction implementation with natural interruption handling via built-in session parameters. It respects conversation patterns while preventing noise and false positives from disrupting agent responses.

**Status:** ✅ Fully implemented and ready to use.
