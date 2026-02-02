# Intelligent Interruption Handling for LiveKit Voice Agent

## Overview

This document explains the modifications made to `basic_agent.py` to implement intelligent interruption handling that distinguishes between **filler words** (acknowledgments like "yeah", "okay") and **command words** (interruptions like "stop", "wait").

---
## Student Details
- **Name:** Sirjan Singh
- **College Roll Number:** 23UCS715
- **Demo Video Link:** [Drive Link](https://drive.google.com/drive/folders/1LXnojdfCtswc14PxWH60ZqynbLN03F3J?usp=sharing)
  
---

## The Challenge

In a natural voice conversation, users often say acknowledgment words like "yeah", "okay", or "hmm" while the agent is speaking. These are **backchannel responses** that mean "I'm listening, continue" — not "stop talking."

However, LiveKit's default Voice Activity Detection (VAD) treats ALL user speech as potential interruptions, causing the agent to stop mid-sentence when hearing these fillers.

**Requirements:**
1. **When agent is speaking + user says filler** → Agent continues uninterrupted
2. **When agent is speaking + user says command** → Agent stops immediately  
3. **When agent is silent** → All user speech is valid input
4. **Mixed input** → Commands always take priority over fillers (e.g., "yeah wait" is a command)

---

## The Core Problem: Timing

The fundamental challenge is **VAD interrupts BEFORE transcripts arrive**:

```
Time 0.0s: User starts saying "yeah"
Time 0.3s: VAD detects speech → Interrupts agent
Time 0.5s: User finishes saying "yeah"  
Time 0.8s: Transcript arrives → "Yeah."
```

By the time we know it was a filler word, the agent has already stopped!

---

## The Solution: Hybrid Approach

We use a **three-layer defense system**:

### Layer 1: Medium VAD Thresholds
```python
min_interruption_duration=0.6,  # Requires 0.6 seconds of speech
min_interruption_words=2,        # Requires at least 2 words
```

**Purpose:** Filters out very quick, single-word fillers ("yeah!", "okay!")

**Tradeoff:** Longer fillers (1.5s "okaaaay") can still slip through

---

### Layer 2: Automatic Resume on False Interruptions
```python
resume_false_interruption=True,
false_interruption_timeout=1.0,
```

**Purpose:** If VAD interrupts the agent, LiveKit waits 1 second for more user speech. If nothing substantial comes, it automatically resumes the agent's speech.

**How it helps:** When a slow filler ("okaaaay") interrupts the agent, this mechanism resumes automatically within 1 second.

---

### Layer 3: Transcript-Based Classification (The Brain)
The most important layer — our custom logic that analyzes transcripts. This layer enforces strict priority: **Commands > Real Input > Fillers**.

#### Key Logic Flow:
```python
@session.on("user_input_transcribed")
def on_user_input_transcribed(ev):
    text = normalize_text(ev.transcript)
    
    # 1. CHECK COMMANDS FIRST (Priority!)
    if contains_command(text):
        if agent.is_speaking:
            session.interrupt()  # Force stop if VAD missed it
        return # Let LLM process the command
        
    # 2. CHECK FILLERS SECOND
    if is_filler_input(text):
        # Suppress from LLM so agent doesn't respond to "yeah"
        try_clear_user_turn(session) 
        return
        
    # 3. REAL INPUT (Questions, conversation)
    # Process normally
```

This handles three cases:

#### Case 1: Agent Was Just Interrupted by VAD
- **Command:** Valid interruption, let LLM respond.
- **Filler:** False alarm! `resume_false_interruption` will auto-resume speech. We call `clear_user_turn()` so the LLM doesn't hear "yeah".
- **Real Input:** Valid interruption.

#### Case 2: Agent Is Currently Speaking (VAD Hasn't Triggered Yet)
- **Command:** Force immediate interrupt (`session.interrupt()`).
- **Filler:** Ignore completely (`clear_user_turn()`).
- **Real Input:** Allow interrupt (`session.interrupt()`).

#### Case 3: Agent Is Idle
- **Command/Real Input:** Process normally.
- **Filler:** Suppress (don't wake up LLM for just "okay").

---

## Key Code Changes (Refactored)

### 1. Robust Word Lists

**Command Detection** (Stop Phrases & Prefixes):
```python
# Single words
STOP_WORDS = {"wait", "stop", "finish", "hold", "pause", "halt", ...}

# Multi-word phrases (normalized)
STOP_PHRASES = {"holdon", "waitasecond", "stopit", "waitaminute", ...}

# Prefixes that can precede commands
COMMAND_PREFIXES = {"no", "but", "and", "okay", "please", "hey"}
```
*Now catches:* `"no wait"`, `"hold on"`, `"wait a second"`, `"yeah stop"`

**Filler Words** (Strict filtering):
```python
FILLER_WORDS = {
    "uhhuh", "okay", "alright", "mhm", "yeah", "yep", "yup",
    "hmm", "right", "uh", "um", "ah", "cool", "great", "no", "nah"
    # Removed generic words like "i", "see", "all" to avoid false positives
}
```

### 2. Detection Functions

**`contains_command(transcript)`**:
- Checks for multi-word phrases (`"hold on"`).
- Checks for prefixes (`"no wait"`).
- Checks priority positions (first 3 words).

**`is_filler_input(transcript)`**:
- **CRITICAL:** Calls `contains_command()` first! If it's a command, it is NOT a filler.
- Only matches if input is *purely* filler words/phrases.

### 3. Transcript Suppression
We use a helper to prevent the LLM from responding to fillers:
```python
def try_clear_user_turn(session):
    if hasattr(session, 'clear_user_turn'):
        session.clear_user_turn()
```

---

## How It All Works Together (Examples)

### Scenario 1: User says "yeah" (0.3s, quick acknowledgment)
1. ✅ **VAD Layer:** Too short (< 0.6s) → No interrupt
2. ✅ **Transcript Layer:** `is_filler_input` = True. `try_clear_user_turn()` called.
3. ✅ **Result:** Agent continues speaking. LLM sees nothing.

### Scenario 2: User says "okaaaay" (1.5s, slow filler)
1. ❌ **VAD Layer:** Long enough (> 0.6s) → Interrupts agent
2. ✅ **Resume Layer:** Waits 1s, decides it's a false interrupt → Resumes
3. ✅ **Transcript Layer:** `is_filler_input` = True. Suppresses transcript.
4. ✅ **Result:** Brief pause (1s), then agent resumes.

### Scenario 3: User says "no wait" (Quick command)
1. ❌ **VAD Layer:** Might be too short or missed.
2. ✅ **Transcript Layer:** `contains_command` = True (catches "no" + "wait").
3. ✅ **Action:** `session.interrupt()` forced immediately.
4. ✅ **Result:** Agent stops. LLM processes "no wait".

### Scenario 4: User says "I have a question"
1. ✅ **Transcript Layer:** Not a command, not a filler.
2. ✅ **Action:** Real input. Interrupts agent.
3. ✅ **Result:** Standard conversation flow.

---

## Files Modified

- **`basic_agent.py`** — Main implementation with all intelligent interruption logic.

## Dependencies

No additional dependencies required. Uses standard Python `re` and LiveKit Agents SDK.

---

## Future Improvements

1. **Semantic Analysis:** Use a small NPU/LLM model to determine if "right" means "correct" (answer) or "continue" (filler).
2. **Prosody Analysis:** Differentiate "stop?" (question) from "STOP!" (command) based on pitch/volume.
