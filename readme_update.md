# Context-Aware Interruption Handling (Assignment Update)

## Background

In the existing LiveKit Agents SDK, **Voice Activity Detection (VAD)** triggers an interruption whenever user speech is detected.  
While correct for explicit commands, this behavior incorrectly interrupts the agent when users make **passive acknowledgements** (e.g. “yeah”, “ok”, “uh-huh”) while the agent is speaking.

This update introduces a **semantic interruption resolution layer** to prevent unnecessary interruptions without affecting real interruption latency.

---

## What Was Changed

A lightweight interruption decision component was added to defer and resolve interruptions using Speech-to-Text (STT):

- Deferred VAD-triggered interruptions when the agent is speaking
- Introduced a shared `InterruptLogic` state:
  - Tracks whether the agent is currently speaking
  - Stores pending VAD-triggered interruption intent
- Interruption decisions are resolved only after final STT transcript availability
- Passive acknowledgements are ignored
- Explicit commands still interrupt immediately
- Mixed utterances (e.g. “yeah wait”) correctly prioritize command intent

No changes were made to:
- VAD models
- STT models
- Audio streaming or buffering logic
- Agent response timing or pacing

---

## Design Rationale

This approach was chosen to:

- Avoid timing-based heuristics (e.g. debounce, sleep)
- Preserve real-time responsiveness
- Maintain existing behavior when the agent is not speaking
- Ensure deterministic, testable decision-making

The solution operates purely at the **decision layer**, making it safe and production-compatible.

---

## Validation

Validation was performed using a standalone logic replay test that exercises the interruption decision logic directly.

This method was chosen to:
- Isolate semantic decision correctness
- Avoid SDK dependency constraints
- Provide deterministic, reviewable evidence

### Tested Scenarios

| Agent Speaking | User Utterance | Result |
|---------------|---------------|--------|
| Yes | “yeah” | Ignored |
| Yes | “ok hmm” | Ignored |
| Yes | “stop” | Interrupted |
| Yes | “yeah wait” | Interrupted |
| No | “yeah” | Normal processing |

### Validation Logs

