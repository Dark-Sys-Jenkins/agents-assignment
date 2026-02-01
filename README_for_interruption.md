# Interrupt-Aware Voice Agent (LiveKit)

This project implements an interrupt-aware voice agent that can distinguish
between conversational fillers (e.g. "yeah", "ok") and real interruption
commands (e.g. "stop", "wait") during speech generation.

## Problem
In default behavior, short utterances like "yeah" interrupt the agent mid-speech,
which leads to unnatural conversations.

## Solution
We introduced a lightweight interruption filtering layer that:

- Ignores filler words while the agent is speaking
- Allows the same words when the agent is silent
- Immediately interrupts on explicit commands like "stop"

## Key Design
- Interruption logic is isolated in `interruption_filter.py`
- Agent internals remain unchanged except for a minimal hook
- Word lists are configurable and easy to extend

## Files Changed
- `livekit/agents/voice/agent_session.py`
- `livekit/agents/voice/agent_activity.py`
- `livekit/agents/voice/interruption_filter.py`
- `examples/voice_agents/resume_interrupted_agent.py`

## Implementation Details

### 1. `interruption_filter.py`
This file contains all interruption-related decision logic and is intentionally
kept independent of agent internals.

Key logic:
- Defines configurable sets for:
  - conversational fillers (e.g. "yeah", "ok")
  - explicit interruption commands (e.g. "stop", "wait")
- Provides helper functions to classify user input:
  - `is_filler_only(text)` – detects non-interruptive acknowledgements
  - `is_real_interruption(text)` – detects commands that should interrupt speech

This makes the behavior easy to extend or tune without touching core agent code.

---

### 2. `agent_activity.py`
This file controls how the agent reacts while it is actively speaking.

Changes made:
- Integrated the interruption filter into the speech activity lifecycle
- When the agent is speaking:
  - filler-only inputs are ignored
  - real interruption commands immediately stop speech
- Preserves default behavior for all other cases

This ensures natural conversational flow without breaking existing logic.

---

### 3. `agent_session.py`
This file handles incoming user transcripts and routes them to the agent.

Changes made:
- Added a lightweight hook before scheduling interruptions
- Checks the current speaking state of the agent
- Delegates interruption decisions to the filter logic

This keeps session-level logic clean while enabling state-aware behavior.

---

### 4. `resume_interrupted_agent.py`
This example demonstrates and validates the new behavior.

Purpose:
- Shows the agent continuing speech over "yeah"/"ok"
- Demonstrates correct interruption on "stop"
- Confirms that short acknowledgements are still processed when the agent is silent

This file is used as the primary demo for evaluation.


## How It Works
1. User speech is transcribed
2. If the agent is currently speaking:
   - filler-only input is ignored
   - real interruption commands trigger an interrupt
3. If the agent is silent:
   - all input is processed normally

## Demo Scenarios
- Saying "yeah" while agent speaks → ignored
- Saying "yeah" when agent is silent → agent responds
- Saying "stop" anytime → agent stops speaking

## Running the Demo
```bash
python examples/voice_agents/resume_interrupted_agent.py dev

