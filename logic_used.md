# Backchannel Handling Logic (LiveKit Agents Fork)

This document describes the logic added/used to correctly handle **backchanneling**
(e.g. "yeah", "ok", "hmm") without incorrectly interrupting the agent speech.

The goal is to distinguish between:

- **Passive acknowledgement** (should NOT interrupt)
- **Active interruption intent** (should interrupt)

---

## 1) Definitions

### 1.1 Soft Backchannel Words (Passive)
Examples:
- "yeah", "ok", "okay", "hmm", "aha", "mhm"

These indicate the user is listening and acknowledging.
✅ **Must NOT interrupt** if the agent is currently speaking.

### 1.2 Hard Interrupt Words (Active)
Examples:
- "stop", "wait", "no", "pause", "hold on"

These indicate that the user wants the agent to stop.
✅ **Must interrupt immediately** if the agent is currently speaking.

---

## 2) State-Based Activation: Only Filter When Agent is Speaking

Backchannel filtering is applied ONLY when the agent is actively speaking.

The agent is considered "actively speaking" when either:
- `session.agent_state == "speaking"` OR
- there is an active `_current_speech` that has not finished

This is implemented using `_agent_is_actively_speaking()`.

✅ If the agent is NOT speaking (silent/listening), backchannel filtering does **not** modify the flow.

---

## 3) Main Trigger: User Activity While Agent is Speaking

### Trigger Event
When VAD (or audio activity) detects user speech while the agent is speaking:

- We do NOT interrupt immediately.
- We start a short validation window.
- We wait for transcript confirmation (STT text).

This is done via:
- `_request_interrupt_validation(reason=...)`

Purpose:
✅ Avoid stopping the agent due to backchannel noises.

---

## 4) Transcript Validation Rules

During the validation window, we check transcript content.

### 4.1 Case A: Agent Speaking + Soft Backchannel
Example:
- Agent is speaking
- User says: "yeah"

Expected behavior:
✅ **Do not interrupt**
✅ Agent continues smoothly

Logic:
- Transcript matches soft backchannel word set
- Interrupt is ignored
- No interrupt commit is executed

Outcome:
- `_interrupt_by_audio_activity_commit()` is NOT called

---

### 4.2 Case B: Agent Speaking + Hard Interrupt Intent
Example:
- Agent is speaking
- User says: "stop"

Expected behavior:
✅ **Interrupt immediately**

Logic:
- Transcript contains hard interrupt word
- Interrupt commit is triggered

Outcome:
- `_interrupt_by_audio_activity_commit()` IS called
- `_current_speech.interrupt()` executes (speech stops)

---

### 4.3 Case C: Agent Speaking + Unknown / Non-backchannel Speech
Example:
- Agent is speaking
- User says: "what about pricing?"

Expected behavior:
✅ Treat as an interruption request (normal interruption behavior)

Logic:
- Not a soft backchannel
- Considered meaningful input
- Interrupt commit is executed

Outcome:
- Agent is interrupted normally

---

## 5) Silent Agent Behavior (Agent NOT Speaking)

### Case D: Agent Silent + Soft Backchannel Word
Example:
- Agent is silent
- User says: "yeah"

Expected behavior:
✅ User input should be processed normally
✅ Agent should respond normally

Reason:
When the agent is silent, backchannel filtering has no meaning
because there is no agent speech to interrupt.

Logic:
- `_request_interrupt_validation()` early returns because agent is not actively speaking
- Transcript flows through normal handling (`on_final_transcript(...)`)

Outcome:
✅ No suppression / ignore logic is applied.

---

### Case E: Agent Silent + Hard Interrupt Word
Example:
- Agent is silent
- User says: "stop"

Expected behavior:
✅ No interruption needed (agent is already silent)
✅ Input is processed normally

Logic:
- No current speech exists to interrupt
- Transcript flows normally

Outcome:
✅ No change from original behavior.

---

## 6) Summary Table

| Scenario | Agent State | User Text | Expected Result |
|---------|-------------|----------|----------------|
| A | speaking | "yeah" | ✅ ignore, do NOT interrupt |
| B | speaking | "stop" | ✅ interrupt immediately |
| C | speaking | "what about..." | ✅ interrupt normally |
| D | silent | "yeah" | ✅ normal handling (respond) |
| E | silent | "stop" | ✅ normal handling (no effect) |

---

## 7) Why This Fix Works

This fix prevents the default overly-sensitive VAD behavior from causing false interruptions,
by requiring transcript validation before interrupting speech.

It ensures:
✅ backchannel does not interrupt agent speech  
✅ real interruptions still work  
✅ silent mode behavior remains unchanged
