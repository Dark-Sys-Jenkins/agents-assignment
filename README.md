# Context-Aware Interruption Logic for LiveKit Voice Agents

This document explains the context-aware interruption logic implementation that distinguishes between passive acknowledgements (backchanneling) and active interruptions in real-time AI voice agents.

## Overview

LiveKit's default Voice Activity Detection (VAD) is highly sensitive and immediately triggers interruptions whenever user audio is detected. This causes incorrect behavior when users provide passive acknowledgements such as "yeah", "ok", "aha", or "hmm" (commonly known as backchanneling). Instead of recognizing these as signs of engagement, the agent would abruptly stop speaking, breaking conversational flow.

**The Solution**: A context-aware decision system that correctly distinguishes between:
1. **Passive acknowledgements** (soft inputs) - should not interrupt when agent is speaking
2. **Active interruptions** (hard commands) - should always interrupt

## How It Works

The interruption logic operates **above the VAD layer** and validates the final Speech-to-Text (STT) transcript before committing to an interruption. This ensures that:

- VAD may fire before STT completes (false starts)
- The system waits for transcript validation before pausing
- Passive acknowledgements are ignored when the agent is speaking
- Interrupt commands are always respected immediately

### Decision Flow

```
User Audio Detected (VAD fires)
    ↓
Wait for STT Transcript (if agent is speaking)
    ↓
Classify Interruption:
    ├─ Contains interrupt command? → INTERRUPT
    ├─ Agent SPEAKING + passive acknowledgement? → IGNORE
    ├─ Agent SILENT + passive acknowledgement? → RESPOND
    └─ Agent SILENT + normal input? → RESPOND
```

## Decision Rules

The system outputs exactly **ONE** of three decisions:

### 1. `INTERRUPT` - Stop the agent immediately
- **Trigger**: Transcript contains ANY interrupt command, even if mixed with passive acknowledgements
- **Examples**: 
  - "stop"
  - "wait"
  - "yeah wait a second" → INTERRUPT (contains "wait")
  - "ok no stop" → INTERRUPT (contains "no" and "stop")

### 2. `IGNORE` - Continue speaking without interruption
- **Trigger**: Agent is SPEAKING AND transcript contains ONLY passive acknowledgement words
- **Examples**:
  - Agent speaking: "yeah" → IGNORE
  - Agent speaking: "ok" → IGNORE
  - Agent speaking: "yeah ok" → IGNORE
  - Agent speaking: "yeah but" → INTERRUPT (contains non-passive word)

### 3. `RESPOND` - Process as new user turn
- **Trigger**: Agent is SILENT AND transcript contains any input
- **Examples**:
  - Agent silent: "yeah" → RESPOND
  - Agent silent: "hello" → RESPOND
  - Agent silent: "tell me a story" → RESPOND

## Passive Acknowledgements vs Interrupt Commands

### Passive Acknowledgements (Soft Inputs)
These words indicate engagement but should not interrupt when the agent is speaking:
- `yeah`
- `ok`
- `okay`
- `hmm`
- `aha`
- `uh-huh`
- `uh huh`
- `right`

### Interrupt Commands (Hard Inputs)
These words always trigger an interruption, regardless of context:
- `stop`
- `wait`
- `no`
- `cancel`
- `hold on`
- `hold`

## Implementation Details

### Core Function

The logic is implemented in `livekit-agents/livekit/agents/voice/interruption_logic.py`:

```python
def classify_interruption(
    agent_state: Literal["SPEAKING", "SILENT"],
    user_transcript: str,
) -> InterruptionDecision:
    """Classify user input as INTERRUPT, IGNORE, or RESPOND."""
    # Rule 1: Check for interrupt commands (highest priority)
    # Rule 2: If speaking + passive acknowledgement → IGNORE
    # Rule 3: If silent + passive acknowledgement → RESPOND
    # Rule 4: If silent + normal input → RESPOND
```

### Integration Points

The logic is integrated into the agent's audio activity handling at three key points:

1. **`_interrupt_by_audio_activity()`** - Prevents premature pauses when VAD fires before transcript is available
2. **`on_interim_transcript()`** - Checks interim transcripts and resumes if false interruption detected
3. **`on_final_transcript()`** - Validates final transcripts and prevents interruption for passive acknowledgements
4. **`on_end_of_turn()`** - Prevents passive acknowledgements from being processed as new user turns

### Key Features

- **Transcript-first approach**: When agent is speaking, waits for transcript before pausing
- **False interruption recovery**: Automatically resumes if pause occurred before transcript validation
- **Turn prevention**: Prevents passive acknowledgements from triggering new LLM responses
- **Punctuation handling**: Normalizes transcripts to handle variations like "yeah!", "ok?", "hmm."

## How to Run the Agent

### Prerequisites

1. **Python 3.12+** installed
2. **Environment variables** set:
   ```bash
   # LiveKit credentials
   LIVEKIT_URL=wss://your-livekit-server.com
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   
   # Groq API (for LLM and STT)
   GROQ_API_KEY=your-groq-api-key
   
   # Cartesia API (for TTS)
   CARTESIA_API_KEY=your-cartesia-api-key
   ```

3. **Install dependencies**:
   ```bash
   # Install workspace packages in editable mode
   uv pip install -e livekit-agents
   uv pip install -e livekit-plugins/livekit-plugins-groq
   uv pip install -e livekit-plugins/livekit-plugins-silero
   uv pip install -e livekit-plugins/livekit-plugins-turn-detector
   uv pip install -e livekit-plugins/livekit-plugins-cartesia
   ```

### Running the Agent

1. **Navigate to the examples directory**:
   ```bash
   cd examples/voice_agents
   ```

2. **Start the agent in development mode**:
   ```bash
   python basic_agent.py dev
   ```

   This will:
   - Start the agent server with hot reloading
   - Connect to your LiveKit server
   - Enable the interruption logic automatically

3. **Connect using LiveKit Playground**:
   - Visit https://agents-playground.livekit.io/
   - Enter your LiveKit credentials
   - Start a conversation with the agent

### Testing the Interruption Logic

#### Test Case 1: Ignore "yeah" while agent is speaking
1. Start a conversation with the agent
2. Wait for the agent to start speaking
3. While the agent is speaking, say "yeah" or "ok"
4. **Expected**: Agent continues speaking without pause or interruption

#### Test Case 2: Respond to "yeah" when agent is silent
1. Start a conversation with the agent
2. Wait for the agent to finish speaking (agent becomes silent)
3. Say "yeah" or "ok"
4. **Expected**: Agent processes this as a new user turn and responds

#### Test Case 3: Stop for "stop" command
1. Start a conversation with the agent
2. While the agent is speaking, say "stop" or "wait"
3. **Expected**: Agent immediately stops speaking

#### Test Case 4: Mixed commands
1. While agent is speaking, say "yeah wait a second"
2. **Expected**: Agent interrupts (because "wait" is an interrupt command)

## Code Structure

```
livekit-agents/
└── livekit/
    └── agents/
        └── voice/
            ├── interruption_logic.py      # Core classification logic
            └── agent_activity.py          # Integration with agent lifecycle
```

## Technical Constraints

- **Latency**: Decisions are made in real-time with no perceptible delay
- **VAD Independence**: Logic operates above VAD layer, VAD kernel is not modified
- **Transcript Validation**: System validates final STT transcript before committing to interruption
- **False Start Handling**: Supports "false start" scenarios where VAD fires but transcript resolves to passive acknowledgement

## Example Scenarios

### Scenario 1: Natural Backchanneling
```
Agent: "So the weather in London is typically..."
User: "yeah"
Agent: "...rainy during the winter months..." [continues seamlessly]
```
**Result**: `IGNORE` - Agent continues speaking

### Scenario 2: User Wants to Interrupt
```
Agent: "Let me explain how this works..."
User: "stop, I have a question"
Agent: [stops immediately]
```
**Result**: `INTERRUPT` - Contains "stop" command

### Scenario 3: User Responds When Agent is Silent
```
Agent: [finished speaking, now silent]
User: "yeah, that makes sense"
Agent: [processes as new turn, generates response]
```
**Result**: `RESPOND` - Agent is silent, so "yeah" triggers a response

### Scenario 4: Ambiguous Input
```
Agent: "The process involves three steps..."
User: "yeah but what about the cost?"
Agent: [interrupts]
```
**Result**: `INTERRUPT` - Contains non-passive word "but", so treated as interruption

## Debugging

To see the interruption logic in action, check the logs for:
- `"Resumed speech after passive acknowledgement"` - Indicates false interruption was detected and corrected
- `"Ignoring passive acknowledgement as new turn"` - Indicates passive acknowledgement was prevented from triggering a new turn

## Limitations

- The logic is deterministic and rule-based. It does not use ML/NLP models for semantic understanding beyond keyword matching.
- Passive acknowledgements list is fixed. Adding new acknowledgements requires code changes.
- The system relies on accurate STT transcription. Mis-transcribed words may not be classified correctly.

## Future Enhancements

Potential improvements:
- Expand passive acknowledgements list dynamically
- Use semantic similarity for better classification
- Support multiple languages
- Learn from user behavior patterns

## Contributing

When modifying the interruption logic:
1. Update tests in `tests/test_interruption_logic.py`
2. Test all three decision types (INTERRUPT, IGNORE, RESPOND)
3. Verify edge cases (punctuation, mixed case, empty transcripts)
4. Ensure no regression in existing behavior

---

**Note**: This interruption logic is automatically enabled when using the `AgentSession` with VAD and STT configured. No additional configuration is required.
