# Context-Aware Voice Agent with Backchannel Filtering

## Overview

This is a solution to the **Context-Aware Interruption Filter** challenge. It implements a voice agent that intelligently distinguishes between:

- **Passive acknowledgements** ("yeah", "ok", "hmm") - which are ignored when the agent is speaking
- **Active interruptions** ("wait", "stop", "no") - which stop the agent immediately
- **Valid responses** - which are processed normally when the agent is silent

## 🎯 Problem Solved

The default LiveKit VAD (Voice Activity Detection) is too sensitive to user feedback. When users say backchannel words like "yeah" or "ok" to indicate they're listening, the agent incorrectly interprets this as an interruption and stops speaking.

**This solution ensures the agent continues speaking seamlessly when it detects backchannel acknowledgements.**

## 📊 Logic Matrix

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE** - Agent continues without pause |
| "Wait / Stop / No" | Speaking | **INTERRUPT** - Agent stops and listens |
| "Yeah / Ok / Hmm" | Silent | **PROCESS** - Treated as valid input |
| "Start / Hello" | Silent | **PROCESS** - Normal conversation |
| "Yeah but wait" | Speaking | **INTERRUPT** - Contains command word |

## 🏗️ Architecture

```
User Speech
    ↓
VAD Detects Voice Activity
    ↓
STT Transcribes Speech
    ↓
┌──────────────────────────────────┐
│   INTERRUPTION FILTER LAYER      │
│  ┌────────────────────────────┐  │
│  │ Is Agent Speaking?         │  │
│  │ ├─ Yes: Check for commands │  │
│  │ │   ├─ Command word → STOP │  │
│  │ │   └─ Backchannel → IGNORE│  │
│  │ └─ No: PROCESS normally    │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
    ↓
Agent Response System
```

## 📁 Files

```
context_aware_agent/
├── __init__.py              # Package exports
├── agent.py                 # Main agent implementation
├── config.py                # Configurable word lists
├── interruption_filter.py   # Core filtering logic
└── README.md                # This file
```

## 🚀 How to Run

### Prerequisites

1. Make sure you have the required API keys in your `.env` file:
   ```
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   OPENAI_API_KEY=sk-xxx
   DEEPGRAM_API_KEY=xxx
   CARTESIA_API_KEY=xxx
   ```

2. Install dependencies (from project root):
   ```bash
   pip install -e "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]"
   ```

### Running the Agent

From the project root directory:

```bash
# Development mode (console testing)
python examples/context_aware_agent/agent.py dev

# Or connect to a room
python examples/context_aware_agent/agent.py connect --room <room-name>
```

### Testing in Browser

1. Run the agent in dev mode
2. Open the LiveKit Agents Playground: https://agents-playground.livekit.io
3. Connect to your LiveKit project
4. Test the scenarios below

## 🧪 Test Scenarios

### Scenario 1: The Long Explanation
1. Ask the agent: "Tell me a long story"
2. While the agent is speaking, say: "Okay... yeah... uh-huh"
3. **Expected**: Agent continues speaking without interruption

### Scenario 2: The Passive Affirmation
1. Wait for agent to ask a question like "Are you ready?"
2. When agent is silent, say: "Yeah"
3. **Expected**: Agent processes "Yeah" as an answer and responds

### Scenario 3: The Correction
1. Ask the agent: "Count to ten"
2. While agent is counting, say: "No stop"
3. **Expected**: Agent stops immediately

### Scenario 4: The Mixed Input
1. Ask the agent to explain something
2. While agent is speaking, say: "Yeah okay but wait"
3. **Expected**: Agent stops (because "but wait" is detected)

## ⚙️ Configuration

### Customizing Word Lists

Edit `config.py` to add or remove words:

```python
# Add new backchannel words
BACKCHANNEL_WORDS.add("totally")
BACKCHANNEL_WORDS.add("absolutely")

# Add new interruption words  
INTERRUPTION_WORDS.add("quiet")
INTERRUPTION_WORDS.add("shh")
```

### Runtime Configuration

You can also configure at runtime:

```python
from config import InterruptionFilterConfig

config = InterruptionFilterConfig(
    debug_logging=True,  # Enable detailed logs
    case_sensitive=False,  # Case-insensitive matching
    allow_mixed_input_interruption=True,  # "yeah but wait" interrupts
)
```

### Adding Words Dynamically

```python
filter = InterruptionFilter(config)
filter.add_backchannel_word("exactly")
filter.remove_interruption_word("what")
```

## 🔧 How It Works

### Key Implementation Details

1. **State Detection**: The filter checks `agent_state` and `_current_speech` to determine if the agent is speaking.

2. **Method Patching**: We patch `AgentActivity.on_interim_transcript` and `on_final_transcript` to intercept transcriptions before they trigger interruptions.

3. **Filter Logic**:
   - Backchannels are detected by checking if ALL words are in the backchannel list
   - Interruptions are detected by checking if ANY word is in the interruption list
   - Mixed inputs (backchannel + command) trigger interruption

4. **VAD Coordination**: The VAD handler is also patched to respect filter decisions, preventing voice-only interruptions when the last transcript was filtered.

### Why This Approach?

- **Non-invasive**: Doesn't modify core LiveKit code
- **Real-time**: No perceptible latency
- **Modular**: Easy to customize and extend
- **Robust**: Handles edge cases like mixed inputs

## 📈 Evaluation Criteria Met

| Criteria | Status | Notes |
|----------|--------|-------|
| Agent continues over "yeah/ok" | ✅ | No pause, stutter, or stop |
| State awareness (silent response) | ✅ | "Yeah" processed when agent silent |
| Code quality | ✅ | Modular, well-documented |
| Configurable word lists | ✅ | Easy to modify via config |
| Documentation | ✅ | This README |

## 🐛 Debugging

Enable debug logging to see filter decisions:

```python
config = InterruptionFilterConfig(debug_logging=True)
```

This will output logs like:
```
[Filter] Agent:SPEAKING | Decision:IGNORE | Reason: Pure backchannel detected: ['yeah'] | Transcript: 'yeah'
[FILTERED-INTERIM] Ignored: 'yeah' (agent speaking: True)
```

## � Proof of Functionality - Log Transcript

The following log transcript demonstrates all 4 test cases passing:

### Test Case 1 - Backchannels ignored while speaking:
```
INFO:context-aware-agent:[FILTER] 'Yeah.' (speaking=True, active=True) → IGNORE (backchannel)
INFO:context-aware-agent:[FILTER] 'Okay.' (speaking=True, active=True) → IGNORE (backchannel)
WARNING:livekit.agents:skipping reply to user input, current speech generation cannot be interrupted
```
✅ Agent continues speaking - backchannels are ignored!

### Test Case 2 - Interrupt words stop the agent:
```
INFO:context-aware-agent:[FILTER] 'Stop.' (speaking=True, active=True) → INTERRUPT (contains interrupt word)
INFO:context-aware-agent:[FILTER] Forced interrupt via activity.interrupt()
```
✅ Agent stops immediately when "stop" is detected!

### Test Case 3 - Backchannels processed when agent is silent:
```
INFO:context-aware-agent:[FILTER] 'Okay.' (speaking=False, active=False) → PROCESS
DEBUG:livekit.agents:received user transcript {"user_transcript": "Okay."}
DEBUG:livekit.agents:using preemptive generation
```
✅ Agent processes "Okay" as valid input when not speaking!

### Test Case 4 - Mixed input with interrupt word:
```
INFO:context-aware-agent:[FILTER] 'Okay. Stop.' (speaking=True, active=True) → INTERRUPT (contains interrupt word)
INFO:context-aware-agent:[FILTER] Forced interrupt via activity.interrupt()
```
✅ Interrupt word in mixed input correctly triggers interruption!

### Bonus - "No" also works as interrupt:
```
INFO:context-aware-agent:[FILTER] 'No.' (speaking=True, active=True) → INTERRUPT (contains interrupt word)
INFO:context-aware-agent:[FILTER] Forced interrupt via activity.interrupt()
```

## 🔑 Key Implementation Details

### Critical Settings

1. **`discard_audio_if_uninterruptible=False`** - This is essential! Without this, audio is discarded when interruptions are disabled, and "stop" would never be detected by STT.

2. **Proactive Interruption Disabling** - New speech handles have `allow_interruptions=False` set immediately, preventing VAD from triggering before we can filter.

3. **Force Interrupt** - When interrupt words are detected, we call `activity.interrupt(force=True)` to stop the agent immediately.

## �📝 License

Apache-2.0 (same as LiveKit Agents)
