# 🎙️ LiveKit Intelligent Interruption Handling  
### Challenge Submission

**Author:** N M Amlan  
**GitHub:** https://github.com/Amlan-0001  
**Branch:** `feature/interrupt-handler-amlan`

---

## 📌 Overview

This project implements **context-aware intelligent interruption handling** for a real-time **LiveKit voice agent**.

By default, LiveKit’s **Voice Activity Detection (VAD)** is overly sensitive and treats listener backchanneling  
(e.g., **“yeah”**, **“ok”**, **“hmm”**) as interruptions.  
This causes the agent to **pause or stop mid-sentence**, degrading conversational quality.

This solution introduces a **logic layer above VAD** that correctly distinguishes between:

- **Passive acknowledgements (backchanneling)**
- **Active interruptions (explicit commands)**

✅ No VAD kernel modifications  
✅ Implemented entirely inside the agent event loop  
✅ Fully real-time with imperceptible latency  

---

## ❗ Problem Statement

### When the agent is speaking
- User says **“yeah” / “ok” / “hmm”** → ❌ Agent must **NOT stop**
- User says **“stop” / “wait” / “no”** → ✅ Agent must **stop immediately**

### When the agent is silent
- User says **“yeah”** → ✅ Agent should respond normally
- User says **“hello” / “start”** → ✅ Normal conversational behavior

---

## 🎯 Goal

Implement **state-aware interruption logic** such that:

- The **same word** (e.g., *“yeah”*) is treated **differently**
- Behavior depends on whether the **agent is speaking or silent**
- Mixed inputs like **“yeah wait”** correctly trigger interruption

---

## 🧠 Logic Matrix

| User Input        | Agent State | Expected Behavior |
|------------------|------------|-------------------|
| yeah / ok / hmm  | Speaking   | IGNORE            |
| stop / wait / no | Speaking   | INTERRUPT         |
| yeah / ok / hmm  | Silent     | RESPOND           |
| hello / start    | Silent     | RESPOND           |
| yeah wait        | Speaking   | INTERRUPT         |

---

## 🛠️ Solution Design

### Key Concepts Used

#### 1️⃣ Configurable Word Lists
- **Ignore words** → soft listener acknowledgements  
- **Interrupt words** → explicit stop commands  

#### 2️⃣ Agent Speaking State
- Tracked using `tts_start` and `tts_end` events

#### 3️⃣ Transcription-Based Filtering
- Uses STT output to semantically classify user intent
- Prevents false interruptions caused by early VAD triggers

#### 4️⃣ Hard-Drop Strategy
- Backchannel words while speaking are **fully ignored**
- No pause, no resume, no stutter

---

## 🧩 Implementation Details


## 📂 Modified File

- `examples/voice_agents/basic_agent.py`

No new dependencies were added.  
`requirements.txt` remains unchanged.

---



## 🧪 Proof of Correct Behavior (Log Transcript)
The following log transcript demonstrates all required scenarios:

text
Copy code
### ✅ LiveKit Intelligent Interruption Handling – Proof Logs

Agent: Kelly
Mode: Console
Purpose: Demonstrate correct handling of backchannel vs interruption
Environment: LiveKit Agents, STT = Deepgram Nova-3, TTS = Cartesia Sonic-2

#### 🧪 Scenario 1 – Backchannel While Agent is Speaking (IGNORE)

Expected Behavior:
Agent must continue speaking when user says filler words like yeah / okay / yes.

Transcript Evidence
[AGENT] Speaking: Long story generation in progress

[USER] "Yes."
[STATE] agent_speaking = True
[DECISION] IGNORE (backchannel)
[RESULT] Agent continues speaking

[USER] "Yeah."
[STATE] agent_speaking = True
[DECISION] IGNORE (backchannel)
[RESULT] Agent continues speaking

[USER] "Okay."
[STATE] agent_speaking = True
[DECISION] IGNORE (backchannel)
[RESULT] Agent continues speaking


✔️ PASS — Agent does not stop or pause on passive acknowledgements.

#### 🧪 Scenario 2 – Mixed Input While Speaking (INTERRUPT)

Expected Behavior:
If user says a filler plus an interrupt command, the agent must stop.

Transcript Evidence
[AGENT] Speaking: Story narration

[USER] "Yeah. Wait. Wait."
[STATE] agent_speaking = True
[DETECTED] interrupt_word = "wait"
[DECISION] INTERRUPT
[RESULT] Agent stops immediately


✔️ PASS — Semantic interruption detected correctly.

#### 🧪 Scenario 3 – Hard Stop Command While Speaking (INTERRUPT)

Expected Behavior:
Agent must stop immediately on commands like stop / wait / no.

Transcript Evidence
[AGENT] Speaking

[USER] "Okay. Stop."
[STATE] agent_speaking = True
[DETECTED] interrupt_word = "stop"
[DECISION] INTERRUPT
[RESULT] Agent stops immediately


✔️ PASS — Hard interruption works correctly.

#### 🧪 Scenario 4 – Backchannel While Agent is Silent (RESPOND / ACCEPT)

Expected Behavior:
When the agent is silent, short acknowledgements are treated as valid input.

Transcript Evidence
[AGENT] Silent

[USER] "Yeah."
[STATE] agent_speaking = False
[DECISION] NORMAL INPUT
[RESULT] Input passed to LLM for response


✔️ PASS — State-aware filtering works.
✅ What This Proves
✔ Agent continues speaking over “yeah / ok / hmm”

✔ Agent responds to “yeah” when silent

✔ Agent immediately stops on “stop”

✔ No partial pauses, hiccups, or resumptions

## 🎥 Video Demonstration
A short screen recording was created showing:

Agent telling a long story

User saying “okay… yeah… hmm” while the agent is speaking

Agent continues seamlessly without interruption

User says “stop”

Agent immediately halts

📎 Video provided separately as per submission instructions.






