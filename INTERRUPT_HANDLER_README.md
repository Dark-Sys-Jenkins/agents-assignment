# LiveKit Intelligent Interruption Handling

## Overview

This implementation adds **context-aware backchannel detection** to the LiveKit Agents framework. The agent can now distinguish between passive acknowledgements ("yeah", "ok", "hmm") and active interruptions ("stop", "wait", "no") based on whether the agent is currently speaking or silent.

### The Problem

LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. When the agent is explaining something and the user says "yeah" or "ok" to indicate they are listening, the agent interprets this as an interruption and abruptly stops speaking.

### The Solution

A **logic filtering layer** sits between the VAD/STT pipeline and the interruption engine. It validates the transcript content before allowing an interruption, without modifying the low-level VAD kernel.

## How It Works

### Logic Matrix

| User Input | Agent State | Behavior |
|---|---|---|
| "Yeah / Ok / Hmm" | **Speaking** | **IGNORE** - Agent continues speaking seamlessly |
| "Wait / Stop / No" | **Speaking** | **INTERRUPT** - Agent stops immediately |
| "Yeah / Ok / Hmm" | **Silent** | **RESPOND** - Agent treats it as valid input |
| "Yeah okay but wait" | **Speaking** | **INTERRUPT** - Contains non-backchannel word "wait" |

### Architecture

```
User speaks → [VAD] detects speech (fast, ~20ms)
                ↓
            Agent speaking + backchannel filter enabled?
            YES → Skip VAD-only interruption, wait for STT
                    ↓
              [STT] returns transcript (~200-500ms)
                    ↓
              All words are backchannel? → YES → IGNORE (no pause, no stutter)
                                        → NO  → INTERRUPT immediately
            NO → Normal interruption behavior
```

**Key design decision**: When backchannel filtering is active and the agent is speaking, VAD events alone do NOT trigger interruptions. The system waits for STT to deliver the actual transcript, then makes an informed decision. This prevents the "false start" problem where VAD would pause the agent before STT realizes the user only said "yeah".

### Files Modified

| File | Change |
|---|---|
| `livekit-agents/livekit/agents/voice/backchannel.py` | **NEW** - Backchannel detection module with configurable word list |
| `livekit-agents/livekit/agents/voice/agent_activity.py` | Added `_is_agent_speaking()`, `_should_ignore_as_backchannel()`, modified `_interrupt_by_audio_activity()`, `on_vad_inference_done()`, `on_interim_transcript()`, `on_final_transcript()` |
| `livekit-agents/livekit/agents/voice/agent_session.py` | Added `backchannel_words` parameter to `AgentSessionOptions` and `AgentSession.__init__()` |
| `livekit-agents/livekit/agents/telemetry/traces.py` | Fixed opentelemetry SDK compatibility |
| `interrupt_agent.py` | **NEW** - Demo agent with backchannel filtering enabled |
| `requirements.txt` | Updated with all required dependencies |

### Backchannel Module (`backchannel.py`)

The `is_backchannel()` function checks if **every** word in the transcript is a backchannel word:

- `"yeah ok hmm"` → all backchannel → returns `True` → ignored while speaking
- `"yeah okay but wait"` → "but" and "wait" are NOT backchannel → returns `False` → triggers interruption
- Multi-word phrases like "got it", "i see", "uh huh" are supported

The `DEFAULT_BACKCHANNEL_WORDS` set includes: yeah, yep, yup, yes, ok, okay, hmm, hm, mhm, mm, uh-huh, uh huh, uhuh, ah, aha, right, sure, got it, i see, alright, cool.

### Configurable Ignore List

The word list is fully configurable via the `backchannel_words` parameter:

```python
from livekit.agents.voice.backchannel import DEFAULT_BACKCHANNEL_WORDS

# Use defaults
session = AgentSession(backchannel_words=DEFAULT_BACKCHANNEL_WORDS)

# Extend with custom words
custom_words = DEFAULT_BACKCHANNEL_WORDS | frozenset({"gotcha", "yea", "ya"})
session = AgentSession(backchannel_words=custom_words)

# Disable backchannel filtering entirely
session = AgentSession(backchannel_words=None)
```

## Setup

### Prerequisites

- Python 3.10+
- API keys for STT, LLM, and TTS providers

### Installation

```bash
git clone https://github.com/<your-username>/agents-assignment.git
cd agents-assignment
git checkout feature/interrupt-handler-krish

# Install from local repo (required for backchannel changes)
pip install -e livekit-agents
pip install -e livekit-plugins/livekit-plugins-silero
pip install -e livekit-plugins/livekit-plugins-deepgram
pip install -e livekit-plugins/livekit-plugins-openai
pip install -e livekit-plugins/livekit-plugins-groq
pip install -e livekit-plugins/livekit-plugins-cartesia
pip install python-dotenv
```

### Environment Variables

Create a `.env` file in the project root:

```env
# At minimum, you need one LLM provider (OpenAI or Groq)
OPENAI_API_KEY="sk-..."       # Primary LLM (optional)
GROQ_API_KEY="gsk_..."        # Fallback LLM (if no OpenAI key)

# STT
DEEPGRAM_API_KEY="..."        # Speech-to-Text

# TTS
CARTESIA_API_KEY="sk_car_..." # Text-to-Speech

# LiveKit (required for dev mode, not needed for console mode)
LIVEKIT_URL="wss://your-project.livekit.cloud"
LIVEKIT_API_KEY="API..."
LIVEKIT_API_SECRET="..."
```

The agent auto-selects providers based on available keys:
- **LLM**: OpenAI (primary) → Groq (fallback)
- **STT**: Deepgram (primary) → OpenAI → Groq
- **TTS**: Cartesia (primary) → OpenAI → Groq

## Running the Agent

### Console Mode (local microphone, no LiveKit server needed)

```bash
python interrupt_agent.py console
```

### Dev Mode (connects to LiveKit Cloud, test via browser)

```bash
python interrupt_agent.py dev
```

Then open [agents-playground.livekit.io](https://agents-playground.livekit.io) and connect.

## Testing

### Test Scenarios

**Scenario 1 - The Long Explanation**:
Let the agent talk for a while. Say "okay... yeah... uh-huh" while it speaks. The agent should NOT stop, pause, or stutter.

**Scenario 2 - The Passive Affirmation**:
Wait for the agent to finish and go silent. Say "Yeah." The agent should respond (e.g., "Great, how can I help?").

**Scenario 3 - The Correction**:
While the agent is speaking, say "No, stop." The agent should cut off immediately.

**Scenario 4 - The Mixed Input**:
While the agent is speaking, say "Yeah okay but wait." The agent should stop because "but wait" is not a backchannel word.

### Capturing Logs for Proof

```bash
# PowerShell
python interrupt_agent.py dev 2>&1 | Tee-Object -FilePath test_log.txt

# Bash / Git Bash
python interrupt_agent.py dev 2>&1 | tee test_log.txt
```

Look for log lines like:
```
backchannel detected while agent speaking, ignoring {"transcript": "yeah"}
backchannel in final transcript, ignoring interruption {"transcript": "ok"}
```

These confirm the agent is correctly filtering backchannel words.

## Design Decisions

1. **No VAD modification**: All filtering is done as a logic layer in `agent_activity.py`. The Silero VAD kernel is untouched.

2. **VAD deferral to STT**: When backchannel filtering is enabled and the agent is speaking, VAD events alone do NOT trigger interruption. This prevents the agent from pausing before STT can determine what was said.

3. **Zero-latency filtering**: The `is_backchannel()` function is a pure string operation (set lookups) running in microseconds. No network calls or model inference.

4. **Backwards compatible**: Setting `backchannel_words=None` (the default) preserves the original behavior entirely. Existing agents are unaffected.
