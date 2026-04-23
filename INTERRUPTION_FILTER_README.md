# Interruption Filter for LiveKit Agents

## Problem

The agent stops talking when users say "yeah" or "ok" while it's speaking. This is annoying because people naturally say these words to show they're listening.

## Solution

Added a filter that checks what the user said and whether the agent is speaking. If the agent is speaking and the user only said backchanneling words like "yeah" or "ok", it ignores the interruption.

## How to Use

### Basic Usage

```python
from livekit.agents import AgentSession

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    vad=silero.VAD.load(),
    interruption_filter_enabled=True,  # enabled by default
)
```

### Custom Ignore Words

```python
session = AgentSession(
    # ... other params ...
    interruption_ignore_words=['yeah', 'ok', 'sure', 'gotcha'],
)
```

### Environment Variable

```bash
export LIVEKIT_INTERRUPTION_IGNORE_WORDS="yeah,ok,hmm,right"
```

### Disable the Filter

```python
session = AgentSession(
    # ... other params ...
    interruption_filter_enabled=False,
)
```

## Default Ignore Words

yeah, ok, okay, hmm, mhm, mm-hmm, uh-huh, right, aha, ah, oh, sure, yep, yup, gotcha, got it, alright, cool

## How It Works

1. User speaks while agent is talking
2. VAD detects speech
3. STT transcribes what they said
4. Filter checks:
   - Is agent speaking? 
   - Are all words in the ignore list?
   - If yes to both → ignore it, agent keeps talking
   - If no → stop the agent

## Examples

**Agent speaking, user says "yeah":**
- Filter ignores it, agent continues

**Agent speaking, user says "wait":**
- Filter allows it, agent stops

**Agent silent, user says "yeah":**
- Filter allows it, agent responds

**Agent speaking, user says "yeah wait":**
- Filter allows it (contains "wait"), agent stops

## Testing

Run the test:
```bash
python direct_test.py
```

All 4 test scenarios should pass.

## Implementation Details

The filter is in `interruption_filter.py`. It's integrated into `agent_activity.py` in the `_interrupt_by_audio_activity()` method.

When an interruption is detected, it checks the transcript and agent state before deciding whether to actually interrupt.

## Configuration

You can customize the ignore words list or disable the filter entirely. The filter is enabled by default because it improves the conversation flow.

## Performance

The filter adds less than 1ms of latency. It just does simple string matching on the transcript.
