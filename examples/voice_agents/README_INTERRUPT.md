# Intelligent Interruption Handling Agent

This project implements a **context-aware interruption logic layer** for LiveKit agents. It solves the common problem where voice assistants stop speaking when users provide passive feedback (backchanneling) like "yeah", "ok", or "uh-huh".

## 🎯 Features

*   **Intelligent VAD**: Distinguishes between "Passive Acknowledgement" (ignored) and "Active Interruption" (stops speech).
*   **State-Aware**:
    *   **While Speaking**: Ignores filler words (`IGNORE_WORDS` list). Stops only for commands or complex sentences.
    *   **While Silent**: Responds to all input normally (e.g., "Yeah" is treated as an answer).
*   **Configurable**: Easily modify the `IGNORE_WORDS` list in `interruption_logic.py`.
*   **Monkeypatched SDK**: Overrides the default `SpeechHandle.interrupt` to enable granular control over interruption events.

## 📂 File Structure

*   `examples/voice_agents/interrupt_agent.py`: Main entry point. Contains the agent class, monkeypatching, and event loop integration.
*   `examples/voice_agents/interruption_logic.py`: Contains the logic for detecting backchannels and the configurable `IGNORE_WORDS` list.

## 🚀 How to Run

1.  **Install Dependencies**:
    Ensure you have the repository dependencies installed (see root README).

2.  **Set Environment Variables**:
    Create a `.env` file with your LiveKit and OpenAI/Deepgram/Cartesia keys.
    ```env
    LIVEKIT_URL=...
    LIVEKIT_API_KEY=...
    LIVEKIT_API_SECRET=...
    OPENAI_API_KEY=...
    DEEPGRAM_API_KEY=...
    CARTESIA_API_KEY=... (Optional, defaults to OfflineTTS if missing in some setups)
    ```

3.  **Run the Agent**:
    ```bash
    python3 examples/voice_agents/interrupt_agent.py dev
    ```

4.  **Connect**:
    Use the [LiveKit Agents Playground](https://agents-playground.livekit.io/) or a local frontend to connect to the room.

## 🧠 Engineering Approach (Deep Dive)

### The Challenge: "The Backchannel Problem"
Standard Voice Activity Detection (VAD) is binary: it detects **sound** vs. **silence**. It cannot distinguish between a user saying "Stop!" (command) and "Yeah" (listening confirmation). This causes frustrating interruptions where the AI cuts itself off mid-sentence just because the user demonstrated they were listening.

### The Solution: Semantic Filtering Layer
I implemented a **semantic logic layer** that sits between the raw audio events and the agent's control loop. Instead of reacting to *sound*, the agent reacts to *meaning*.

#### 1. Bypassing Default SDK Constraints (Monkeypatching)
The LiveKit SDK is designed to be "safe" — it automatically interrupts speech when it detects user input to prevent talking over the user. To implement custom logic, I had to bypass this safety mechanism.
*   **Technique**: I "monkeypatched" the `SpeechHandle.interrupt` method.
*   **Result**: This allows me to suppress the automatic interruption signal when `allow_interruptions=False`, effectively giving my custom code full control over the decision-making process.

#### 2. The Logic Matrix (State Machine)
The core logic is a state machine that evaluates two inputs: **Current Agent State** (Speaking/Silent) and **User Intent** (Backchannel/Command).

```python
if agent.is_speaking():
    if user_input in ["yeah", "ok", "mm-hmm"]:
        # Case A: Backchannel
        logging.info("Ignoring backchannel")
        continue_speaking() 
    else:
        # Case B: Valid Interruption
        logging.info(f"Command detected: {user_input}")
        agent.stop_speaking()
else:
    # Case C: Standard Conversation
    agent.process_input(user_input)
```

#### 3. Why This Matters
*   **User Experience**: It creates a natural, human-like flow where users can be active listeners without breaking the AI's train of thought.
*   **Latency**: The check is performed on the *transcription text* (STT), which is slightly slower than raw VAD but necessary for semantic understanding. By optimizing the code path, the decision happens in milliseconds after transcription arrives.
*   **Modularity**: The ignore list is decoupled from the core agent, allowing non-engineers to tune the "sensitivity" of the agent by simply updating a list of words.

### Configuration
To change the list of ignored words, edit `IGNORE_WORDS` in `examples/voice_agents/interruption_logic.py`.

```python
IGNORE_WORDS = {
    'yeah', 'ok', 'hmm', 'uh-huh', 'right', 'gotcha', ...
}
```

## 🎥 Proof of Work
[**Watch the Demo Video**](https://drive.google.com/file/d/1rRg5pDK0g3GF9vy0hoZ_Zhaj136E6ykI/view?usp=sharing)
