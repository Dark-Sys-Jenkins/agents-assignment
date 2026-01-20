# LiveKit Intelligent Interruption Handling

## Overview

This project implements a **context-aware interruption handling layer** for a LiveKit voice agent.

By default, LiveKit’s Voice Activity Detection (VAD) is very sensitive and treats any user speech
(e.g. “yeah”, “ok”, “uh-huh”) as an interruption. This causes the agent to stop speaking even when
the user is only providing passive acknowledgement.

The goal of this assignment is to **distinguish passive acknowledgements from real interruptions**
without modifying the low-level VAD kernel and while keeping the system fully real-time.

---

## Problem Statement

When the agent is speaking:

- Passive acknowledgements such as **“yeah”, “ok”, “hmm”, “uh-huh”** must be ignored.
- Explicit commands such as **“stop”, “wait”, “no”** must interrupt immediately.
- Mixed input such as **“yeah okay but wait”** must interrupt.

When the agent is silent:

- Short replies like **“yeah”** should be treated as valid user input.

A major challenge is handling **false-start interruptions**, where VAD triggers before STT has
determined whether the user input is meaningful.

---

## Solution Approach

The solution adds a **semantic validation layer** inside the existing LiveKit agent interruption
flow.

Instead of interrupting immediately when VAD fires, the system:

1. Uses the **streaming STT transcript**
2. Checks whether the agent is currently speaking
3. Validates user intent before calling `interrupt()`

No changes are made to:
- The VAD kernel
- The audio pipeline
- The LiveKit runtime internals

---

## Handling False-Start Interruptions

VAD is faster than STT and may fire on noise or short acknowledgements.

To prevent false interruptions:

- Interruption requests are treated as **tentative**
- The agent waits for a **partial STT transcript**
- If the transcript is empty or contains only acknowledgement words, the interruption is ignored
- If a semantic interrupt keyword appears, interruption occurs immediately

This ensures:
- No stuttering
- No pause-resume glitches
- Imperceptible latency

---

## Core Interruption Logic (Conceptual)

While the agent is speaking:

- **Empty transcript** → Ignore (noise / breathing)
- **Only acknowledgement words** → Ignore
- **Contains interrupt keyword** → Interrupt immediately

While the agent is silent:

- Any input is treated as valid user activity

---

## Assignment Scenarios Covered

The following scenarios from the assignment are explicitly tested:

### Scenario 1: Long Explanation
- Agent is speaking
- User says: “Okay… yeah… uh-huh”
- Result: Agent continues speaking

### Scenario 2: Passive Affirmation
- Agent is silent
- User says: “Yeah”
- Result: Agent responds and proceeds

### Scenario 3: Correction
- Agent is speaking
- User says: “No stop”
- Result: Agent stops immediately

### Scenario 4: Mixed Input
- Agent is speaking
- User says: “Yeah okay but wait”
- Result: Agent stops

---

## Testing Strategy

The assignment focuses on **semantic interruption logic**, not speech recognition accuracy.
Therefore, testing is done using **deterministic log-based tests** that simulate:

- Streaming STT output
- Agent speaking vs silent state
- Interruption decisions


### Run Tests

```bash
python run_tests.py

