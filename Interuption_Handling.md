# Context-Aware Interruption Handling for LiveKit Agent

## Summary
This document introduces a **state-aware interruption handling layer** that enables the LiveKit agent to intelligently distinguish between **passive acknowledgements** (backchanneling) and **active interruptions**. The update prevents unintended speech cutoffs during agent explanations while preserving immediate responsiveness to explicit user commands.

This implementation strictly complies with the challenge constraints and does **not modify LiveKit’s low-level VAD**.

---

## Problem Statement
LiveKit’s default VAD is overly sensitive to short user utterances such as:
- “yeah”
- “ok”
- “hmm”

During agent speech, these are incorrectly treated as interruptions, causing the agent to abruptly stop mid-sentence and degrade conversational quality.

---

## Solution Overview
A lightweight **logic-handling layer** has been added within the agent’s event loop that operates on **STT output** and **agent speaking state**.

The system now:
- Ignores passive acknowledgements while the agent is speaking
- Immediately interrupts on explicit commands
- Treats the same acknowledgement words as valid input when the agent is silent
- Handles mixed semantic inputs correctly (e.g., “yeah wait”)

All decisions are made in real time with no perceptible latency.

---

## Key Features
- **Configurable Ignore List** for soft inputs (e.g., `yeah`, `ok`, `hmm`)
- **State-Based Filtering** (Speaking vs Silent)
- **Semantic Interruption Detection** for mixed inputs
- **No VAD Kernel Modification**
- **No Audio Pauses, Stutters, or Resume Artifacts**
- **Modular and Easily Extendable Design**

---

## Behavior Matrix

| User Input            | Agent State | Expected Behavior |
|-----------------------|-------------|-------------------|
| "yeah / ok / hmm"     | Speaking    | Ignore completely |
| "stop / wait / no"    | Speaking    | Interrupt immediately |
| "yeah / ok"           | Silent      | Treat as valid input |
| "yeah but wait"       | Speaking    | Interrupt |

---

## Validation
The implementation has been tested against all required scenarios:
- Long agent explanations remain uninterrupted during backchanneling
- Short affirmations are processed correctly when the agent is silent
- Explicit stop commands immediately halt agent speech
- Mixed inputs trigger correct interruption behavior

Supporting logs / recordings are included as required.

---

## Risk Assessment
- No breaking changes
- No performance degradation
- Fully backward compatible
- Scoped only to agent logic layer

---

## Checklist
- [x] Strict functionality compliance
- [x] State-aware interruption logic
- [x] Configurable ignore list
- [x] Modular and clean code
- [x] Documentation updated

---

# Documentation: Context-Aware Interruption Handling

## Purpose
This change improves conversational robustness by preventing unintended agent speech interruptions caused by passive user acknowledgements, while preserving natural conversational flow.

---

## Core Concepts

### 1. Agent State Awareness
The agent explicitly tracks whether it is:
- **Speaking**: Actively generating or playing audio
- **Silent**: Idle and waiting for user input

---

### 2. Input Classification
User speech (via STT) is classified into:
- **Soft Inputs**: Passive acknowledgements  
  Examples: `yeah`, `ok`, `hmm`, `uh-huh`
- **Hard Commands**: Explicit interruption intent  
  Examples: `stop`, `wait`, `no`
- **Mixed Inputs**: Soft + command tokens  

---

### 3. Configurable Ignore List
Passive acknowledgements are defined centrally:

```python
IGNORE_WORDS = ["yeah", "ok", "okay", "hmm", "uh-huh", "right"]

User Speech → STT → Token Normalization
               ↓
        Agent State Check
               ↓
 ┌───────────────────────────────┐
 │ Is the Agent Speaking?        │
 └───────────────┬───────────────┘
                 │
       YES ──────┴────── NO
        │                │
Soft Input?         Process Normally
        │
YES → Ignore Completely
NO  → Interrupt Immediately
