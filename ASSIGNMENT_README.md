# Intelligent Interruption Agent - Assignment Submission

## Overview
This project implements an intelligent voice agent designed to handle interruptions elegantly. The core objective is to distinguish between **"Passive Acknowledgements"** (backchanneling) and **"Active Interruptions"** (commands/questions).

### The Problem
Default Voice Activity Detection (VAD) is often too sensitive, causing agents to stop speaking if the user simply says "yeah" or "ok" to indicate they are listening.

### The Solution: Logic Handling Layer
This agent uses a custom logic layer within the LiveKit Agent framework:
1.  **Strict Continuity**: By setting `allow_interruptions=False`, we prevent the VAD from cutting off the agent audio prematurely. This eliminates pauses, stutters, or hiccups on filler words.
2.  **State-Aware Filtering**: The interruption logic only triggers when the agent is actively speaking. If the agent is silent, all inputs are processed normally.
3.  **Configurable Ignore List**: A list of "soft" words (e.g., `yeah`, `ok`, `hmm`) is used to filter out passive feedback.
4.  **Semantic Interruption**: The system analyzes the full transcript. If a "hard" word (e.g., `wait`, `stop`, `no`) is detected—even if mixed with soft words—it triggers a `force=True` interruption.

---

## Technical Details
- **Framework**: LiveKit Agents (Python)
- **STT**: Deepgram
- **TTS**: Deepgram
- **LLM**: Meta-Llama 3.1 8B (via OpenRouter)
- **VAD**: Silero

---

## How to Run

1.  **Install Dependencies**:
    Make sure you are in the project root and your virtual environment is active.
    ```powershell
    pip install -r examples/voice_agents/requirements.txt
    pip install livekit-plugins-openai livekit-plugins-deepgram livekit-plugins-silero python-dotenv
    ```

2.  **Configure Environment**:
    Create a `.env` file in the root directory with the following keys:
    ```env
    LIVEKIT_URL=<your-livekit-url>
    LIVEKIT_API_KEY=<your-api-key>
    LIVEKIT_API_SECRET=<your-api-secret>
    DEEPGRAM_API_KEY=<your-deepgram-key>
    OPENROUTER_API_KEY=<your-openrouter-key>
    ```

3.  **Execute the Agent**:
    ```powershell
    python examples/voice_agents/intelligent_agent.py dev
    ```

4.  **Test the Scenarios**:
    Open the [LiveKit Agents Playground](https://agents-playground.livekit.io/), connect to your room, and try the following:
    - **Scenario 1**: While the agent is explaining history, say *"Yeah... ok... hmm"*. The agent will **not** stop.
    - **Scenario 2**: When the agent finishes, say *"Yeah"*. The agent will respond naturally (e.g., *"Great, let's continue"*).
    - **Scenario 3**: While the agent is speaking, say *"Stop"* or *"Wait a second"*. The agent will cut off **immediately**.
    - **Scenario 4 (Mixed)**: Say *"Yeah ok but wait"*. The agent will stop because *"wait"* is not in the ignore list.

---

## Evaluation Criteria Mapping
- **Strict Functionality (70%)**: Implemented via `allow_interruptions=False` and manual `session.interrupt(force=True)`.
- **State Awareness (10%)**: Managed by checking `session.agent_state == "speaking"` in the transcription listener.
- **Code Quality (10%)**: Logic is modularized into the `should_interrupt` function and a clean event listener.
- **Documentation (10%)**: Provided in this README.
