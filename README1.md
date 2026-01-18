# LiveKit Intelligent Interruption Handling (Backchannel Fix)

This repository contains a fix for LiveKit voice agents where **backchannel words**
(e.g. “yeah”, “ok”, “hmm”, “mhm”) were incorrectly treated as **interruptions**
while the agent was speaking.

The goal is to make interruption handling **context-aware**:

- If the agent is speaking and the user says a filler/backchannel word → **IGNORE**
- If the agent is silent and the user says a filler/backchannel word → **RESPOND**
- If the user says an actual interrupt command (“stop”, “wait”, “no”) → **INTERRUPT**
- If the user says a mixed sentence (“yeah wait a second”) → **INTERRUPT**

This solution is implemented as a **logic layer** inside the agent loop.
No low-level VAD kernel modifications were made.

---

## Problem Summary

LiveKit’s default interruption behavior relies heavily on **VAD (Voice Activity Detection)**.

VAD triggers extremely fast, so even small user acknowledgements like:

- “yeah”
- “ok”
- “hmm”
- “mhm”

were detected as “user started speaking” and the agent would stop mid-sentence.

This breaks natural conversational flow, because these are **passive acknowledgements**
(backchanneling), not real interruptions.

---

## Solution Overview

The fix introduces **STT-based validation** before performing an interruption.

### Key idea: “STT validation gate”

Because VAD is faster than STT, we do NOT immediately interrupt when VAD detects speech.
Instead, we wait a very small delay for STT text to arrive and then decide:

- If transcript is only backchannel words → ignore completely (do not interrupt)
- If transcript contains interruption keywords (“stop”, “wait”, “no”) → interrupt
- If transcript contains real content → interrupt

This keeps the system real-time and avoids noticeable latency.

---

## What Was Changed

### 1) Added Configurable Session Options

File:

- `livekit/agents/voice/agent_session.py`

New options:

- `backchannel_ignore_words`
- `interruption_keywords`
- `backchannel_validation_delay`

Default ignore words include:

- `yeah, ok, okay, hmm, mm, mhm, uh-huh, aha, right, ...`

Default interruption keywords include:

- `stop, wait, no, pause, hold, cancel, quit`

This makes the solution modular and easy to tune.

---

### 2) Added Backchannel Decision Logic + Pending Timer

File:

- `livekit/agents/voice/agent_activity.py`

Main changes:

- Added normalization + tokenization helpers
- Added `_is_backchannel_only()` and `_should_interrupt_on_text()`
- Updated `_interrupt_by_audio_activity()` to support transcript-based decisions
- Introduced `_pending_interruption_timer` to delay interruption briefly until STT arrives

This prevents the agent from stopping immediately on backchannel VAD triggers.

---

### 3) Added Transcript Filtering in Recognition Pipeline

File:

- `livekit/agents/voice/audio_recognition.py`

Main changes:

- Added hook: `should_ignore_transcript(text, is_final)`
- While agent is speaking, drop backchannel-only interim/final transcripts completely
- Added a small heuristic to rewrite meaningless “mhm/yeah” into `"continue"`
  only when the last assistant message was not a question

This prevents unwanted user turns and keeps conversation clean.

---

## How It Meets the Challenge Requirements

Required behavior matrix:

| User Input         | Agent State | Expected                            |
| ------------------ | ----------- | ----------------------------------- |
| “Yeah / Ok / Hmm”  | Speaking    | IGNORE (agent continues speaking)   |
| “Wait / Stop / No” | Speaking    | INTERRUPT (agent stops immediately) |
| “Yeah / Ok / Hmm”  | Silent      | RESPOND normally                    |
| “Start / Hello”    | Silent      | RESPOND normally                    |

This implementation satisfies all scenarios including “mixed input” like:

- “Yeah okay but wait” → interrupts due to keyword detection.

---

## How To Run

### 1) Create and activate a virtual environment

Windows (PowerShell):
powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

### 2) Install Depndencies:

pip install -r requirements.txt

### 3) Run the sample voice agent in console mode

python examples/voice_agents/basic_agent.py console
