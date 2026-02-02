# Intelligent Interruption Handling Agent

## Overview
This agent implements smart interruption logic using LiveKit Agents. It solves the "VAD Sensitivity" problem by filtering user speech before stopping the agent.

## Logic Implementation
The agent listens to the `user_speech_committed` event and applies the following decision matrix:
1.  **Passive Backchanneling:** If the user says words like *"yeah", "uh-huh", "ok"* (defined in `IGNORE_WORDS`), the agent **ignores** them and continues speaking.
2.  **Active Interruption:** If the user says command words like *"stop", "wait"* (defined in `INTERRUPT_WORDS`), the agent **interrupts** immediately.
3.  **New Input:** Any other sentence triggers a standard interruption.

## How to Run
1.  **Install Dependencies:**
    ```bash
    pip install livekit-agents livekit-plugins-openai livekit-plugins-silero python-dotenv
    ```
2.  **Set Environment Variables:**
    Create a `.env` file with `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `OPENAI_API_KEY`.
3.  **Run the Agent:**
    ```bash
    python examples/smart_agent.py dev
    ```

## Python Version
This project uses **Python 3.12** (via a virtual environment) to ensure compatibility with `livekit-agents` v0.8+.