# 🧠 Intelligent Interruption Handler (LiveKit Agent)

**Submitted by:** Noor
**Course:** Agents Assignment

## 👋 Overview
This submission solves the "Interrupt vs. Backchannel" problem in Voice AI.
Standard agents stop talking whenever they hear a sound. This agent is context-aware:
* **Ignores Backchanneling:** If you say "Yeah", "Uh-huh", or "Okay" while the agent is speaking, it **continues** seamlessly.
* **Respects Commands:** If you say "Stop" or "Wait", it **stops** immediately.
* **Conversational Awareness:** If the agent is silent, it treats "Yeah" as a valid response.

---

## 🚀 How to Run It

### Install Dependencies
```bash
pip install -r requirements.txt

### Set Up Environment
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
GROQ_API_KEY=...
DEEPGRAM_API_KEY=...


### Run the Agent
python basic_agent.py dev

### Video Link :
https://drive.google.com/file/d/126Q2jviMTf10WxzFSNnwovy3QC69cViN/view?usp=sharing