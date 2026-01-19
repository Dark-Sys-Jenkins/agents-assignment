# Intelligent Interruption Handling

## Overview

This feature implements context-aware interruption handling for LiveKit voice agents. It distinguishes between **passive acknowledgements** (backchannels like "yeah", "ok", "hmm") and **active interruption commands** (like "stop", "wait", "no") based on whether the agent is currently speaking.

## Key Features

- **Seamless Continuation**: When user says backchannels while agent speaks, audio continues without pause, stutter, or hiccup
- **State-Aware**: Same word ("yeah") is ignored during speech but processed normally when agent is silent
- **Mixed Input Detection**: "Yeah but wait" triggers interrupt because it contains "wait"
- **Configurable Word Lists**: Customize backchannel and interrupt words via constructor parameters
- **Zero New Files**: Integrated directly into existing `agent_activity.py` and `agent_session.py`

## Logic Matrix

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE** - Agent continues seamlessly |
| "Stop / Wait / No" | Speaking | **INTERRUPT** - Agent stops immediately |
| "Yeah / Ok / Hmm" | Silent | **RESPOND** - Valid input, agent responds |
| "Yeah but wait" | Speaking | **INTERRUPT** - Contains interrupt word |

## Configuration

```python
from livekit.agents import AgentSession

session = AgentSession(
    # Enable backchannel filtering (default: False for backward compatibility)
    # Set to True to enable intelligent backchannel handling
    ignore_backchannels_when_speaking=True,
    
    # Customize backchannel words (default: common acknowledgements)
    backchannel_words=frozenset({
        "yeah", "yep", "yes", "ok", "okay", "hmm", "mhm", "uhuh",
        "right", "sure", "mm", "aha", "gotcha", "alright"
    }),
    
    # Customize interrupt words (default: stop commands)
    interrupt_words=frozenset({
        "stop", "wait", "no", "cancel", "pause", "hold", "quit", "end"
    }),
)
```

## How It Works

1. **VAD Detection**: Voice Activity Detection triggers when user speaks
2. **STT Transcription**: Speech-to-Text produces transcript
3. **Classification**: `_classify_interruption()` checks if transcript is:
   - Pure backchannel (all words in `backchannel_words`)
   - Contains interrupt command (any word in `interrupt_words`)
4. **Decision**: If agent is speaking and input is pure backchannel → **IGNORE**
5. **Early Return**: Returns before any audio manipulation for zero latency impact

## Files Modified

| File | Changes |
|------|---------|
| `agent_session.py` | Added `backchannel_words`, `interrupt_words`, `ignore_backchannels_when_speaking` options |
| `agent_activity.py` | Added `_classify_interruption()` helper and filtering in `_interrupt_by_audio_activity()` |

## Testing

```bash
# Run the interruption filter tests
python -m pytest tests/test_interruption_filter.py -v

# Run all agent session tests
python -m pytest tests/test_agent_session.py -v
```

## Log Output

When backchannel filtering is active, you'll see debug logs:

```
DEBUG - ignoring backchannel while agent speaking - {"transcript": "yeah", "action": "IGNORE"}
DEBUG - interrupt command detected while agent speaking - {"transcript": "stop", "action": "INTERRUPT"}
```
