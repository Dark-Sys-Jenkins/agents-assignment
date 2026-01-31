# LiveKit Intelligent Interruption Agent

**Assignment Submission:** LiveKit Intelligent Interruption Handling Challenge for Salescode.ai Gen AI Role Summer Internship Assignment by Aditya Chaudhary(22DCS002).

🎥 **Demo Video:** [Watch the implementation and testing here](https://drive.google.com/file/d/1RluhAnQrEIBEWPVTCy06n_HR5zcuob2E/view?usp=sharing)

This challenge's solution implements an intelligent interruption handling system for LiveKit Voice Agents. It differentiates between "backchannel" words (like "yeah", "ok") and actual interruptions, ensuring a seamless and natural conversation flow. The goal is to make the agent feel more human by allowing the user to affirm listener engagement without stopping the agent's speech, while still stopping immediately for commands or substantial input.

## 🚀 Key Features

*   **Smart Backchannel Filtering:** The agent continues speaking over user backchannels (e.g., "uh-huh", "right", "yeah") without pausing, stuttering, or hiccuping.
*   **State-Aware Logic:** The filtering logic is context-sensitive. "Backchannel" words are treated as valid responses when the agent is silent (e.g., answering "Yes" to a question) and are only ignored when the agent is actively speaking.
*   **Semantic Interruptions:** The system handles mixed sentences intelligently. A phrase like "Yeah wait a second" correctly triggers an interruption because it contains an intent word ("wait"), effectively prioritizing semantic meaning over simple word lists.
*   **Zero-Latency / "False Start" Handling:** Implements a "Deferred Interruption" strategy. The low-level VAD (Voice Activity Detection) signal alone does not trigger an interruption when STT is active. Instead, the agent waits for the first interim transcript to determine if the speech is a backchannel to be ignored or a valid interruption.
*   **Fully Configurable:** Intent words and backchannel words are managed via a simple `config.yaml` file, allowing for easy tuning without code changes.

## 🛠️ Configuration

The agent's behavior is configured using the `config.yaml` file in the root directory. This allows for persistent configuration of interruption sensitivity.

### Using `config.yaml`
Edit the `config.yaml` file in the root of your workspace:

```yaml
intent_words:
  - stop
  - wait
  - pause
  # ... (add words that force immediate interruption)

backchannel_words:
  - okay
  - ok
  - uhhuh  # handles "uh-huh" (punctuation stripped)
  - uh-huh
  # ... (add words that should be ignored while speaking)
```

## 🧠 Logic Overview & Implementation Details

The core logic is implemented in the **application logic layer** within `livekit-agents/livekit/agents/voice/agent_activity.py` (the `AgentActivity` class), with helper utilities in `_utils.py`.

** Compliance Note:** As per assignment requirements, we **do not** modify the low-level VAD kernel. Instead, we implement a smart handling layer within the agent's existing event loop to process VAD and STT events intelligently.

### 1. Logic Handling Layer (VAD Event Strategy)
To satisfy the "Zero Pause" requirement, we adjusted the `on_vad_inference_done` event handler in the agent's logic loop.
*   **Standard Behavior:** VAD event triggers -> Agent pauses immediately -> STT processes text.
*   **Our Logic:** VAD event triggers -> Agent **keeps speaking** (ignores signal at kernel level) -> STT processes text -> Application Layer (`on_interim_transcript`) decides whether to interrupt.
This ensures that if the user just says "Yeah", the audio stream is never cut, avoiding the jarring "hiccup" effect.

### 2. State-Based Filtering Algorithm
The interruption decision happens inside `on_interim_transcript` and `on_final_transcript`:

1.  **State Check:** We first check `if self._current_speech is not None`.
    *   If **Speech is None** (Agent is silent): All input is processed as a valid user turn.
    *   If **Speech is Active** (Agent is speaking): We enter the filtering logic.

2.  **Token-Based Intent Analysis:**
    *   The transcript is split into tokens. We check if **ANY** intent word (from `config.yaml`) exists in the sentence.
    *   *Example:* "Yeah hold on" -> Contains "hold" -> **INTERRUPT**.
    *   This check bypasses minimum word count constraints, ensuring commands like "Stop" work instantly.

3.  **Backchannel Validation:**
    *   If no intent words are found, we check if **ALL** words in the transcript are in the configured backchannel list.
    *   *Example:* "Yeah okay sure" -> All are backchannels -> **IGNORE** (Agent continues speaking).
    *   *Example:* "Yeah help" -> "help" is not a backchannel -> **INTERRUPT**.

### 3. Files Modified
*   `livekit-agents/livekit/agents/voice/agent_activity.py`:
    *   Imports and uses logic from `_utils.py`.
    *   Updated `on_interim_transcript`, `on_final_transcript`, `on_end_of_turn`, and `on_vad_inference_done`.
*   `livekit-agents/livekit/agents/voice/_utils.py`:
    *   Contains configuration loading (`config.yaml` support).
    *   Contains helper functions (`_load_config_words`, `_is_only_backchannels`).

## 🏃‍♂️ How to Run

1.  **Environment Setup:**
    *   Navigate to the `examples/voice_agents` directory (or wherever your target agent is located).
    *   Create a `.env` file (or rename `.env.example`).
    *   Add your API keys:
        *   `LIVEKIT_URL`
        *   `LIVEKIT_API_KEY`
        *   `LIVEKIT_API_SECRET`

2.  **Run the Test Agent:**
    You can run the basic agent in dev mode to test the functionality.
    ```bash
    python examples/voice_agents/basic_agent.py dev
    ```
    *Or run in console mode for text-based debugging:*
    ```bash
    python examples/voice_agents/basic_agent.py console
    ```

3.  **Testing the Logic:**
    *   *Scenario 1:* While the agent is speaking long text, say "Yeah", "Uh-huh". -> Agent should **continue** speaking.
    *   *Scenario 2:* While the agent is speaking, say "Stop" or "Wait". -> Agent should **interrupt** immediately.
    *   *Scenario 3:* While the agent is speaking, say "Yeah wait I have a question". -> Agent should **interrupt**.
    *   *Scenario 4:* When the agent is silent, say "Yeah". -> Agent should **respond** to you.
