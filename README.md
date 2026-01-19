# SalesCode.ai Voice Agent (Context-Aware)

This project implements a real-time AI Voice Agent for SalesCode.ai using the LiveKit Agents framework. It features an advanced **Intelligent Interruption System** that distinguishes between passive listening signals (backchanneling) and active interruptions.

## 🚀 Features

* **Smart Backchannel Filtering:** The agent intelligently ignores filler words like "yeah", "uh-huh", or "okay" while speaking, ensuring a smooth, uninterrupted sales pitch.
* **Semantic Interruption:** If the user issues a command ("Stop", "Wait") or asks a question, the agent immediately stops speaking and responds.
* **State-Awareness:** The agent tracks its own speaking state. If it is silent, it treats "Yeah" as a valid confirmation (Passive Affirmation).
* **Optimized Latency:** Utilizes **Groq (Llama 3.3)** for near-instant inference and **Deepgram** for high-speed STT/TTS.

## 🛠️ Technical Implementation

### The "Deferred Interruption" Strategy
To solve the problem of the agent cutting off too sensitively, I implemented a custom logic layer in `agent.py`:

1.  **VAD Override:** The default `on_user_started_speaking` event is overridden to `pass`. This prevents the Voice Activity Detector from blindly cutting the audio stream the moment sound is detected.
2.  **Transcript Analysis:** Interruption logic is deferred to the `on_user_transcript` event.
    * **IF** Agent is Speaking **AND** Input is in `IGNORE_WORDS`: -> **Drop the message.** (Audio continues seamlessly).
    * **IF** Agent is Speaking **AND** Input is active text: -> **Pass to LLM.** (Agent stops and replies).
    * **IF** Agent is Silent: -> **Pass to LLM.** (Normal conversation).

### Tech Stack
* **Framework:** LiveKit Agents (Python)
* **LLM:** Groq (`llama-3.3-70b-versatile`)
* **STT/TTS:** Deepgram
* **VAD:** Silero

## 🏃‍♂️ How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment:**
    Create a `.env` file with your keys:
    ```env
    LIVEKIT_URL=...
    LIVEKIT_API_KEY=...
    LIVEKIT_API_SECRET=...
    GROQ_API_KEY=...
    DEEPGRAM_API_KEY=...
    ```

3.  **Run the Agent:**
    ```bash
    python3 agent.py dev
    ```

4.  **Connect:**
    Open the [LiveKit Playground](https://agents-playground.livekit.io/), connect to your instance, and start the conversation.
