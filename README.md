GitHub README: Echo Multi-Modal Voice Agent
This README is designed to showcase your sophisticated multi-agent implementation, highlighting the transition logic and custom interruption handling you've built.

Markdown
# 🎭 Echo: Multi-Agent Storytelling Voice Assistant

Echo is a sophisticated, real-time voice agent built using the **LiveKit Agents SDK**. It features a state-managed, multi-agent architecture that transitions from a data-gathering "Intro" phase to a personalized "Storytelling" phase, utilizing a cutting-edge multimodal stack.

## 🚀 Key Features

- **Multi-Agent Handoff:** Uses a state machine logic to transition from `IntroAgent` (Data Collection) to `StoryAgent` (Creative Generation) seamlessly.
- **Intelligent Turn-Detection:** - **Filler Word Filtering:** Ignores backchanneling like "yeah" and "ok" to maintain flow.
    - **Hard Command Recognition:** Immediately respects commands like "STOP" or "PAUSE" using a custom transcript listener.
- **Dynamic Context:** Captures user name and location to generate unique, personalized narratives on the fly.
- **Automated Lifecycle:** Automatically cleans up resources and deletes the LiveKit room upon session completion.

## 🛠️ Technical Architecture

| Component | Technology |
| :--- | :--- |
| **Orchestration** | LiveKit Agents SDK (Python) |
| **STT** | Deepgram (Model: Nova-3) |
| **LLM** | Google Gemini 2.0 Flash |
| **TTS** | ElevenLabs (Model: Flash v2.5) |
| **VAD** | Silero (Local Inference) |


## 📋 Prerequisites

- Python 3.11+
- [LiveKit Cloud](https://cloud.livekit.io) account and project.
- API Keys for: Deepgram, ElevenLabs, and Google (Gemini).

## ⚙️ Setup & Installation

1. Copy the code from examples/voice_agents/multi_agent.py

   
Install dependencies:

pip install livekit-agents livekit-plugins-deepgram livekit-plugins-elevenlabs livekit-plugins-silero livekit-plugins-google python-dotenv


Configure Environment Variables: Create a .env file in the project root:

->LIVEKIT_URL=wss://your-project.livekit.cloud

->LIVEKIT_API_KEY=your_livekit_key

->LIVEKIT_API_SECRET=your_livekit_secret

->DEEPGRAM_API_KEY=your_deepgram_key

->ELEVEN_API_KEY=your_eleven_key

->GOOGLE_API_KEY=your_gemini_key

Initialize Models:

->python multi_model.py download-files

🏃 Running the Project

Start the agent worker with:

->python multi_model.py dev

Join the session via the LiveKit Agents Sandbox to begin the experience.
