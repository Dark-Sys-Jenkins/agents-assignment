# LiveKit Voice Agent – Smart Interrupt + Resume (Backchannel Handler)
video-demo-link: https://drive.google.com/file/d/16BUG2mXjcEYcAaihq4nF53NeLS74VHPl/view?usp=sharing
This project gives you a voice agent that:
- stops instantly when the user says a command like “stop”, “wait”, “hold on”
- supports “soft” command phrases like “yeah wait a second”
- lets the user resume the agent’s previous speech by saying “yeah / ok / hmm” right after stopping
- does NOT swallow “yeah/ok/hmm” when the agent is silent (so yes/no answers still work)
- avoids annoying “double commits” and accidental swallowing of the user’s next real prompt

---

## What you get

### 1) Real-time interruption
While the agent is speaking:
- “stop” → agent stops immediately
- “wait” / “hold on” / “hang on” → agent stops immediately
- “yeah wait a second” → agent stops immediately (backchannel lead-in supported)

### 2) Resume mode (after stop)
After you stop the agent:
- A short resume window opens (default: 15 seconds)
- If the user says “yeah / ok / hmm / uh-huh” during that window:
  - that word is swallowed (it does NOT become a user prompt)
  - the agent continues the previous response from where it stopped

### 3) Backchannels are not swallowed when silent
When the agent is NOT speaking:
- “yeah” is NOT swallowed (outside resume window)
- “ok” is NOT swallowed (outside resume window)
This is important because it lets the user answer yes/no questions naturally.

### 4) No accidental “next prompt swallowing”
We use a time-bounded swallow window (default: 1s) so if we swallow something, we swallow only the intended utterance, not the user’s next real sentence.

### 5) Debounced commit
We delay commit slightly (default: 350ms) so the user can speak naturally without the system committing too early.

---

## Files

- `examples/voice_agents/backchannel_handler.py`
  - core logic: detect backchannels, commands, pause state, resume window, swallow window
- `examples/voice_agents/basic_agent.py`
  - LiveKit agent wiring
  - session config
  - debounced commit
  - example tool: weather lookup (Open-Meteo)

---

## How it works (mental model)

### A) Agent is speaking
User transcript arrives:

1. If it’s a command:
   - interrupt immediately
   - swallow that utterance (so it doesn’t become a user prompt)
   - set paused_by_stop = True
   - open resume window

2. If it’s a pure backchannel (“yeah”, “ok”, “hmm”):
   - swallow (so it doesn’t derail the agent mid-sentence)

3. If it’s real user speech (not a backchannel):
   - interrupt
   - keep it as a normal user turn (it will commit normally)

### B) Agent is silent
User transcript arrives:

1. If resume window is active and user says a backchannel:
   - swallow it
   - generate a continuation reply (instructions-only, not a user prompt)

2. If resume window is NOT active and user says a backchannel:
   - allow it (commit normally)
   - this keeps yes/no answers working naturally

3. If user says a command while silent:
   - swallow it (it should not become a prompt)

---

## Command detection (important)

We detect commands in two ways:

### 1) Direct command
Examples:
- “stop”
- “wait”
- “pause”
- “cancel”
- “hold on”
- “hang on”

### 2) Backchannel lead-in + command (your requirement)
Examples:
- “yeah wait a second”
- “ok hold on”
- “hmm hang on one sec”

Rule:
- We allow a leading backchannel (“yeah/ok/hmm”) before a command
- We only treat it as command if the command phrase is at the start after removing the lead-in

This avoids false positives like:
- “I can’t wait for tomorrow”  (not treated as a command because “wait” is not at the start)

---

## Environment variables (optional)

You can override phrases without changing code.

### BACKCHANNEL_IGNORE_WORDS
Comma-separated.
Example:
BACKCHANNEL_IGNORE_WORDS="yeah,ok,okay,hmm,uh huh,mm hmm"

### BACKCHANNEL_COMMAND_WORDS
Comma-separated.
Example:
BACKCHANNEL_COMMAND_WORDS="stop,wait,pause,cancel,hold on,hang on"

### BACKCHANNEL_NEGATION_WORDS
Comma-separated.
Example:
BACKCHANNEL_NEGATION_WORDS="no,nope,nah"

---

## Key tuning knobs

In `backchannel_handler.py`:
- `resume_window_seconds` (default 15.0)
  - how long user can say “yeah/ok/hmm” to resume after stopping
- `swallow_window_seconds` (default 1.0)
  - protects against swallowing the next real prompt
- `fast_command_partial_word_limit` (default 4)
  - allows early interruption on partial transcripts

In `basic_agent.py`:
- debounce delay: `await asyncio.sleep(0.35)`
  - increase to 0.5 if you still see premature commits
- Silero VAD:
  - `min_silence_duration=0.60` is a good start
  - increase to 0.75–0.90 if the system cuts users off too early

---

## Quick start
## Install

This repo uses uv (pyproject.toml is the source of truth). You do not need requirements.txt.
- livekit agents + plugins
- deepgram stt
- gemini llm
- cartesia tts
- requests, python-dotenv

### 2) Run the agent
Option A (recommended): uv
- cd ~/agents-assignment (if on wsl)
- uv sync --dev
- uv run examples/voice_agents/basic_agent.py

Option B: pip + venv (fallback)
- python3 -m venv .venv
- source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python examples/voice_agents/basic_agent.py




