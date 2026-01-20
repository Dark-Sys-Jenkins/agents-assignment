# Interrupt-Aware Voice Agent (LiveKit)

## Overview
This project implements an interrupt-aware voice agent using the LiveKit Agents framework.
The agent intelligently distinguishes between passive acknowledgements (e.g. "yeah", "okay")
and real interruption commands (e.g. "stop", "wait") while speaking.

The solution is implemented purely as a logic layer on top of LiveKit’s existing framework,
without modifying the VAD kernel.

---

## Key Features 

### 1. Configurable Ignore List
- Implemented via `IGNORE_WORDS` and `INTERRUPT_WORDS`
- Easy to extend or modify

### 2. State-Based Filtering
- Interruption logic applies **only when the agent is speaking**
- Normal processing when the agent is silent

### 3. Semantic Interruption
- Mixed phrases like `"yeah but wait"` are detected correctly
- Any interrupt keyword causes an immediate stop

### 4. No VAD Modification
- Uses LiveKit event hooks (`agent_state_changed`, `user_input_transcribed`)
- No changes to low-level VAD or STT components


## How Stop Is Handled
- `session.cancel_answer()` immediately halts speech
- `session.clear_user_turn()` prevents auto-resume
- Agent asks: *"Is there something else I can help you with?"*

---

## How to Run

```bash
python resume_interrupted_agent.py dev
