

# LiveKit Intelligent Interruption Handling (Backchannel-Aware)

##  Author Details

**Name:** Kush Tokas 

**College:** IIIT D 

**Roll Number:** 2023296 

**Assignment:** LiveKit Agents — Intelligent Interruption Handling

---

##  Overview

This submission implements **context-aware interruption handling** for LiveKit Voice Agents by distinguishing between:

* **Passive backchannel acknowledgements**: `"yeah"`, `"ok"`, `"hmm"`, `"uh-huh"`
* **Active interruption commands**: `"stop"`, `"wait"`, `"pause"`, `"cancel"`, `"hold on"`

The system prevents the agent from being interrupted by natural conversational backchannels **while the agent is speaking**, but still allows **immediate interruption** when the user uses command-like words.

---

##  Problem Statement

In the default LiveKit agent pipeline, **Voice Activity Detection (VAD)** is highly sensitive and treats *any* user speech during agent output as an interruption.

This causes a common real-world failure:

> When the agent is explaining something and the user says “yeah” or “hmm” (backchanneling), the agent stops mid-sentence.

This breaks the conversational flow and makes the agent feel unstable and overly reactive.

---

##  What I Initially Did Wrong (Learning + Iteration)

During early attempts, I tried to solve the interruption problem at the **wrong layer** of the system.

### 1) Fixing too late in the pipeline

At first, I attempted to filter interruptions at a higher “conversation” level (or after events were already committed).
However, in real-time voice systems:

* **VAD triggers immediately**
* interruption logic may execute **before** transcription is finalized
* sometimes the transcript reaches the LLM quickly and the response begins generation

So even if I detected “yeah” later, the interruption had already happened or the LLM had already reacted.

### 2) Relying only on session configuration knobs

I explored parameters like:

* minimum interruption words/duration
* false interruption resume settings

These help reduce noise interruptions, but they **cannot distinguish meaning**, i.e.:

* “yeah” (acknowledgement)
* “stop” (command)

So configuration alone cannot satisfy the assignment requirement.

---

## Final Approach (What I Did Right)

The correct fix is to implement interruption handling **at the right layer**:

### ✔ Context-aware filtering between STT and interruption logic

I implemented a **semantic filter** that uses:

1. **Agent speaking state**
2. **Normalized transcript tokens**
3. **Command priority rules**

So the same word behaves differently depending on context:

* Agent speaking + “yeah” → ignored (no interruption)
* Agent silent + “yeah” → valid input (processed normally)
* Agent speaking + “stop” → interrupts immediately

---

##  Key Features

### State-Based Behavior

| Input          | Agent Speaking? | Result    | Why              |
| -------------- | --------------- | --------- | ---------------- |
| “yeah”         | Yes             | IGNORE    | backchannel      |
| “yeah”         | No              | PROCESS   | valid response   |
| “stop”         | Yes             | INTERRUPT | explicit command |
| “yeah wait”    | Yes             | INTERRUPT | command wins     |
| “hmm ok right” | Yes             | IGNORE    | pure backchannel |

### Semantic Priority (Commands Always Win)

If any explicit command word exists inside the transcript, interruption is allowed immediately even if backchannel words exist.

Example:
“yeah wait a second” → contains `"wait"` → **interrupt**

###  Normalization + Tokenization

The filter normalizes transcripts for reliability:

* lowercasing
* punctuation cleanup
* token extraction using regex (supports hyphenated tokens)

###  Edge Case Handling

The system safely handles empty / meaningless inputs:

* empty string
* whitespace-only
* punctuation-only

These are treated as **non-actionable** and do not cause unstable behavior.

---

##  Architecture

### High-Level Pipeline

```
User Speech (Audio)
    ↓
Voice Activity Detection (VAD)
    ↓
Speech-to-Text (STT)
    ↓
Interruption Filter (My Implementation)
    ↓
Decision: IGNORE or INTERRUPT
    ↓
Agent continues speaking OR stops immediately
```

### Why this layer matters

This approach prevents backchannels from becoming interruptions **before they reach the interruption handler / LLM**, avoiding real-time race conditions.

---

##  Files Changed / Added

### 1) `examples/voice_agents/basic_agent.py` (Modified)

This file was heavily updated (~80–90%) to implement a working demonstration agent.

Key changes include:

* agent speaking state tracking
* STT transcript interception and filtering
* smooth real-time behavior during speech

This file is the easiest way to demo the feature in a real voice session.

---

### 2) `intterrupt_audio_backend.py` (Added)

This file contains the reusable core implementation:

* `InterruptionSettings`
* `InterruptionHandler`
* decision logic: `should_ignore_interrupt(text, is_speaking)`

It supports:

* backchannel words
* backchannel phrases
* explicit command words
* debug explanations and structured decision reasons

---

### 3) `agent_activity.py` (Modified)

This integrates the interruption filter into the agent runtime activity logic.

Integration point calls:

```python
should_ignore = self._interrupt_filter.should_ignore_interrupt(
    text=text,
    is_speaking=is_speaking
)
```

If `should_ignore=True`, the interruption event is dropped and the agent continues naturally.

---

### 4) `interrupt_tests.py` (Added)

A full isolation-level test suite validating correctness across multiple scenarios.

This includes:

* pure backchannel while speaking
* explicit commands while speaking
* mixed backchannel + command
* same input behaving differently when agent is silent vs speaking
* edge cases like empty/whitespace/punctuation-only

---

## 🧪 Test Coverage (Isolation Level Validation)

### Running tests

```bash
python interrupt_tests.py
```

### What the tests validate

* backchannels do not interrupt while speaking
* commands always interrupt
* mixed phrases prioritize commands
* silent-state input is not ignored
* edge cases do not break the system

---

## 🎬 Live Demo Validation(demo_video.mov) (Real-Time Behavior)

This was also validated in a real voice agent session (not only unit tests).

### Demo Case 1: Backchannel During Explanation

Agent speaking:
User says: “yeah”, “ok”, “hmm”
✅ Agent continues smoothly without stopping.

### Demo Case 2: Explicit Interrupt

Agent speaking:
User says: “stop” / “wait”
✅ Agent stops immediately.

### Demo Case 3: Mixed Input

Agent speaking:
User says: “yeah but wait”
✅ Agent stops (command wins).

---

## 🧠 Decision Logic Summary

### Algorithm (simplified)

```
Input: (text, is_speaking)

1) Normalize + tokenize transcript
2) If empty/meaningless -> ignore safely
3) If contains explicit command -> DO NOT ignore (interrupt)
4) If pure backchannel AND agent is speaking -> ignore
5) Otherwise -> do not ignore
```

---

## 📌 References

* LiveKit Agents Documentation
* Backchannel communication concept (linguistics)
* GPT+LLMs

---

