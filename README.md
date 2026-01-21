# Voice AI Agent with Intelligent Interruption Handling

This repository contains a low-latency Voice AI agent built with LiveKit. The agent features custom logic to handle interruptions intelligently, distinguishing between active user speech and passive background acknowledgements (backchanneling).

## Features
- **Real-Time Voice Interaction**: High-speed, natural conversation flow.
- **Intelligent Interruption Layer**: Filters out filler words to prevent the agent from cutting off unnecessarily.
- **High-Performance Stack**: Utilizes Deepgram and Groq for industry-leading speed and accuracy.

## Tech Stack
- **Framework**: [LiveKit Agents](https://docs.livekit.io/agents/)
- **LLM**: [Groq](https://groq.com/) (Llama 3.3 70B)
- **STT/TTS**: [Deepgram](https://deepgram.com/) (Nova-2 / Aura)
- **VAD**: [Silero](https://github.com/snakers4/silero-vad) (Local)

## Intelligent Interruption Logic

Standard voice agents often suffer from oversensitivity, where the agent stops talking the moment it hears a small sound or a filler word like "yeah." This agent implements a custom logic layer in the `stt_node` to solve this issue.



### How it Works:
1. **Event Interception**: When the user starts speaking while the agent is active, the system intercepts the `START_OF_SPEECH` event and buffers it instead of stopping the agent immediately.
2. **Transcript Analysis**: The agent monitors the "interim" transcript of the user's speech while continuing its own turn.
3. **Filtering Decision**:
   - **Ignore List**: If the user says a word in the `IGNORE_WORDS` list (e.g., "yeah", "ok", "hmm"), the buffered interruption event is discarded. [cite_start]The agent continues speaking seamlessly[cite: 5].
   - [cite_start]**Active Interruption**: If the user says anything else (e.g., "Stop" or "Wait"), the buffered event is released, causing the agent to stop immediately and listen[cite: 5].
4. **Natural Turn-Taking**: If the agent is silent, all user speech is treated as a normal start of a turn, ensuring the agent remains responsive.

## Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.10 or higher installed.

### 2. Environment Variables
Create a `.env` file in the `examples/voice_agents/` directory:
```env
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

DEEPGRAM_API_KEY=your_deepgram_key
GROQ_API_KEY=your_groq_key
```

### 3. Installation
```python
pip install -r requirements.txt
```

### 4. Running the Agent
```python
python basic_agent.py dev
```
