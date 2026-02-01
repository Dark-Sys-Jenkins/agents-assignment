# Intelligent Interruption Handling Assignment

This repository contains the implementation for the "Intelligent Interruption Handling" challenge.

## Overview

We have implemented a logic layer that makes the agent context-aware, distinguishing between passive backchanneling and active interruptions. This ensures the agent does not stop speaking when the user provides "soft" inputs like "yeah" or "ok".

## Features

1.  **Configurable Ignore List**: A defined list of words acts as "soft" inputs that do not trigger an interruption.
    -   *Default Words*: "yeah", "ok", "okay", "hmm", "hm", "right", "sure", "uh-huh".
    -   **Configurable**: You can change this list by setting the `LIVEKIT_IGNORE_WORDS` environment variable (comma-separated).
2.  **State-Based Filtering**: The ignore logic **only** applies when the agent is actively speaking (`_current_speech` is active).
3.  **Semantic Interruption**: Mixed sentences containing ignored words along with other content (e.g., "Yeah wait a second") correctly trigger an interruption.
4.  **No VAD Modification**: The solution is implemented as a logic handling layer within the agent's event loop, without altering the low-level VAD kernel.

## Technical Implementation

-   **File**: `examples/voice_agents/intelligent_agent.py`
-   **Mechanism**: Monkey patching `AgentActivity._interrupt_by_audio_activity` and `AgentActivity.on_end_of_turn` to intercept and evaluate user input against the ignore list before deciding to interrupt.
-   **Modularity**: The ignore list is loaded from an environment variable, making it easily configurable without code changes.

## How to Run

1.  **Prerequisites**: Ensure you have the `.env` file with LiveKit and OpenAI/Deepgram/Cartesia credentials in the root directory.

2.  **Install Dependencies**:
    ```bash
    pip install -r examples/voice_agents/requirements.txt
    ```

3.  **Run the Agent**:
    ```bash
    python examples/voice_agents/intelligent_agent.py console
    ```

### Configuration

To customize the ignore list, set the `LIVEKIT_IGNORE_WORDS` environment variable before running:

**Windows (PowerShell)**:
```powershell
$env:LIVEKIT_IGNORE_WORDS="yes,correct,indeed"
python examples/voice_agents/intelligent_agent.py console
```

## Testing & Verification

The agent has been tested for the following scenarios and meets all requirements:

| Scenario | User Action | Expected Behavior | Result |
| :--- | :--- | :--- | :--- |
| **Ignore** | User says "Yeah" while agent speaks | Agent **continues** speaking | ✅ Passed |
| **Interrupt** | User says "Stop" while agent speaks | Agent **stops** immediately | ✅ Passed |
| **Response** | User says "Yeah" while agent is silent | Agent **responds** (e.g. "Great") | ✅ Passed |
| **Mixed Input** | User says "Yeah wait" | Agent **stops** (Semantic Interruption) | ✅ Passed |

verification logs confirm that "Ignoring interruption: 'yeah' matches ignore list" appears in the console during successful ignore events.
