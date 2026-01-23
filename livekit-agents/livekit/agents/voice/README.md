# Intelligent Interruption Handling - Backchanneling Detection

## 🎯 Overview

This implementation adds **context-aware backchanneling detection** to the LiveKit Agents framework. The agent intelligently distinguishes between passive acknowledgments ("yeah", "ok", "hmm") and active interruptions ("wait", "stop", "no").

### The Problem Solved
Previously, the AI agent would stop speaking whenever it detected any user voice activity. This caused unnatural conversation flow - even when the user was just saying "yeah" to show they were listening.

### The Solution
**Background Speech Processing**: The agent processes user speech in the background while continuing to speak. Only when STT confirms an interrupt word does the agent stop.

- User says "yeah" while agent speaks → Agent continues seamlessly
- User says "wait" while agent speaks → Agent stops and listens

---

## ✅ Features Implemented

| Feature | Description |
|---------|-------------|
| **Configurable Word Lists** | Easily customizable backchanneling and interrupt word sets |
| **Multi-language Support** | Built-in words for English, Hindi, Spanish, French |
| **State-Based Filtering** | Backchanneling only ignored when agent is speaking |
| **Semantic Interruption** | Mixed inputs like "yeah but wait" correctly trigger interruption |
| **Seamless Speech** | Agent continues without pause during backchanneling |

---

## 📁 Files Changed

```
livekit-agents/livekit/agents/voice/
├── backchanneling_config.py # NEW - Configuration and word lists
├── agent_activity.py        # MODIFIED - Integration hooks
├── agent_session.py         # MODIFIED - Config parameter
└── __init__.py              # MODIFIED - Exports
```

---

## 🚀 Quick Start

### Basic Usage (Default Configuration)

```python
from livekit.agents.voice import AgentSession

# Backchanneling detection is enabled by default
session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4o-mini",
    tts="cartesia/sonic-2",
)
```

### Custom Configuration

```python
from livekit.agents.voice import AgentSession
from livekit.agents.voice.backchanneling_config import create_config

# Add custom words
custom_config = create_config(
    backchanneling_words={"roger", "copy that", "understood"},
    interrupt_words={"cancel", "abort", "emergency"},
)

session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4o-mini", 
    tts="cartesia/sonic-2",
    backchanneling_config=custom_config,
)
```

### Disable Backchanneling Detection

```python
from livekit.agents.voice.backchanneling_config import create_config

config = create_config(enabled=False)

session = AgentSession(
    ...,
    backchanneling_config=config,
)
```

---

## 🔧 Configuration Options

### BackchannelingConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `True` | Enable/disable backchanneling detection |
| `backchanneling_words` | FrozenSet[str] | See below | Words to ignore when agent is speaking |
| `interrupt_words` | FrozenSet[str] | See below | Words that always trigger interruption |

### Default Word Lists

**Backchanneling Words (Ignored when agent speaks):**
```
English: yeah, yes, yep, ok, okay, alright, hmm, mhm, uh-huh, right, 
         sure, got it, gotcha, cool, awesome, go on, continue...

Hindi:   theek, theek hai, haan, bilkul, accha, ji, haanji...

Spanish: sí, vale, claro, bueno, ajá...

French:  oui, ouais, d'accord, bon...
```

**Interrupt Words (Always stop agent):**
```
English: wait, stop, hold, pause, no, nope, hey, listen, actually, but,
         what, why, how, wrong, sorry, repeat...

Hindi:   ruk, ruko, nahi, mat, suno...

Spanish: espera, para, no, perdón...

French:  attends, non, arrête, pardon...
```

---

## 🧪 Test Scenarios

The implementation handles all required test scenarios:

### Scenario 1: Long Explanation ✅
- **Context:** Agent reading a long paragraph
- **User says:** "Okay... yeah... uh-huh"
- **Result:** Agent continues speaking without any interruption

### Scenario 2: Passive Affirmation ✅
- **Context:** Agent asks "Are you ready?" and goes silent
- **User says:** "Yeah"
- **Result:** Agent processes "Yeah" as a valid answer and proceeds

### Scenario 3: The Correction ✅
- **Context:** Agent counting "One, two, three..."
- **User says:** "No stop"
- **Result:** Agent stops (after STT processing)

### Scenario 4: Mixed Input ✅
- **Context:** Agent is speaking
- **User says:** "Yeah okay but wait"
- **Result:** Agent stops (detects "but" and "wait" as interrupt words)

---

## 🏗️ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        EVENT FLOW                               │
└─────────────────────────────────────────────────────────────────┘

User speaks while agent is talking
         │
         ▼
┌─────────────────┐
│ VAD Detects     │
│ Voice Activity  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent Continues │  ◄── No pause! Speech keeps going
│ Speaking        │
└────────┬────────┘
         │
         ▼ (STT processes in background)
┌─────────────────┐
│ STT Returns     │
│ Transcript      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check: Is it    │
│ backchanneling? │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│"yeah" │ │"wait" │
│IGNORE │ │ STOP  │
│continue│ │agent  │
└───────┘ └───────┘
```

---

## 📝 API Reference

### BackchannelingConfig Factory

```python
from livekit.agents.voice.backchanneling_config import (
    create_config,
    create_english_only_config,
    DEFAULT_BACKCHANNELING_CONFIG,
    DEFAULT_BACKCHANNELING_WORDS,
    DEFAULT_INTERRUPT_WORDS,
)

# Create with all options
config = create_config(
    enabled=True,
    backchanneling_words={"custom", "words"},  # Adds to defaults
    interrupt_words={"custom", "interrupts"},   # Adds to defaults
    extend_defaults=True,                       # Set False to replace
)

# English-only config (no Hindi/Spanish/French)
english_config = create_english_only_config()
```

---

## 🔍 Troubleshooting

### Agent still stops on "yeah"
- Check that `backchanneling_config.enabled` is `True`
- Verify the word is in the `backchanneling_words` set
- Check STT is transcribing correctly (might be hearing differently)

### Agent doesn't stop on "wait"
- Verify the word is in the `interrupt_words` set
- STT processing takes ~1-1.5s - this is expected latency

### Want faster interrupt response?
- The delay is due to STT processing time
- Consider using a faster STT provider
- The tradeoff is accuracy vs speed

---

## 📄 License

This implementation follows the same license as the LiveKit Agents framework.
