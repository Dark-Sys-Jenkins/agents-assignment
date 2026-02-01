# Intelligent Interruption Handling for LiveKit Agents

## Overview
This feature implements intelligent interruption logic for the LiveKit Voice Agent. It distinguishes between passive acknowledgements (backchanneling) and active interruptions.

**Goal:** The agent should **continue speaking** when the user says "yeah", "ok", or "hmm", but **stop immediately** for "wait", "stop", or other substantive input.

## Features
- **Backchanneling Filtering**: Ignores configurable words/phrases like "yeah", "uh-huh" while the agent is speaking.
- **State Awareness**: Responds to those same words if the agent is silent (e.g., answering "Yeah" to a question).
- **Interrupt Keywords**: always interrupts for words like "stop", "wait", "no".
- **Mixed Input Handling**: Interrupts if the user says a mix of backchanneling and real words (e.g., "Yeah but wait").

## Configuration

The logic is configurable via `AgentSession` options:

```python
session = AgentSession(
    # ...
    intelligent_interruption_enabled=True,
    backchanneling_words=["yeah", "ok", "cool"],
    interrupt_keywords=["stop", "wait"],
    max_backchanneling_words=3,
)
```

## How it Works

1. **VAD Deferral**: When the agent is speaking, Voice Activity Detection (VAD) interruptions are deferred.
2. **Transcript Analysis**: The Speech-to-Text (STT) transcript is analyzed by `InterruptionFilter`.
3. **Decision Logic**:
   - IF (Agent Speaking) AND (Input in Backchannel List) -> **IGNORE**
   - IF (Agent Speaking) AND (Input has Interrupt Keyword) -> **INTERRUPT**
   - IF (Agent Speaking) AND (Input > Max Words) -> **INTERRUPT**
   - IF (Agent Silent) -> **RESPOND**

## Testing

Run the provided unit tests to verify the logic:

```bash
python -m unittest tests/test_interruption_logic.py
```
*(Ensure `livekit-agents` is in your PYTHONPATH)*
