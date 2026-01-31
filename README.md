# LiveKit Intelligent Interruption Handler

This implementation adds intelligent backchannel filtering to LiveKit voice agents. The agent can now distinguish between passive acknowledgements ("yeah", "mhmm", "okay") and actual interruption commands ("stop", "wait", "no").

## Problem Solved

When users provide backchannel feedback while an agent is speaking, the default VAD would interrupt the agent. This created a choppy conversation experience. Now:

- **Agent is speaking + user says "mhmm"** → Agent continues seamlessly
- **Agent is speaking + user says "stop"** → Agent stops immediately  
- **Agent is silent + user says "yeah"** → Agent responds normally

## Quick Start

```bash
# Install dependencies
cd livekit-agents
pip install -e .

# Set up environment variables
export LIVEKIT_URL="wss://your-livekit-server"
export LIVEKIT_API_KEY="your-api-key"
export LIVEKIT_API_SECRET="your-api-secret"
export OPENAI_API_KEY="your-openai-key"
export DEEPGRAM_API_KEY="your-deepgram-key"

# Run the demo agent
cd examples/voice_agents
python interrupt_demo.py dev
```

Then connect via [LiveKit Playground](https://agents-playground.livekit.io/).

## How It Works

### Architecture

```
User Speech → VAD → STT → InterruptionFilter → Agent Response
                              ↓
                    Checks agent state:
                    - Speaking? Filter backchannels
                    - Silent? Allow all input
```

### Key Components

1. **InterruptionFilter** (`livekit/agents/voice/interruption_filter.py`)
   - Core filtering logic with configurable word lists
   - `should_interrupt(transcript, agent_state)` returns True/False

2. **Word Lists** (configurable)
   - `DEFAULT_BACKCHANNEL_WORDS`: yeah, ok, mhmm, uh-huh, right, sure, etc.
   - `DEFAULT_INTERRUPT_WORDS`: stop, wait, no, actually, hold on, etc.

3. **Integration Points**
   - `agent_activity.py`: Captures agent state, applies filter
   - `audio_recognition.py`: Skips EOU detection for filtered utterances

### Configuration

```python
from livekit.agents.voice import InterruptionFilterConfig

# Custom configuration
config = InterruptionFilterConfig(
    backchannel_words={"yeah", "ok", "mhmm"},
    interrupt_words={"stop", "wait"},
    enabled=True
)
```

## Files Changed

| File | Description |
|------|-------------|
| `interruption_filter.py` | NEW - Core filter logic |
| `agent_activity.py` | State tracking and filter integration |
| `audio_recognition.py` | Skip EOU for filtered utterances |
| `agent_session.py` | Configuration options |
| `__init__.py` | Public API exports |

## Testing

```bash
# Run unit tests
cd livekit-agents
python -m pytest tests/test_interruption_filter.py -v
```

## Proof of Functionality

See the `proof/` folder for:
- `transcript.txt` - Annotated conversation transcript
- Screen recording demonstrating the feature

## Key Design Decisions

1. **State Capture Timing**: Agent state is captured when user starts speaking, not when filter runs. This handles race conditions between VAD and STT.

2. **EOU Detection Skip**: When backchannel is filtered, End-of-Utterance detection is also skipped to prevent new response generation.

3. **Flexible Matching**: Hyphenated words like "uh-huh" match "uh-huh", "uh huh", and "uhhuh" to handle STT variations.

4. **Safe Default**: Unknown words while agent is speaking trigger interruption (could be important).
