# Context-Aware Interruption Logic

This implementation refines the conversational flow of the LiveKit agent by filtering passive acknowledgments (backchanneling) to prevent unwanted interruptions.

## Logic Overview

The agent disables default VAD interruptions and uses a custom logic layer to analyze transcripts:

| User Input | Agent State | Action |
|------------|-------------|--------|
| "Yeah / Ok / Hmm" | **Speaking** | **Ignore**: Agent continues speaking seamlessly. |
| "Stop / Wait / No" | **Speaking** | **Interrupt**: Agent stops immediately. |
| "Yeah but wait" | **Speaking** | **Interrupt**: Mixed content acts as a command. |
| Any Input | **Silent** | **Respond**: Standard conversational turn. |

## How to Run

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the agent:
    ```bash
    python examples/voice_agents/basic_agent.py dev
    ```

## Configuration

Behavior can be tuned via environment variables:
*   `BACKCHANNEL_WORDS`: Comma-separated list of words to ignore (default includes "yeah", "ok", "uh-huh").
*   `INTERRUPT_WORDS`: Words that force an immediate stop (default includes "stop", "wait").

## Implementation Details

*   **State Awareness**: The filter is only active when `agent_is_speaking` is true.
*   **Latency Handling**: "Strong" interrupt words are checked against interim results for immediate reaction. Backchannel filtering waits for final transcripts to ensure accuracy.
*   **Edge Cases**: Handles STT artifacts (e.g., "k." for "okay") and normalizes tokens to catch variations like "mm-hmm".