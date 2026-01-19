# Interruption Agent

This repository contains an example LiveKit Agents voice agent that demonstrates "intelligent interruptions": ignoring backchannel/filler words while speaking, but interrupting when the user provides meaningful speech (for example: "hold" or "stop").

## Overview

- Components: Deepgram STT/TTS, Silero VAD, Google Gemini LLM, and the LiveKit Agents framework.
- Behavior: The agent reads a long text and uses a logic layer to ignore backchannels ("yeah", "ok", etc.) while allowing explicit interrupt commands to stop speech.

## Prerequisites

- Python 3.10+
- Install dependencies:

```bash
pip install -r requirements.txt
pip install python-dotenv
```

- Ensure your `.env` contains your keys:

```
LIVEKIT_URL=wss://robox-v9wnrsbv.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
GOOGLE_API_KEY=...
DEEPGRAM_API_KEY=...
```

## Files

- `agent.py` — main agent implementation. It registers an `AgentServer` and an `AgentSession`, and wires event handlers that implement interruption logic.

## How the logic works (current implementation)

- The agent uses a VAD for turn detection, `deepgram.STT()` for transcriptions, and `deepgram.TTS()` for synthesis by default.
- Session settings in `agent.py`:
  - `allow_interruptions=True`
  - `min_interruption_duration=60.0`
  - `min_interruption_words=50`
  - `min_endpointing_delay=0.5`
- Word sets in `agent.py` (customizable):
  - `IGNORE_WORDS`: filler/backchannel words that should never interrupt the agent (e.g., "yeah", "ok").
  - `INTERRUPT_WORDS`: explicit commands that should interrupt (e.g., "stop", "wait").
- Flow:
  1. When a user starts speaking, the code snapshots whether the agent was speaking at the turn start.
  2. When a final transcript arrives (`ev.is_final`), if the transcript is empty nothing happens.
  3. If the agent was speaking at turn start and the transcript is in `IGNORE_WORDS`, the user turn is cleared and ignored.
  4. If the agent was speaking and the transcript contains any `INTERRUPT_WORDS`, `session.interrupt(force=True)` is called to stop the ongoing speech.
  5. Otherwise the transcript is ignored while the agent is speaking.

## Running the agent

Start the agent and connect it to a room (example uses room `test`):

```bash
python agent.py connect --room test --participant-identity agent-test
```

Then join the same room from your client. Example join command you used:

```bash
go run ./cmd/lk token create --join --room test --identity aditya --valid-for 30m --open meet --quiet
```

## Test cases

1. Backchannel ignore
  - While the agent is reading, say: "yeah", "ok", "right".
  - Expected: Agent continues speaking; logs show an "Ignoring backchannel" entry.

2. Manual interruption
  - While the agent is reading, say: "stop" or "wait".
  - Expected: Agent stops speaking immediately and logs an "Active interruption detected" entry.

3. Mixed content
  - Say "yeah stop".
  - Expected: Agent interrupts (because interrupt word present).

4. Post-reading reply suppression
  - If you say only a backchannel when the agent is waiting for input, it should not generate a reply.

## Customization

- To change which words are considered fillers or interrupts, edit the `IGNORE_WORDS` and `INTERRUPT_WORDS` sets in `agent.py`.
- To change interruption sensitivity, adjust the session parameters (`min_interruption_duration`, `min_interruption_words`, `min_endpointing_delay`).

## Troubleshooting

- If the agent is not speaking, check the worker logs to confirm it registered and connected to the room, and ensure your TTS provider is available.
- If interruptions are not detected, confirm the STT provider produces the expected transcripts (look for `received user transcript` in logs). You can also switch to reacting to interim transcripts if you need lower latency.

If you want, I can add an automated test harness to simulate audio input for the cases above.
# LiveKit Intelligent Interruption Handling

This agent implements context-aware interruption logic for LiveKit. It distinguishes between passive "backchanneling" (e.g., "yeah", "uh-huh") and active interruptions (e.g., "stop", "wait").

## The Logic

The core challenge is to prevent the agent from stopping its speech when the user says a filler word, while still allowing immediate interruption for commands.

We achieve this by:
1.  **Disabling Auto-Interruption**: We set `allow_interruptions=False` in the `VoicePipelineAgent`. This prevents the VAD (Voice Activity Detection) from cutting off the audio immediately upon detecting sound.
2.  **Manual Interruption Logic**: We monitor the `user_speech_transcribed` event (interim STT results).
    *   If the agent is speaking AND the text is in the `IGNORE_LIST` (e.g., "yeah"), we do nothing. The audio continues seamlessly.
    *   If the agent is speaking AND the text is meaningful (e.g., "stop", "yeah wait"), we manually call `agent.interrupt()`.
3.  **Response Suppression**: In the `will_synthesize_assistant_reply` callback, if we determine the user input was just a backchannel while the agent was speaking, we cancel the LLM generation (return `False`). This prevents the agent from replying "You said yeah" to a passive listener.

## Setup & Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Create a `.env` file with your keys:
    ```
    LIVEKIT_URL=...
    LIVEKIT_API_KEY=...
    LIVEKIT_API_SECRET=...
    OPENAI_API_KEY=...
    DEEPGRAM_API_KEY=...
    ```

3.  **Run the Agent**:
    ```bash
    python agent.py dev
    ```

## Logic Matrix Behavior

| User Input | Agent State | Behavior | Implementation Detail |
| :--- | :--- | :--- | :--- |
| "Yeah" | Speaking | **IGNORE** | `allow_interruptions=False` keeps audio playing. `will_synthesize` cancels reply. |
| "Stop" | Speaking | **INTERRUPT** | `on_user_speech_transcribed` detects valid text and calls `agent.interrupt()`. |
| "Yeah" | Silent | **RESPOND** | `agent_was_speaking` is False. Logic allows standard LLM processing. |
| "Hello" | Silent | **RESPOND** | Standard behavior. |

## Modularity

*   **Ignored Words**: Configurable via the `IGNORE_WORDS` set in `agent.py`.
*   **Logic Layer**: The interruption decision is isolated in `on_user_speech_transcribed`.