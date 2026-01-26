# LiveKit Intelligent Interruption Handling

This repository contains a refined conversational logic layer for a real-time AI agent. It implements a context-aware interruption handler that distinguishes between passive "backchanneling" (listener feedback) and active user interruptions, as required by the LiveKit Intelligent Interruption Handling Challenge.

### Submitted By
**Name:** Hari Kishoare
**GitHub Username:** atomiclifestyle
**Branch:** feature/interrupt-handler-hariKishore
**College:** International Institute of Information Technology(IIIT), Bhubaneswar
**ID:** B423024
**Date of Submission:** 26th January 2026

## Overview

The default Voice Activity Detection (VAD) in real-time agents can be overly sensitive, cutting off the agent when the user says simple filler words like "yeah" or "uh-huh".

This solution implements a logic filtering layer that adheres to the following behavioral matrix:

| User Input | Agent State | Behavior | Outcome |
|:-----------|:------------|:---------|:--------|
| "Yeah" / "Ok" / "Hmm" | Speaking | IGNORE | Agent continues speaking seamlessly. |
| "Stop" / "Wait" | Speaking | INTERRUPT | Agent stops immediately. |
| "Yeah" / "Ok" | Silent | RESPOND | Agent treats this as a conversational turn. |
| "Yeah but wait" | Speaking | INTERRUPT | Mixed input triggers a stop. |

## Features

* **Context Awareness:** Dynamically checks if the agent is "speaking" or "listening" before deciding to interrupt.
* **Configurable Ignore List:** The list of "soft" interruption words is customizable via environment variables.
* **Greedy Matching Strategy:** Accurately detects phrases (e.g., "make sense") and handles complex sentences to prevent false positives.
* **Latency Optimized:** Logic is injected directly into the audio activity loop to ensure real-time performance.

## Installation & Setup

### 1. Prerequisites
* Python 3.8+
* LiveKit API Credentials

### 2. Setup
Clone the repository and install dependencies:
```bash
# Install dependencies
pip install -r examples/voice_agents/requirements.txt

# Install the local package in editable mode (Critical for local dev)
pip install -e livekit-agents
```

### 3. Configuration
Create a `.env` file in the root directory. You must configure the standard LiveKit keys, and you can optionally override the ignore list.
```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=Secret...
OPENAI_API_KEY=sk-...

# Custom Ignore List (Optional)
INTERRUPT_IGNORE_WORDS=yes,yeah,yep,yup,sure,ok,okay
```

If `INTERRUPT_IGNORE_WORDS` is not set, the agent defaults to a standard list of backchannel phrases.
**Default Ignore List:**
```python
DEFAULT_IGNORE_LIST: list[str] = [
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "alright", "all right", "right", "fine", "cool",
    "i see", "got it", "understood", "makes sense",
    "uh-huh", "mhmm", "hmm", "aha", "mm-hmm", "mhm",
    "go on", "keep going", "continue",
    "oh", "ohh", "ah", "wow", "k",
]
```
## Programmatic Configuration
You can also configure the ignore list directly while creating a agent using livekit by passing it to the session options. This takes precedence over default settings and allows for per-session customization.

```python
from livekit.agents import (AgentSession)

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # ... other fields ...
    
    session = AgentSession(
        # ... other configs ...
        ignore_list=["yeah", "ok", "absolutely", "continue"]
    )

```

## Logic Implementation

The core logic is implemented in `_interrupt_by_audio_activity`.

1. **State Check:** The handler first verifies if `self._session.agent_state == "speaking"`.
2. **Transcription Analysis:** If speaking, it captures the incoming user transcript.
3. **Filtering:** It runs `can_ignore(transcript, ignore_list)`:
   * It normalizes text (removes punctuation/case).
   * It checks if the entirety of the user's speech consists only of ignored words.
   * If True: The interruption signal is suppressed, and the agent continues.
   * If False (e.g., "Yeah stop"): The standard interruption sequence proceeds.

## Testing

### Automated Tests
Run the included pytest suite to verify the logic matrix:
```bash
pip install pytest pytest-asyncio

pytest -v tests/test_interrupt_handler.py
```

### Manual Verification Scenarios
1. **The Long Explanation:** Have the agent read a long paragraph. Say "Uh-huh" or "Yeah" repeatedly. The agent should NOT stop.
2. **The Correction:** While the agent is speaking, say "No stop". The agent MUST stop immediately.
3. **Passive Affirmation:** When the agent is silent, say "Yeah". The agent should acknowledge and respond.