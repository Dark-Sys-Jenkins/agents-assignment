# 🎭 Echo — Multi-Modal, Multi-Agent Voice Storyteller

Echo is a real-time, multi-modal voice assistant built on the LiveKit Agents SDK. It uses a structured, state-driven, multi-agent design that smoothly shifts from an information-gathering phase into a creative storytelling phase, powered by a modern AI stack.

This project demonstrates custom interruption handling, intelligent turn detection, and seamless agent handoff to deliver a natural and engaging voice experience.

---

## 🚀 Features

- **Multi-Agent Flow Control**  
  Uses a state-machine-based handoff to move from the `IntroAgent` (user data capture) to the `StoryAgent` (personalized narrative generation) without breaking conversation flow.

- **Smart Turn Detection**  
  - **Filler Filtering:** Ignores casual backchannel words like *“yeah”* and *“ok”* so the agent doesn’t lose momentum.  
  - **Priority Commands:** Instantly responds to hard commands such as *“STOP”* or *“PAUSE”* through a custom transcript listener.

- **Dynamic Personalization**  
  Collects user details like name and location to generate unique, real-time, customized stories.

- **Automated Session Cleanup**  
  Automatically shuts down resources and removes the LiveKit room once a session ends.

---

## 🛠️ System Architecture

| Component     | Technology                          |
|--------------|--------------------------------------|
| Orchestration | LiveKit Agents SDK (Python)        |
| Speech-to-Text | Deepgram (Nova-3 Model)         |
| Language Model | Google Gemini 2.0 Flash         |
| Text-to-Speech | ElevenLabs (Flash v2.5)        |
| Voice Activity Detection | Silero (Local Inference) |

---

## 📋 Requirements

- Python 3.11 or newer  
- LiveKit Cloud account and active project  
- API keys for:
  - Deepgram  
  - ElevenLabs  
  - Google (Gemini)

---

## ⚙️ Installation & Setup

1. Copy the source file from:  
   `examples/voice_agents/multi_agent.py`

2. Install the required packages:
   ```bash
   pip install livekit-agents livekit-plugins-deepgram livekit-plugins-elevenlabs livekit-plugins-silero livekit-plugins-google python-dotenv
   ```
3. Create a .env file in the root directory and add:
  ```bash
  LIVEKIT_URL=wss://your-project.livekit.cloud
  LIVEKIT_API_KEY=your_livekit_key
  LIVEKIT_API_SECRET=your_livekit_secret
  DEEPGRAM_API_KEY=your_deepgram_key
  ELEVEN_API_KEY=your_eleven_key
  GOOGLE_API_KEY=your_gemini_key
  ```
4. Download and initialize required model files:
```python
python multi_model.py download-files
```
🏃 Running the Agent

Start the development worker with:
```python
python multi_model.py dev
```
Open the LiveKit Agents Sandbox, join the session, and begin interacting with Echo’s personalized storytelling experience.
