# Intelligent Interruption Handling for LiveKit Agents

## Overview

This feature implements context-aware interruption handling that distinguishes between **backchanneling** (passive acknowledgements like "yeah", "ok", "hmm") and **real interruptions** based on the agent's current state.

### The Problem

LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. When the AI agent is explaining something important, if the user says "yeah," "ok," "aha," or "hmm" (backchanneling) to indicate they are listening, the agent interprets this as an interruption and abruptly stops speaking.

### The Solution

This implementation adds a logic layer that filters user input based on:
1. **Agent State**: Whether the agent is currently speaking or silent
2. **Transcript Content**: Whether the user said backchanneling words or real commands
3. **Semantic Analysis**: Detection of interrupt keywords even in mixed sentences

## Logic Matrix

| User Input | Agent State | Desired Behavior |
|------------|-------------|------------------|
| "Yeah / Ok / Hmm" | Agent is Speaking | **IGNORE**: Agent continues speaking without pausing |
| "Wait / Stop / No" | Agent is Speaking | **INTERRUPT**: Agent stops immediately and listens |
| "Yeah / Ok / Hmm" | Agent is Silent | **RESPOND**: Agent treats this as valid input |
| "Start / Hello" | Agent is Silent | **RESPOND**: Normal conversational behavior |
| "Yeah wait a second" | Agent is Speaking | **INTERRUPT**: Contains interrupt keyword "wait" |

## Installation

No additional dependencies required. The feature is built into the LiveKit Agents framework.

## Usage

### Basic Usage

```python
from livekit.agents import AgentSession

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    # Enable intelligent interruption handling (enabled by default)
    intelligent_interruption_enabled=True,
)
```

### Custom Configuration

```python
# Define custom backchanneling words
custom_backchanneling = frozenset([
    "yeah", "yea", "yep", "yes", "ok", "okay",
    "hmm", "uh-huh", "right", "sure",
    "i see", "got it", "gotcha",
    "uh", "um", "like",
    # Add your custom words
    "understood", "go on",
])

# Define custom interrupt keywords
custom_interrupt_keywords = frozenset([
    "wait", "stop", "hold on", "pause", "no",
    "actually", "but", "however",
    "question", "what", "why", "how",
    # Add your custom keywords
    "repeat", "slow down",
])

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    # Intelligent interruption config
    intelligent_interruption_enabled=True,
    backchanneling_words=custom_backchanneling,
    interrupt_keywords=custom_interrupt_keywords,
    max_backchanneling_words=3,  # Max words to consider as backchanneling
)
```

### Disabling the Feature

```python
session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    # Disable intelligent interruption handling
    intelligent_interruption_enabled=False,
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `intelligent_interruption_enabled` | `bool` | `True` | Enable/disable the feature |
| `backchanneling_words` | `frozenset[str]` | See below | Words to ignore while speaking |
| `interrupt_keywords` | `frozenset[str]` | See below | Words that always trigger interruption |
| `max_backchanneling_words` | `int` | `3` | Max words to consider as backchanneling |

### Default Backchanneling Words

```python
DEFAULT_BACKCHANNELING_WORDS = frozenset([
    "yeah", "yea", "yep", "yes", "yup", "ya",
    "ok", "okay", "k",
    "hmm", "hm", "mm", "mmhmm", "mhm", "uh-huh", "uhuh", "uh huh",
    "right", "alright", "sure",
    "i see", "got it", "gotcha",
    "ah", "aha", "oh", "ooh",
    "nice", "cool", "great", "good", "fine",
    "true", "indeed",
    "uh", "um", "er", "like",
])
```

### Default Interrupt Keywords

```python
DEFAULT_INTERRUPT_KEYWORDS = frozenset([
    "wait", "stop", "hold on", "hold", "pause", "no",
    "actually", "but", "however", "excuse me",
    "question", "what", "why", "how", "when", "where", "who",
    "can you", "could you", "would you",
    "i have", "i need", "i want",
    "let me", "hang on", "one second", "one moment",
    "sorry", "pardon",
])
```

## Technical Implementation

### Architecture

The implementation consists of three main components:

1. **InterruptionFilter** (`interruption_filter.py`)
   - Core filtering logic
   - Configurable word lists
   - Decision engine for ignore/interrupt/respond

2. **AgentSessionOptions** (`agent_session.py`)
   - Configuration storage
   - New options for intelligent interruption

3. **AgentActivity** (`agent_activity.py`)
   - Integration with VAD and STT events
   - Decision enforcement

### How It Works

```
Audio Input → VAD Detection → STT Transcription → Interruption Filter → Decision
                                                         ↓
                                                 Agent State Check
                                                         ↓
                                           ┌─────────────┴─────────────┐
                                           ↓                           ↓
                                   Agent Speaking              Agent Silent
                                           ↓                           ↓
                                   Check Transcript              Respond to
                                           ↓                      All Input
                                  ┌────────┴────────┐
                                  ↓                 ↓
                         Backchanneling        Real Input
                                  ↓                 ↓
                              IGNORE           INTERRUPT
```

### Key Design Decisions

1. **VAD Deferral**: When intelligent interruption is enabled and the agent is speaking, VAD-triggered interruptions are deferred to STT. This prevents the agent from pausing before we know what the user said.

2. **STT-Based Filtering**: The actual filtering happens when STT provides a transcript. This ensures we have the text content needed to make an informed decision.

3. **Semantic Detection**: The filter checks for interrupt keywords within any transcript, so "yeah wait a second" triggers an interruption because it contains "wait".

4. **Word Count Threshold**: If the user says more than `max_backchanneling_words`, it's treated as real input regardless of content.

## Example Scenarios

### Scenario 1: The Long Explanation

**Context**: Agent is reading a long paragraph about history.
**User Action**: User says "Okay... yeah... uh-huh" while Agent is talking.
**Result**: Agent audio does not break. It ignores the user input completely.

### Scenario 2: The Passive Affirmation

**Context**: Agent asks "Are you ready?" and goes silent.
**User Action**: User says "Yeah."
**Result**: Agent processes "Yeah" as an answer and proceeds (e.g., "Okay, starting now").

### Scenario 3: The Correction

**Context**: Agent is counting "One, two, three..."
**User Action**: User says "No stop."
**Result**: Agent cuts off immediately.

### Scenario 4: The Mixed Input

**Context**: Agent is speaking.
**User Action**: User says "Yeah okay but wait."
**Result**: Agent stops (because "but wait" contains interrupt keywords).

## Running the Example Agent

1. Set up environment variables:
```bash
export LIVEKIT_URL=<your-livekit-url>
export LIVEKIT_API_KEY=<your-api-key>
export LIVEKIT_API_SECRET=<your-api-secret>
export DEEPGRAM_API_KEY=<your-deepgram-key>
export OPENAI_API_KEY=<your-openai-key>
export CARTESIA_API_KEY=<your-cartesia-key>
```

2. Run the example:
```bash
cd examples/voice_agents
python intelligent_interruption_agent.py dev
```

3. Connect to the agent using the LiveKit Agents Playground or your own client.

4. Test the feature:
   - Ask the agent to explain something (triggers a long response)
   - While it's speaking, say "yeah", "ok", or "hmm"
   - The agent should continue speaking
   - Say "wait" or "stop" - the agent should stop

## Debugging

Enable debug logging to see the filter decisions:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

You'll see logs like:
```
DEBUG: Ignoring backchanneling during agent speech: 'yeah' (reason: Backchanneling while agent speaking)
DEBUG: Interrupting agent speech: 'wait' (reason: Contains interrupt keyword)
DEBUG: Deferring interruption decision to STT (intelligent interruption enabled, agent speaking)
```

## Files Changed

| File | Description |
|------|-------------|
| `livekit-agents/livekit/agents/voice/interruption_filter.py` | New file - core filtering logic |
| `livekit-agents/livekit/agents/voice/agent_session.py` | Added configuration options |
| `livekit-agents/livekit/agents/voice/agent_activity.py` | Integration with event handlers |
| `examples/voice_agents/intelligent_interruption_agent.py` | Example demonstrating the feature |

## Contributing

1. Fork the repository
2. Create a feature branch: `feature/interrupt-handler-<yourname>`
3. Make your changes
4. Submit a pull request to: https://github.com/Dark-Sys-Jenkins/agents-assignment

**DO NOT submit PRs to the original LiveKit repo.**

## License

This implementation follows the same license as the LiveKit Agents framework.
