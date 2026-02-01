# Intelligent Interruption Handling for LiveKit Agents

**Demo video:** [Interruption handling in action](https://youtu.be/ynl37J1Hq4M)

## Problem

When an AI agent is speaking, LiveKit's default VAD is too sensitive to user feedback. If the user says "yeah," "ok," or "hmm" to indicate they're listening, the agent interprets this as an interruption and stops speaking abruptly.

## Solution

The `InterruptionFilter` analyzes STT transcripts in real-time to distinguish between **backchannels** (passive acknowledgements) and **real interruptions** (commands to stop).

### Behavior Matrix

| User Input | Agent State | Result |
|------------|-------------|--------|
| "Yeah / Ok / Hmm" | Speaking | **IGNORE** - Agent continues |
| "Wait / Stop / No" | Speaking | **INTERRUPT** - Agent stops |
| "Yeah / Ok / Hmm" | Silent | **RESPOND** - Normal reply |
| "Yeah wait a second" | Speaking | **INTERRUPT** - Command detected |

## Quick Start

```python
from livekit.agents.voice import AgentSession, InterruptionFilter

session = AgentSession(
    stt=deepgram.STT(),
    vad=silero.VAD.load(),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=openai.TTS(),
    interruption_filter=InterruptionFilter(),  # Enable filtering
)
```

## Configuration

**Custom words:**
```python
InterruptionFilter(
    ignore_words=["roger", "copy"],
    interrupt_words=["abort", "cancel"],
)
```

**Environment variables:**
- `LIVEKIT_IGNORE_WORDS` - Comma-separated backchannel words
- `LIVEKIT_INTERRUPT_WORDS` - Comma-separated interrupt words

## Default Word Lists

**Backchannels (ignored):** yeah, ok, hmm, mhm, uh-huh, right, sure, got it, alright, cool, nice, great, yes, yep, um, uh, etc.

**Interrupts (stops agent):** stop, wait, hold on, pause, no, nope, actually, but, excuse me, let me, can i, question, etc.

## Files Changed

| File | Change |
|------|--------|
| `livekit/agents/voice/interruption_filter.py` | NEW - Core filter |
| `livekit/agents/voice/agent_activity.py` | Integration |
| `livekit/agents/voice/agent_session.py` | Added parameter |
| `tests/test_interruption_filter.py` | NEW - Tests |
| `examples/voice_agents/weather_agent.py` | Example |

## Running Tests

```bash
pytest tests/test_interruption_filter.py -v
```

## Running Example

```bash
export OPENAI_API_KEY="your-key"
export DEEPGRAM_API_KEY="your-key"
python examples/voice_agents/weather_agent.py dev
```

## Important Notes

- Works with **STT+LLM+TTS pipeline only** (not OpenAI Realtime API)
- No VAD modification - operates as a logic layer on top
- Real-time performance - simple word matching, no LLM inference
