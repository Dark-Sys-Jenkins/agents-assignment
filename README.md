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

## ▶️ How to Run

```bash
python examples/voice_agents/basic_agent.py console

⚠️ Note: The .env file is not committed (security best practice).

🧪 Proof of Correct Behavior (Log Transcript)
The following log transcript demonstrates all required scenarios:

text
Copy code
[TRANSCRIPT] speaking=True | text='yeah'
[DECISION] IGNORE (backchannel)

[TRANSCRIPT] speaking=True | text='okay'
[DECISION] IGNORE (backchannel)

[TRANSCRIPT] speaking=True | text='hmm'
[DECISION] IGNORE (backchannel)

[TRANSCRIPT] speaking=False | text='yeah'
[DECISION] NORMAL INPUT

[TRANSCRIPT] speaking=True | text='no stop'
[DECISION] INTERRUPT
✅ What This Proves
✔ Agent continues speaking over “yeah / ok / hmm”

✔ Agent responds to “yeah” when silent

✔ Agent immediately stops on “stop”

✔ No partial pauses, hiccups, or resumptions

🎥 Video Demonstration
A short screen recording was created showing:

Agent telling a long story

User saying “okay… yeah… hmm” while the agent is speaking

Agent continues seamlessly without interruption

User says “stop”

Agent immediately halts

📎 Video provided separately as per submission instructions.






