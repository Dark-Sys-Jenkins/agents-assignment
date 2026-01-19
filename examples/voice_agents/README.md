# LiveKit Voice Agent with Context-Aware Backchannel Detection

A voice agent that intelligently handles user backchannels (like "mhmm", "okay", "uh-huh") while speaking, providing a natural conversational experience.

## Features

- **Zero-pause backchannel handling** - Agent continues speaking when user says acknowledgements
- **Instant interrupt for commands** - Says "stop" or "wait" triggers immediate interruption
- **Multi-word phrase support** - Recognizes phrases like "I see", "got it", "uh huh"

## Quick Start

### 1. Setup Environment

```bash
cd d:\Work\SalesCodeAI\agents-assignment

# Create virtual environment (if not already done)
python -m venv .venv

# Activate
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .\livekit-agents[openai,cartesia,elevenlabs,deepgram,silero,turn-detector]
```

### 2. Configure Environment Variables

Create a `.env` file in root directory:

```env
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
ELEVENLABS_API_KEY=your-elevenlabs-key
```

### 3. Run the Agent

```bash
cd examples/voice_agents
python basic_agent.py dev
```

### 4. Connect to Test

Open the LiveKit Playground at your LiveKit server URL to interact with the agent.

---

## How Backchannel Detection Works

### The Problem

When a user says "mhmm" or "okay" while the agent is speaking, traditional voice agents either:
- Pause and wait (bad UX - noticeable stuttering)
- Interrupt and generate a new response (bad UX - agent responds to acknowledgements)

### The Solution

```
User speaks while agent talking
        ↓
VAD detects voice → Skip pause (agent keeps speaking)
        ↓
STT transcribes in parallel
        ↓
Is it a backchannel? ──Yes──→ Ignore completely
        │
        No / Has "stop", "wait"
        ↓
Interrupt agent immediately
```

**Parallel Processing Approach:** The key insight is that the agent's audio playback and the backchannel detection run as two independent, parallel processes. When the VAD (Voice Activity Detection) detects user speech, instead of immediately pausing the agent, we let the agent continue speaking while the STT (Speech-to-Text) transcribes the user's words in the background. Only once we have the actual transcript do we make a decision: if it's a backchannel word like "mhmm" or "okay", we simply discard it and the agent never knew the user spoke. If it's a real command like "stop" or a genuine question, we interrupt immediately. This separation ensures the agent's speech flow remains completely unaffected by passive acknowledgements, creating a natural conversation experience.

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Backchannel words | `agent_session.py` | Frozenset of 30+ words like "yeah", "mhmm", "okay" |
| VAD bypass | `agent_activity.py` | Skip pause when agent speaking |
| Transcript check | `agent_activity.py` | Classify as backchannel or real input |
| Buffer clearing | `audio_recognition.py` | Prevent backchannel accumulation |

### Backchannel Word List

```python
backchannel_words = frozenset({
    "yeah", "yes", "yep", "yup", "ok", "okay", "aha", "uh-huh",
    "hmm", "mm", "mhm", "mhmm", "right", "sure", "got it", "i see",
    "uh", "um", "understood", "continue", "go on", "really",
    "wow", "nice", "cool", "oh", "ah", "mm-hmm", "mmhmm", "uh huh"
})
```

### Interrupt Commands

Even if text contains backchannel words, these trigger interruption:
```python
interrupt_commands = {"wait", "stop", "hold", "pause", "no", "actually", "but", "however"}
```

---

## Testing

| Say this while agent speaks | Expected behavior |
|----------------------------|-------------------|
| "mhmm" | Agent continues, no pause |
| "okay" | Agent continues, no pause |
| "I see" | Agent continues, no pause |
| "yeah uh-huh" | Agent continues, no pause |
| "stop" | Agent stops immediately |
| "wait a second" | Agent stops immediately |
| "yeah but wait" | Agent stops (contains "wait") |

---

## Troubleshooting

### Agent pauses on backchannels
- Check if the word is in `backchannel_words` in `agent_session.py`
- Check logs for `"backchannel ignored on final"` message

### Import errors with opentelemetry
- Ensure `opentelemetry-sdk<1.39` in `pyproject.toml`
- Reinstall: `pip install -e .\livekit-agents[...]`

### Logs show backchannels accumulating
- Verify `audio_recognition.py` clears `_audio_transcript` after all `on_end_of_turn` calls

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AgentSession                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │                  AgentActivity                   │    │
│  │                                                  │    │
│  │  on_vad_inference_done() ──→ Skip pause if      │    │
│  │                              agent speaking      │    │
│  │                                                  │    │
│  │  on_interim_transcript() ──→ Check backchannel  │    │
│  │  on_final_transcript()   ──→ Check backchannel  │    │
│  │  on_end_of_turn()        ──→ Block LLM response │    │
│  │                                                  │    │
│  │  _is_backchannel_text()  ──→ Word matching      │    │
│  │  _contains_interrupt_cmd() ──→ Command check    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │              AudioRecognition                    │    │
│  │                                                  │    │
│  │  _audio_transcript ──→ Cleared after each turn  │    │
│  │                        (prevents accumulation)   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## License

See repository root for license information.
