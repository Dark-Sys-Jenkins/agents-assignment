
# LiveKit Context-Aware Interruption Handling

This repository contains my implementation for the **LiveKit Intelligent Interruption Handling Assignment**.

The work is built on top of the official assignment template provided here:  
https://github.com/Dark-Sys-Jenkins/agents-assignment

The primary goal of this project is to improve the natural flow of voice conversations by ensuring the agent can correctly differentiate between:

- simple listener acknowledgements, and  
- genuine interruption commands.

---

## Problem Description

In the default LiveKit voice-agent pipeline, the interruption mechanism is heavily driven by **Voice Activity Detection (VAD)**.

As a result, when the agent is speaking and the user utters short backchannel words such as:

- "okay"
- "yeah"
- "hmm"
- "uh-huh"

the system mistakenly treats them as interruptions and stops the agent mid-response.

This creates an unnatural and fragmented conversational experience.

---

## Project Goal

The objective of this submission is to introduce an intelligent interruption layer such that:

- Passive filler acknowledgements are ignored *while the agent is actively speaking*
- Explicit interruption commands instantly stop the agent
- The same filler words are still accepted normally when the agent is silent
- All improvements remain in the application logic layer (no changes to the VAD kernel)

---

## Expected Agent Behavior

| User Utterance | Agent Status | Outcome |
|--------------|-------------|--------|
| "yeah", "ok", "hmm" | Agent speaking | Ignored, agent continues speaking |
| "stop", "wait", "cancel" | Agent speaking | Agent is interrupted immediately |
| "yeah", "ok" | Agent silent | Treated as a valid user response |
| "yeah wait a second" | Agent speaking | Interruption triggered due to intent word |
| "hello", "start" | Agent silent | Standard reply generation |

---

## Approach Summary

The key issue comes from a timing mismatch:

- VAD reacts instantly when the user produces sound  
- STT transcription arrives slightly later

Because of this, interruptions may occur before the system understands whether the user intended to stop the agent or was simply acknowledging.

To address this, my solution introduces a **state-aware interruption filter** that:

1. Tracks whether the agent is currently speaking  
2. Captures the STT transcript content  
3. Filters interruptions based on semantic intent  

---

## Design Principles

- **No modification to VAD internals**  
  VAD is treated only as a signal, not the final decision-maker.

- **Transcript-confirmed interruption**  
  Speech is interrupted only when the transcript indicates true intent.

- **Backchannel suppression only during speech**  
  Passive acknowledgements are ignored only if the agent is already talking.

---

## Setup Instructions

### Requirements

- Python 3.9+
- `uv` package manager
- LiveKit Cloud credentials (URL + API Keys)

---

### Installation

Clone the repository:

```bash
git clone <your-repo-url>
cd agents-assignment
````

Install dependencies:

```bash
uv sync --all-extras --dev
```

---

### Environment Setup

Create a `.env` file using `.env.example` and fill in your LiveKit credentials:

```env
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

---

## Running the Agent

To test the interruption logic in terminal mode:

```bash
uv run examples/voice_agents/basic_agent.py console
```

* Press `Space` to simulate voice input
* Enter text manually to simulate STT transcripts

---

## Configuration

The word categories for interruption handling are defined inside:

`livekit/agents/voice/agent_activity.py`

```python
# Hard interruption commands (always stop the agent)
INTERRUPT_KEYWORDS = "stop,wait,pause,hold,cancel,halt,abort,no"

# Passive acknowledgement fillers (ignored only during speech)
PASSIVE_FILLER_WORDS = "okay,ok,yeah,yes,yep,uh,um,hmm,hm,right,sure,gotcha"
```

To customize behavior:

* Add acknowledgement words to `PASSIVE_FILLER_WORDS`
* Add command words to `INTERRUPT_KEYWORDS`

---

## Implementation Highlight

A dedicated ignore list is used for conversational backchannels:

```python
IGNORE_WORDS = [
    "yeah",
    "ok",
    "okay",
    "hmm",
    "uh-huh",
    "right"
]
```

These are filtered only when the agent is already speaking.

---

## Demonstration Video

A working demo of all required scenarios is provided here:

[https://drive.google.com/file/d/1PrefOubQecFKNXs6Qi45-oJTlHnhPsAI/view?usp=sharing](https://drive.google.com/file/d/1PrefOubQecFKNXs6Qi45-oJTlHnhPsAI/view?usp=sharing)

---

## Summary

This project improves LiveKit interruption handling by preventing false cutoffs on passive listener cues while maintaining immediate responsiveness to genuine stop commands. The solution operates purely at the logic layer and meets the assignment constraints for real-time conversational robustness.


