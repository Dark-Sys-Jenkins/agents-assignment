# Intelligent Interruption Handler (LiveKit Agent)

**Submitted by:** Kriti Gupta
**Assignment:** LiveKit Intelligent Interruption Challenge

## 🚀 Overview
This project implements a context-aware Voice Activity Detection (VAD) logic layer for a LiveKit AI agent. The goal is to distinguish between "passive backchanneling" (e.g., "yeah", "ok") and "active interruptions" (e.g., "stop", "wait") to create a seamless conversational experience.

## 🛠 Key Features Implemented

### 1. Seamless "Ignore" Logic
- **Problem:** Standard VAD cuts off the agent immediately when the user makes any sound.
- **Solution:** I implemented a logic layer that filters user input based on the agent's state (Speaking vs. Silent).
- **Result:** If the agent is speaking and the user says *"Yeah"* or *"Uh-huh"*, the agent **continues speaking without pausing or stuttering**.

### 2. Context-Aware Interruption Matrix
The agent follows this strict logic matrix:

| Agent State | User Says | Action |
| :--- | :--- | :--- |
| **Speaking** | "Yeah", "Ok", "Hmm" | **IGNORE** (Continue speaking) |
| **Speaking** | "Stop", "Wait", "No" | **INTERRUPT** (Stop audio immediately) |
| **Speaking** | "Yeah wait" (Mixed) | **INTERRUPT** (Treat as command) |
| **Silent** | "Yeah", "Ok" | **RESPOND** (Treat as valid answer) |

### 3. VAD "Hiccup" Fix
- Modified the `AgentSession` configuration to include `interrupt_speech_duration=0.5`.
- This creates a small buffer window that prevents the hardware VAD from cutting audio before the logic layer validates the text.

## 📂 Project Structure

- **`interrupt-handler-KritiGupta.py`**: Main entry point containing the agent logic, event loop, and VAD configuration.
- **`key_words.py`**: Configurable lists for `Soft_word` (ignore) and `Hard_word` (interrupt) vocabularies.
- **`LOGS/`**: Contains the proof of execution (`logs.txt`).

## ⚡ How to Run
Start the Agent:

Bash
python interrupt-handler-KritiGupta.py dev
Connect:

Go to meet.livekit.io

Connect and speak to the agent.

✅ Proof of Work
A full transcript log and also video demonstrating the "Ignore" and "Interrupt" scenarios can be found in: LOGS/logs.txt

