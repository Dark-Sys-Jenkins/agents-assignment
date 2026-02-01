# Interrupt Handler Flow Diagram

This document explains the flow of the interrupt handler system used in the voice agent application.

## Overview

The interrupt handler manages user interruptions during agent speech, distinguishing between meaningful interruptions and backchannel responses (like "yeah", "ok", "hmm").

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VOICE AGENT SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐      ┌──────────────────┐                │
│  │ Voice Agent │─────▶│ Session Handlers │                │
│  └─────────────┘      └────────┬─────────┘                │
│                                 │                           │
│                                 ▼                           │
│                    ┌──────────────────────┐                │
│                    │ InterruptController  │                │
│                    └──────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Configuration

```
┌──────────────────────────────────────────────────────┐
│ INTERRUPT CONTROLLER CONFIGURATION                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Ignore Words (Backchannel):                        │
│ ┌────────────────────────────────────────────┐     │
│ │ yeah, ok, okay, hmm, uh, uh-huh,          │     │
│ │ aha, right, correct                        │     │
│ └────────────────────────────────────────────┘     │
│                                                      │
│ Interrupt Words (Explicit Commands):               │
│ ┌────────────────────────────────────────────┐     │
│ │ stop, wait, no, cancel, hold               │     │
│ └────────────────────────────────────────────┘     │
│                                                      │
│ Grace Period: 250ms                                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### State Variables

```
┌──────────────────────────────────────────┐
│ STATE TRACKING                           │
├──────────────────────────────────────────┤
│                                          │
│ agent_is_speaking    : Boolean          │
│   → TRUE when agent is speaking          │
│   → FALSE when agent is silent           │
│                                          │
│ pending_interrupt    : Boolean          │
│   → TRUE when user speaks during agent   │
│   → FALSE otherwise                      │
│                                          │
│ pending_since        : Timestamp        │
│   → Records when user started speaking   │
│                                          │
└──────────────────────────────────────────┘
```

## Event Flow

```
1. Agent Starts Speaking
   Agent → InterruptController
   ├─ Event: "agent_state_changed(speaking)"
   └─ Action: Set agent_is_speaking = TRUE

2. User Starts Speaking (While Agent is Speaking)
   User → VAD → InterruptController
   ├─ Event: "user_speech_detected"
   ├─ Action: Set pending_interrupt = TRUE
   └─ Action: Set pending_since = current_time

3. User Finishes Speaking
   User → STT → InterruptController
   ├─ Event: "user_input_transcribed(final)"
   └─ Action: Evaluate should_interrupt()

4. Interrupt Decision
   InterruptController evaluates:
   ├─ INTERRUPT → session.interrupt() → Agent stops
   └─ IGNORE → Agent continues speaking
```

## Interrupt Decision Logic

The system evaluates in **priority order** (top to bottom):

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Check for Explicit Interrupt Words                  │
├──────────────────────────────────────────────────────────────┤
│ Contains: "stop", "wait", "no", "cancel", "hold"?          │
│                                                              │
│ YES → ❌ INTERRUPT (Priority: HIGHEST)                       │
│ NO  → Continue to Step 2                                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Check Grace Period                                  │
├──────────────────────────────────────────────────────────────┤
│ Time since user started speaking > 250ms?                   │
│                                                              │
│ YES → ❌ INTERRUPT (Priority: HIGH)                          │
│ NO  → Continue to Step 3                                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Check for Backchannel Only                         │
├──────────────────────────────────────────────────────────────┤
│ Agent speaking AND all words are ignore words?              │
│ (yeah, ok, hmm, uh, etc.)                                   │
│                                                              │
│ YES → ✅ IGNORE (Backchannel Response)                       │
│ NO  → Continue to Step 4                                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ STEP 4: Check for Mixed/Semantic Input                     │
├──────────────────────────────────────────────────────────────┤
│ Agent speaking AND has meaningful tokens?                   │
│                                                              │
│ YES → ❌ INTERRUPT (Priority: NORMAL)                        │
│ NO  → ✅ IGNORE (Empty/No Content)                           │
└──────────────────────────────────────────────────────────────┘
```

## State Transitions

```
[Initial State]
      │
      ▼
┌──────────────┐
│ Agent Idle   │◀──────────────────┐
│ (Silent)     │                   │
└─────┬────────┘                   │
      │                            │
      │ agent_state_changed        │
      │ (speaking)                 │
      ▼                            │
┌──────────────────┐               │
│ Agent Speaking   │               │
│ agent_is_speaking│               │
│ = TRUE           │               │
└─────┬────────────┘               │
      │                            │
      │ user_speech_detected       │
      ▼                            │
┌──────────────────────┐           │
│ Pending Interrupt    │           │
│ pending_interrupt=TRUE│          │
│ pending_since=now()  │           │
└─────┬────────────────┘           │
      │                            │
      │ Evaluate Transcript        │
      ▼                            │
┌─────────────┐                    │
│  Decision   │                    │
├─────────────┤                    │
│ Interrupt?  │───YES──▶ INTERRUPT─┤
│             │         Agent stops │
│             │                     │
│             │───NO───▶ IGNORE     │
│                       Continue    │
└───────────────────────────────────┘
```

## Examples: When to Interrupt vs Ignore

### ❌ INTERRUPT Scenarios (Agent Speech is Canceled)

**Scenario 1: Explicit Interrupt Word**
```
Agent: "The Battle of Waterloo took place in..."
User: "STOP"
Result: ❌ INTERRUPT (Highest Priority)
```

**Scenario 2: Grace Period Expired**
```
Agent: "The Battle of Waterloo took place in..."
User: "What about..." (speaks for > 250ms)
Result: ❌ INTERRUPT (High Priority)
```

**Scenario 3: Meaningful Conversation**
```
Agent: "The Battle of Waterloo took place in..."
User: "Tell me about Paris instead"
Result: ❌ INTERRUPT (Normal Priority)
```

### ✅ IGNORE Scenarios (Agent Continues Speaking)

**Scenario 1: Backchannel Only**
```
Agent: "The Battle of Waterloo took place in..."
User: "yeah"
Result: ✅ IGNORE (Backchannel)
```

**Scenario 2: Multiple Backchannels**
```
Agent: "The Battle of Waterloo took place in..."
User: "ok hmm right"
Result: ✅ IGNORE (All Backchannel Words)
```

**Scenario 3: Empty/Silence**
```
Agent: "The Battle of Waterloo took place in..."
User: [no meaningful speech]
Result: ✅ IGNORE (No Content)
```

## Decision Priority Summary

```
Priority 1 (HIGHEST)   → Explicit interrupt words
        ↓
Priority 2 (HIGH)      → Grace period expired (>250ms)
        ↓
Priority 3 (MEDIUM)    → Check backchannel
        ↓
Priority 4 (NORMAL)    → Mixed/semantic input
        ↓
Default                → Ignore (no meaningful tokens)
```

## Component Details

### System Components

| Component | Responsibility |
|-----------|---------------|
| **InterruptController** | Core logic for evaluating interruptions |
| **Session Handlers** | Connects events to interrupt controller |
| **Voice Agent** | Main agent orchestrating the conversation |

### Configuration Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **ignore_words** | `yeah`, `ok`, `okay`, `hmm`, `uh`, `uh-huh`, `aha`, `right`, `correct` | Backchannel words that don't interrupt |
| **interrupt_words** | `stop`, `wait`, `no`, `cancel`, `hold` | Explicit commands that force interruption |
| **grace_ms** | `250ms` | Time window before treating speech as interruption |

## Implementation Files

- **interrupt_controller.py**: Core interrupt logic and decision-making
- **session_handlers.py**: Event handler registration and coordination
- **history_agent.py**: Main agent implementation using the interrupt controller

## Usage Example

```python
# Initialize the interrupt controller
interrupt_controller = InterruptController(
    ignore_words={"yeah", "ok", "hmm"},
    interrupt_words={"stop", "wait", "no"},
    grace_ms=250
)

# Register event handlers
register_interrupt_handlers(session, interrupt_controller, logger)
```
