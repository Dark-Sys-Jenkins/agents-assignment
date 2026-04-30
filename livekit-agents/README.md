# LiveKit Agent with Smart Interruption Handling

This project implements a LiveKit voice agent that intelligently handles user interruptions. It uses the OpenAI Realtime API alongside Silero VAD and OpenAI STT to achieve natural, seamless conversational dynamics.

## Features & Evaluation Criteria Addressed

### 1. Strict Functionality (No Hiccups on Filler Words)
The agent features a robust semantic interruption filter. When the user says filler words like "yeah", "ok", or "hmm" while the agent is actively speaking, the agent will **continue speaking without any pauses or hiccups**.
- **How it works:** We disabled server-side turn detection (`turn_detection=None` in RealtimeModel) and implemented a client-side barge-in control. When the STT detects incoming speech during an active agent turn, the text is evaluated against a fuzzy-matching logic. If it matches an "ignored" word, the interruption signal is bypassed, leaving the agent's current audio stream completely unaffected.

### 2. State Awareness (Responding to Short Answers)
The agent correctly differentiates between "filler words during its own speech" and "short valid answers when it is listening".
- **How it works:** The ignore logic only prevents the *cancellation of an active agent speech task*. If the agent has finished speaking and is waiting for a response, saying "yeah" or "ok" is processed as a standard user turn. The VAD and STT capture the utterance, pass it to the LLM as part of the conversation context, and the agent responds accordingly.

### 3. Code Quality (Modular & Configurable)
The logic separating interruptions from filler words is highly modular and easily configurable.
- **How it works:** The word lists are not hardcoded deep in the agent logic. Instead, they are passed as configuration arrays to the `AgentSession` instantiation in `main.py`:
  ```python
  session = AgentSession(
      vad=silero.VAD.load(),
      stt=openai.STT(language="en"),
      llm=openai.realtime.RealtimeModel(voice="alloy", turn_detection=None),
      ignore_interruption_words=["yeah", "ok", "hmm", "mhm", "right", "uh-huh"],
      stop_interruption_words=["wait", "stop", "no"]
  )
  ```
  This makes it trivial to modify the behavior. The arrays can easily be populated from environment variables, a database, or a JSON configuration file without needing to modify the core agent source code.

---

## Getting Started

### Prerequisites
- Python 3.9+
- A LiveKit Cloud project (URL, API Key, API Secret)
- An OpenAI API Key (for Realtime model and STT)

### Setup

1. **Install Dependencies**
   The project uses standard dependency management. Make sure you install the required packages in your virtual environment.

2. **Configure Environment Variables**
   Ensure you have a `.env` file in the root directory (`livekit-agents/.env`) with your keys:
   ```env
   LIVEKIT_URL=wss://<your-project>.livekit.cloud
   LIVEKIT_API_KEY=<your-api-key>
   LIVEKIT_API_SECRET=<your-api-secret>
   OPENAI_API_KEY=<your-openai-key>
   ```

3. **Customizing the Interruption Words (Optional)**
   Open `main.py` and modify the `ignore_interruption_words` or `stop_interruption_words` lists passed to `AgentSession` if you wish to add support for additional filler words or commands.

### Running the Agent
Start the agent worker by running:
```bash
python main.py dev
```

Once the worker is running, it will connect to your LiveKit room and wait for a participant to join. The agent will begin speaking, and you can test the interruption functionality by saying "yeah" (which will be ignored and allow the agent to continue smoothly) or "wait" (which will immediately halt the agent).
