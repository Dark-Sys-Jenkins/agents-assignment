# LiveKit Intelligent Interruption Handling
### Context-Aware, Race-Safe Voice Agent Interruption System

This project implements a **real-time, semantic, race-condition-safe interruption handling layer** for LiveKit voice agents.

It solves the core problem:

> LiveKit’s VAD (Voice Activity Detection) fires faster than STT (Speech-to-Text).
> As a result, even harmless backchannel words like *"yeah"*, *"hmm"*, *"ok"* incorrectly interrupt the agent mid-sentence.

The strict requirement was:

- **While the agent is speaking:**
  - "yeah / ok / hmm" → **must NOT stop audio**
  - "stop / wait / no" → **must immediately stop audio**
  - "yeah but wait" → **must stop**
- **When the agent is silent:**
  - "yeah" → **must be processed as a valid response**
- No stutter, no pause, no resume glitch.
- VAD must NOT be modified.
- Must be real-time and race-safe.

This solution achieves that by **buffering VAD interruptions and validating them semantically with STT before cutting audio**.

---

## Architecture Overview

```mermaid
graph TD
    User[User Speech] --> VAD[VAD (Acoustic/Fast)]
    VAD --> Buffer[SmartAgentActivity Buffer]
    Buffer --> STT[STT (Semantic/Slow)]
    STT --> Classifier[InterruptionClassifier]
    Classifier -- Backchannel --> Discard[Discard (TTS Continues)]
    Classifier -- Command --> Execute[Execute Interrupt (Cut Audio)]
```

**Key idea:**
> VAD becomes a *soft, reversible signal* instead of an immediate hard stop.
> Only semantic confirmation from STT is allowed to trigger an actual interruption.

---

## File Structure

```
examples/voice_agents/
│
├── intelligent_interruption_agent.py   # Semantic logic + LiveKit wiring
├── smart_interruption_session.py       # Core race-safe buffering & interception
├── fakes.py                            # Fake VAD/STT/LLM/TTS for deterministic testing
├── simulate_interruption_race.py       # Real-time race simulation & proof logs
└── test_timing_race.py                 # Formal pytest verification of all edge cases
```

Each file has a precise role in the system.

---

## 1. `intelligent_interruption_agent.py`
### Semantic Decision Layer & System Bootstrap

**Purpose:**
Defines what counts as backchannel vs. real interruption, how state (speaking vs silent) affects meaning, and how the custom `SmartInterruptionSession` is wired into LiveKit.

**Core Components:**

1.  **`AgentStateTracker`**
    *   Tracks whether the agent is currently speaking.
    *   Enables distinction between:
        *   "yeah" while speaking → **ignore**
        *   "yeah" while silent → **valid input**

2.  **`InterruptionClassifier`**
    *   Implements the logic matrix:
        | Condition | Decision |
        | :--- | :--- |
        | Agent silent | Always process |
        | Speaking + Keyword | Interrupt |
        | Speaking + Ignore Word | Ignore |
        | Speaking + Mixed | Interrupt |
    *   Supports configurable ignore lists, multi-word phrases ("hold on"), and interim keyword detection.

3.  **`IntelligentInterruptionHandler`**
    *   Combines Agent State, Classifier, and Session Control (interrupt/commit/discard). This is the policy layer.

4.  **`SmartInterruptionSession` Injection**
    *   Instead of using LiveKit’s default `AgentSession`, we create:
        ```python
        session = SmartInterruptionSession(...)
        ```
    *   This replaces LiveKit’s internal activity engine with our buffered, semantic-aware one.

---

## 2. `smart_interruption_session.py`
### Core Real-Time Race Condition Fix

This is the heart of the solution.

**Problem Solved:**
*   **Default:** `VAD fires → audio cut immediately → STT arrives later (too late)`
*   **Our Solution:** `VAD fires → buffer → wait for STT → semantic decision → cut or discard`

**Key Mechanisms:**

1.  **`SmartAgentActivity` (Subclass of `AgentActivity`)**
    *   Overrides critical LiveKit hooks:
        *   **`on_vad_inference_done()`**:
            *   If silent: Normal behavior.
            *   If speaking: **Do NOT interrupt**. Buffer the event. Start timeout watchdog.
        *   **`on_interim_transcript()`**: if "stop" detected early, interrupt immediately (low latency).
        *   **`on_final_transcript()`**: Run semantic classification. If Backchannel → discard buffer. If Command → execute interruption.

2.  **Timeout Safety**
    *   If STT never arrives within **400ms**, force interruption to avoid deadlock.

3.  **Audio Cut Execution**
    *   Uses LiveKit’s internal method `await self._interrupt_by_audio_activity()`.
    *   Guarantees: **No resume, No stutter, No audio re-synthesis, True hard stop**.

---

## 3. `fakes.py`
### Deterministic Real-Time Pipeline Simulation

Provides fully compatible fake implementations of `FakeVAD`, `FakeSTT`, `FakeLLM`, and `FakeTTS`.

**Why this matters:**
*   Real timing (async, streaming) without API cost or microphone requirement.
*   Reproducible race conditions.
*   Allows precise VAD → STT ordering simulation.

---

## 4. `simulate_interruption_race.py`
### Deterministic Race Proof Generator

Simulates four canonical scenarios:
1.  "yeah" while speaking
2.  "stop" while speaking
3.  "yeah" while silent
4.  "yeah but wait" while speaking

Artificially enforces `VAD @ t=50ms` and `STT @ t=200ms`.

**Generates timestamped logs proving:**
*   VAD did NOT cut audio.
*   STT semantics decided the outcome.
*   Only real commands executed interruption.
*   Backchannels were fully ignored with **no pause**.

---

## 5. `test_timing_race.py`
### Formal Verification via PyTest

Automated tests validating:
*   Backchannel ignored (No false cut)
*   Hard interrupt works (Commands still stop)
*   Timeout fallback (No deadlock)
*   Interim detection (Ultra-low latency stop)
*   Silent state logic (State-aware behavior)
*   Mixed input (Semantic dominance)

**Key assertion:** `assert not activity._interrupt_by_audio_activity.called` directly proves audio was never cut on "yeah".

---

## 6. How to Run Verification

You can verify the solution using the provided simulation and test scripts.

### 1. Run the Race Condition Simulation
This script simulates the VAD/STT timing delays and outputs a proof log.

```bash
python examples/voice_agents/simulate_interruption_race.py
```

**Check the output:** `interruption_log_proof.txt` will be generated in the root directory.

### 2. Run Formal PyTest Requirements
This runs the full test suite asserting all edge cases (backchannel, interrupt, silent, mixed).

```bash
python -m pytest examples/voice_agents/test_timing_race.py -v
```

---

## Summary: Why This Solves the Task

| Requirement | How It's Solved |
| :--- | :--- |
| **Ignore "yeah" while speaking** | Buffered VAD + semantic discard |
| **Stop on "stop"** | Interim + final STT keyword interrupt |
| **Mixed input handling** | Semantic classifier dominance |
| **State awareness** | `AgentStateTracker` |
| **No stutter / pause** | Audio never cut until semantic confirmation |
| **No VAD modification** | Logic layer interception only |
| **Real-time** | Async, streaming, low latency strategies |
| **Race-safe** | VAD is soft signal, STT is authoritative |

The system converts VAD from an **irreversible interrupt trigger** into a **provisional signal** pending semantic validation. This matches how production-grade voice assistants avoid false barge-ins and conversational breakdowns.