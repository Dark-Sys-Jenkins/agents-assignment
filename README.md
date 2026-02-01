# Intelligent Interruption Voice Agent - GenAI Assignment

## Overview
This project implements a voice AI agent with **Intelligent Interruption Handling**. The goal is to allow users to provide "passive feedback" (like "yeah", "ok", "mhm") without stopping the agent's speech, while still allowing "active interruptions" (like "stop", "wait", or meaningful questions) to take effect immediately.

## File Structure
- `examples/voice_agents/intelligent_interruption.py`: The main entry point for the LiveKit agent. Handles session management and event listeners.
- `examples/voice_agents/logic.py`: The modular core logic that handles text classification and interruption decisions.
- `.env`: Contains your API keys.

---

## Setup & Running

### 1. Prerequisites
Ensure you have a Python virtual environment set up and active.
```powershell
.\scvenv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r examples/voice_agents/requirements.txt
pip install livekit-plugins-groq livekit-plugins-cartesia
```

### 3. Configure API Keys
Fill in your `.env` file with the following:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` - Get from [LiveKit Console](https://cloud.livekit.io/)
- `GROQ_API_KEY` (Brain) - Get from [Groq Console](https://console.groq.com/keys)
- `DEEPGRAM_API_KEY` (Ears/Voice) - Get from [Deepgram Console](https://console.deepgram.com/)

### 4. Run the Agent
```powershell
.\scvenv\Scripts\python.exe examples/voice_agents/intelligent_interruption.py dev
```

---

## How the Logic Works

### 1. Disabling Default VAD Interruptions
Standard agents use Voice Activity Detection (VAD) to stop a speaker as soon as *any* sound is detected. This causes "hiccups" on simple breaths or filler words. 
In `intelligent_interruption.py`, we set `allow_interruptions=False`. This tells the agent: **"Don't stop talking until I manually tell you to."**

### 2. Manual Interruption Handler (`logic.py`)
Because we disabled automatic stopping, we use the `user_input_transcribed` event to analyze what the user actually said before deciding to stop.

#### A. The Ignore List (Soft Words)
We maintain an `IGNORE_WORDS` set (e.g., *yeah, ok, mhm, right, i see*). If the user's transcript consists **entirely** of these words, the logic returns `False` (Ignore), and the agent continues speaking seamlessly.

#### B. Explicit Commands
If the transcript contains words like *stop, wait, pause, quiet*, the handler returns `True` immediately, causing the agent to stop.

#### C. Semantic/Hard Interruptions
If the user says something that isn't in the ignore list (e.g., *"But why is that?"*), it's considered a "Hard" interruption.
- **Robustness Filter**: To prevent random stopping from background noise or STT "hallucinations", the logic requires either a long word (>5 chars) or at least 2 non-filler words to trigger a semantic interrupt.

### 3. State Awareness
The filtering only happens while the agent is **speaking** or **thinking**. If the agent is silent (IDLE), it will respond to everything, including a single "yeah", as a natural part of a conversation.

---

## Test Scenarios to Verify
1. **Passive Feed**: Say "yeah" while Kelly is explaining planets. She should not pause.
2. **Compound Feed**: Say "ok cool right" while she is talking. She should continue.
3. **Active Kill**: Say "Stop!" or "Wait!" -> She should stop instantly.
4. **Natural Response**: Wait for her to finish. Say "Yeah". She should respond back.
