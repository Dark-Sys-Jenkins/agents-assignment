# Intelligent Interruption Handling

This document describes the intelligent interruption handling feature that enables context-aware filtering of user speech during voice agent conversations.

## Overview

The problem this feature solves: When the AI agent is explaining something important, LiveKit's default Voice Activity Detection (VAD) is too sensitive to user feedback. If the user says "yeah," "ok," "aha," or "hmm" (known as backchanneling) to indicate they are listening, the agent interprets this as an interruption and abruptly stops speaking.

The solution: A logic layer that is context-aware, distinguishing between "passive acknowledgement" and "active interruption" based on whether the agent is currently speaking or silent.

## Core Logic Matrix

| User Input | Agent State | Desired Behavior |
|------------|-------------|------------------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE**: Agent continues speaking without pausing or stopping |
| "Wait / Stop / No" | Speaking | **INTERRUPT**: Agent stops immediately and listens to the new command |
| "Yeah / Ok / Hmm" | Silent | **RESPOND**: Agent treats this as valid input (e.g., "Yeah." -> "Great, let's continue.") |
| "Start / Hello" | Silent | **RESPOND**: Normal conversational behavior |

## Key Features

### 1. Configurable Ignore List

Define a list of words that act as "soft" inputs (backchanneling):

```python
from livekit.agents.voice import InterruptionFilterConfig, InterruptionFilter

config = InterruptionFilterConfig()
config.backchannel_words = [
    'yeah', 'ok', 'hmm', 'right', 'uh-huh',
    'sure', 'got it', 'i see', 'aha', 'cool'
]
filter = InterruptionFilter(config)
```

### 2. State-Based Filtering

The filter only applies when the agent is actively generating or playing audio. When the agent is silent, all user input is treated as valid.

### 3. Semantic Interruption Detection

If the user says a mixed sentence like "Yeah wait a second," this contains a command ("wait"). The agent will interrupt in this case because the filter detects command words.

Default interrupt words include:
- wait, stop, no, hold, pause
- actually, but, however, question
- what, why, how, when, where, who
- repeat, again, sorry, pardon
- help, cancel, exit, quit, end

### 4. No VAD Modification

This is implemented as a logic handling layer within the agent's event loop, not as a modification to the low-level VAD kernel.

## Usage

### Basic Usage (Automatic)

The interruption filter is automatically enabled with default settings. No configuration needed:

```python
from livekit.agents import AgentSession

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2:...",
    allow_interruptions=True,
)
```

### Custom Configuration

You can customize the filter by modifying the default filter:

```python
from livekit.agents.voice import (
    InterruptionFilter,
    InterruptionFilterConfig,
    set_default_filter,
)

# Create custom configuration
config = InterruptionFilterConfig()

# Add additional backchannel words
config.backchannel_words.extend(['fascinating', 'interesting', 'wow'])

# Add additional interrupt words
config.interrupt_words.extend(['excuse me', 'one moment'])

# Set as default
custom_filter = InterruptionFilter(config)
set_default_filter(custom_filter)
```

### Environment Variables

You can also configure the filter via environment variables:

```bash
# Comma-separated list of backchannel words
export LIVEKIT_BACKCHANNEL_WORDS="yeah,ok,hmm,right,uh-huh"

# Comma-separated list of interrupt words
export LIVEKIT_INTERRUPT_WORDS="wait,stop,no,hold,pause"

# Enable/disable the filter
export LIVEKIT_INTERRUPTION_FILTER_ENABLED=true
```

## Example Agent

See `examples/voice_agents/intelligent_interruption.py` for a complete example that demonstrates:

1. Custom filter configuration
2. Event logging for debugging
3. An agent that gives long explanations to test the feature

## Test Scenarios

### Scenario 1: The Long Explanation
- **Context**: Agent is reading a long paragraph about history
- **User Action**: User says "Okay... yeah... uh-huh" while Agent is talking
- **Result**: Agent audio does not break. It ignores the user input completely.

### Scenario 2: The Passive Affirmation
- **Context**: Agent asks "Are you ready?" and goes silent
- **User Action**: User says "Yeah."
- **Result**: Agent processes "Yeah" as an answer and proceeds (e.g., "Okay, starting now").

### Scenario 3: The Correction
- **Context**: Agent is counting "One, two, three..."
- **User Action**: User says "No stop."
- **Result**: Agent cuts off immediately.

### Scenario 4: The Mixed Input
- **Context**: Agent is speaking
- **User Action**: User says "Yeah okay but wait."
- **Result**: Agent stops (because "but wait" contains command words).

## Technical Details

### Implementation

The interruption filter is implemented in `livekit/agents/voice/interruption_filter.py` and integrated into `livekit/agents/voice/agent_activity.py`.

The filter intercepts the `_interrupt_by_audio_activity()` method which is called when:
- VAD detects speech activity (`on_vad_inference_done`)
- STT provides interim transcripts (`on_interim_transcript`)
- STT provides final transcripts (`on_final_transcript`)

### Latency Considerations

The solution remains real-time with imperceptible delay because:
1. The filter uses pre-compiled regex patterns for efficient matching
2. The decision is made synchronously within the existing event loop
3. No additional network calls or async operations are required

### How It Handles VAD-Before-STT Timing

Since VAD is faster than STT, the filter handles the "false start" scenario:
1. VAD triggers before STT completes
2. If no transcript is available yet (empty string), the filter returns "ignore"
3. Once STT provides a transcript, the filter makes the final decision
4. If it's backchannel-only, the audio continues uninterrupted

## API Reference

### InterruptionFilterConfig

```python
@dataclass
class InterruptionFilterConfig:
    backchannel_words: list[str]  # Words to ignore while speaking
    interrupt_words: list[str]    # Words that always trigger interruption
    enabled: bool = True          # Enable/disable the filter
    min_words_for_interruption: int = 1  # Minimum words to consider
```

### InterruptionFilter

```python
class InterruptionFilter:
    def decide(transcript: str, agent_is_speaking: bool) -> Literal["ignore", "interrupt", "respond"]
    def contains_backchannel_only(text: str) -> bool
    def contains_interrupt_word(text: str) -> bool
    def add_backchannel_word(word: str) -> None
    def add_interrupt_word(word: str) -> None
    def remove_backchannel_word(word: str) -> None
    def remove_interrupt_word(word: str) -> None
```

### Helper Functions

```python
from livekit.agents.voice import get_default_filter, set_default_filter

# Get the current default filter
filter = get_default_filter()

# Set a custom filter as default
set_default_filter(my_custom_filter)
```
