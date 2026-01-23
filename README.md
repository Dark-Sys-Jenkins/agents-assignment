# Intelligent Interruption Handling for LiveKit Agents

## 📝 Overview

This project implements **Intelligent Interruption** logic for LiveKit Voice Agents. It solves the common problem where agents abruptly stop speaking when users provide passive feedback (backchanneling) like "yeah", "ok", or "hmm".

**Key Features:**
- **Context-Awareness**: Distinguishes between **Passive Acknowledgement** (fillers) and **Active Interruption** (commands).
- **State-Based Logic**:
    - **Speaking State**: Ignores filler words; stops only for commands (e.g., "stop", "wait").
    - **Silent State**: Responds to filler words as valid input (e.g., "Yeah?" -> "How can I help?").
- **Mixed Input Handling**: Correctly interrupts for compound phrases like "Yeah wait" (contains command "wait").

## 📂 Core Implementation Files

The solution is implemented and verified through the following key files:

- **`examples/test_interruption_agent.py`**:
    - The main Voice Agent implementation tailored for this challenge.
    - Configured with `allow_interruptions=True` and acts as the reference for the playground compatibility.

- **`examples/test_interruption_console.py`**:
    - A specialized **Console-Mode Agent** for rapid local testing without a frontend.
    - Logs internal events like `agent_false_interruption` to visualize the logic in real-time.

- **`tests/test_interruption_scenarios.py`**:
    - A robust `pytest` suite ensuring the logic holds under various conditions.
    - Covers scenarios: Filler during speech, Commands ("stop"), Silent prompts, and Stress tests (rapid fire, gibberish).

## ⚙️ Configuration & Environment

To run this agent, you must configure the following:

1. **Environment Variables**:
   Copy `.env.template` to `.env` and fill in your API keys:
   ```bash
   cp examples/.env.template examples/.env
   ```
   **Required Keys in `.env`:**
   ```ini
   LIVEKIT_URL=...
   LIVEKIT_API_KEY=...
   LIVEKIT_API_SECRET=...
   DEEPGRAM_API_KEY=...
   GROQ_API_KEY=...
   CARTESIA_API_KEY=...
   ```

2. **Logic Configuration (`agent_activity.py` & `.env`)**:
   The core logic works by utilizing the `resume_false_interruption` flag in the agent options.
   - **`resume_false_interruption=True`**: Enables the agent to resume speech if the interruption was determined to be a "false alarm" (filler word).
   - **Filter Words**: The list of ignored words is managed internally but can be extended via environment variables if configured in the agent script.

## 🚀 Usage

### 1. Install Dependencies
**CRITICAL**: You must install `livekit-agents` in editable mode to ensure local changes to the core logic (`agent_activity.py`) are active.

```bash
pip install -r requirements.txt
```
*(This includes `-e livekit-agents` automatically)*

### 2. Run Console Test (Recommended for Logic Verification)
This runs the agent in your terminal. You can speak to it, and it will log whether it detected a "False Interruption".
```bash
python examples/test_interruption_console.py
```
*Try saying "Yeah" while it speaks. It should log a warning but continue speaking.*

### 3. Run Agent for LiveKit Playground
To test with the visual frontend:
```bash
python examples/test_interruption_agent.py dev
```
Then connect via [https://agents-playground.livekit.io/](https://agents-playground.livekit.io/).

## 🧪 Testing

Run the automated scenario suite to verify all logic branches:

```bash
# Run the manual test suite (ensuring local code is used)
PYTHONPATH=livekit-agents .venv/bin/python -m tests.test_interruption_scenarios
```

**What this tests:**
- ✅ **Scenario 1**: Agent ignores "yeah" while speaking.
- ✅ **Scenario 2**: Agent stops for "stop".
- ✅ **Scenario 3**: Agent responds to "yeah" when silent.
- ✅ **Scenario 4**: Agent interrupts for "yeah wait".
- ✅ **Stress Tests**: Rapid filler flood, gibberish handling, etc.
