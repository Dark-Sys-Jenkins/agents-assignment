# Interruption Test Agent

This project demonstrates an intelligent LiveKit agent with robust interruption handling, specifically designed to ignore common filler words (e.g., "yeah", "ok") while speaking, but remaining responsive to them as valid answers when silent.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- LiveKit Cloud or Self-Hosted instance
- API Keys for:
  - LiveKit
  - Deepgram (STT/TTS)
  - OpenRouter (LLM)

### 2. Environment Setup
Create a `.env` file in the root directory:
```bash
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENROUTER_API_KEY=your-openrouter-key
```

### 3. Run the Agent
```bash
python3 examples/voice_agents/interruption_test_agent.py dev
```

## 🧠 Interruption Logic (The "Smart Strategy")

The core challenge is that **VAD is faster than STT**. Standard agents interrupt immediately upon hearing any sound, which causes "hiccups" when the user says "yeah" just to acknowledge the agent.

### Our Strategy: **Wait-and-Validate**
1.  **VAD Trigger**: When the user starts speaking, the agent's VAD triggers.
2.  **SDK Hook**: We've modified the `AgentActivity._interrupt_by_audio_activity` method in the local SDK.
3.  **Validation**:
    - If the agent is speaking, it **waits** for the first transcript result.
    - If the transcript is empty or consists **only** of words in the `INTERRUPTION_IGNORE_LIST` (e.g., "yeah", "ok"), the agent **ignores** the interruption and continues speaking.
    - If the transcript contains any other word (e.g., "stop", "wait"), the agent interrupts immediately.
4.  **State Awareness**: This logic is only active while the agent is speaking. When the agent is silent, "yeah" is processed normally as a substantive answer.

## 🧪 Test Cases (Scenarios)

| Scenario | User Action | Expected Result |
| :--- | :--- | :--- |
| **1. Long Explanation** | Say "yeah... ok... uh-huh" while agent reads history. | Agent continues without any pause or hiccup. |
| **2. Passive Affirmation**| Agent asks "Ready?" and waits. User says "Yeah." | Agent treats "Yeah" as an answer and proceeds. |
| **3. Correction** | User says "No stop" while agent is speaking. | Agent cuts off immediately. |
| **4. Mixed Input** | User says "Yeah okay but wait" while agent is speaking. | Agent stops because "but wait" is not ignored. |

## 🛠️ Configuration

The agent is modular. You can easily change the behavior in `examples/voice_agents/agent_config.py`:

- `INTERRUPTION_IGNORE_LIST`: Add or remove words that the agent should ignore while speaking.
- `LLM_MODEL`: Change the underlying model (default: Llama 3.1 70B).
- `AGENT_INSTRUCTIONS`: Update the core behavior prompts.

## 📁 Project Structure
- `examples/voice_agents/interruption_test_agent.py`: Main entry point.
- `examples/voice_agents/agent_config.py`: Modular configuration.
- `livekit-agents/`: Local modified SDK containing the smart interruption hooks.
