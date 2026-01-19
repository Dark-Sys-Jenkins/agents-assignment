# Filler Word Interruption Filter for LiveKit Voice Agents

## 🎯 Overview

This implementation adds **context-aware filler word detection** to LiveKit Voice Agents. The agent intelligently distinguishes between:

- **Passive acknowledgments** ("yeah", "ok", "hmm") that should be ignored while speaking
- **Active interruptions** ("stop", "wait", "no") that should immediately interrupt the agent
- **Mixed inputs** ("yeah okay but wait") where a command follows filler words

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Context-Aware** | Filter only activates when agent is speaking |
| **Accumulation-Based** | Buffers transcript until a decision can be made |
| **Configurable** | Easy to customize filler word list |
| **Zero-Latency** | Simple set lookup, no ML or external calls |
| **No VAD Modification** | Implemented as logic layer, not VAD changes |

## ✅ Test Results

```
============== 61 passed in 0.65s ==============

Tests Covered:
├── TestInterruptionFilterBasic (5 tests)
├── TestScenario1LongExplanation (3 tests)
├── TestScenario2PassiveAffirmation (3 tests)
├── TestScenario3Correction (5 tests)
├── TestScenario4MixedInput (4 tests)
├── TestEdgeCases (6 tests)
├── TestCreateInterruptionFilter (3 tests)
├── TestStateTransitions (3 tests)
└── TestDefaultFillerWords (29 parametrized tests)
```

**Run tests:**
```bash
cd livekit-agents
python -m pytest tests/test_interruption_filter.py -v
```

**Generate proof log:**
```bash
python demo_proof.py > PROOF_LOG.txt
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTERRUPTION FILTER FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │  VAD START   │
                              │ (User speaks)│
                              └──────┬───────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │  Is Agent Speaking?    │
                        └────────────┬───────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
            ┌───────────────┐                 ┌───────────────┐
            │     YES       │                 │      NO       │
            │ Filter ACTIVE │                 │ Filter OFF    │
            └───────┬───────┘                 └───────┬───────┘
                    │                                 │
                    ▼                                 ▼
        ┌───────────────────────┐         ┌───────────────────────┐
        │  Accumulate words     │         │  PASS THROUGH         │
        │  Check each one       │         │  Process normally     │
        └───────────┬───────────┘         └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  Is word in FILLER_WORDS?                             │
        │                                                       │
        │  YES (filler) → Keep waiting                          │
        │  NO (real word) → INTERRUPT immediately               │
        └───────────────────────────────────────────────────────┘
```

## 📋 Logic Matrix

| User Input | Agent State | Behavior | Result |
|------------|-------------|----------|--------|
| "Yeah / Ok / Hmm" | **Speaking** | IGNORE | Agent continues uninterrupted |
| "Wait / Stop / No" | **Speaking** | INTERRUPT | Agent stops immediately |
| "Yeah / Ok / Hmm" | **Silent** | RESPOND | Agent processes as valid input |
| "Start / Hello" | **Silent** | RESPOND | Normal conversation |
| "Yeah okay but wait" | **Speaking** | INTERRUPT | "but" triggers interrupt |

## 🚀 Quick Start

### Basic Usage

```python
from livekit.agents import voice

# Create agent session with default filler words
session = voice.AgentSession(
    # ... other options
)
```

The filter is **enabled by default** with a comprehensive list of filler words.

### Custom Filler Words

```python
from livekit.agents import voice

# Use custom filler words
session = voice.AgentSession(
    filler_words=["yeah", "ok", "hmm", "right", "sure", "gotcha"],
    # ... other options
)
```

### Disable Filler Word Filtering

```python
session = voice.AgentSession(
    filler_words=[],  # Empty list disables filtering
    # ... other options
)
```

## 🔧 Configuration

### Default Filler Words

The following words are ignored by default when the agent is speaking:

```python
DEFAULT_FILLER_WORDS = {
    # Affirmations
    "yeah", "yep", "yes", "yup", "yea",
    "ok", "okay", "k", "kay",
    "sure", "right", "alright",
    
    # Backchannels
    "hmm", "hm", "mm", "mmm", "mhm", "mm-hmm",
    "uh-huh", "aha", "ah",
    
    # Hesitations
    "uh", "um", "er", "eh", "oh",
    
    # Continuers
    "go on", "continue", "i see", "got it", "gotcha",
    "understood", "makes sense",
}
```

### Adding Custom Words

You can extend the defaults or replace them entirely:

```python
from livekit.agents.voice import create_interruption_filter, DEFAULT_FILLER_WORDS

# Extend defaults
filter = create_interruption_filter(
    filler_words=["totally", "absolutely", "for sure"],
    extend_defaults=True  # Adds to defaults
)

# Replace defaults
filter = create_interruption_filter(
    filler_words=["yes", "no", "maybe"],
    extend_defaults=False  # Uses only these words
)
```

## 📝 Test Scenarios

### Scenario 1: The Long Explanation
```
Agent: "The French Revolution began in 1789 and was a period of..."
User: "Okay... yeah... uh-huh"
Result: Agent continues speaking (fillers ignored)
```

### Scenario 2: The Passive Affirmation
```
Agent: "Are you ready to proceed?"
[Agent goes silent]
User: "Yeah."
Result: Agent responds "Great, let's continue." (processed as input)
```

### Scenario 3: The Correction
```
Agent: "One, two, three, four..."
User: "No stop."
Result: Agent stops immediately ("no" is not a filler)
```

### Scenario 4: The Mixed Input
```
Agent: "Let me explain the next steps..."
User: "Yeah okay but wait."
Result: Agent stops (because "but" is not in filler list)
```

## 🧪 Running Tests

```bash
# Navigate to the livekit-agents directory
cd livekit-agents

# Run all interruption filter tests
pytest tests/test_interruption_filter.py -v

# Run specific scenario tests
pytest tests/test_interruption_filter.py::TestScenario1LongExplanation -v
pytest tests/test_interruption_filter.py::TestScenario2PassiveAffirmation -v
pytest tests/test_interruption_filter.py::TestScenario3Correction -v
pytest tests/test_interruption_filter.py::TestScenario4MixedInput -v
```

## 🔍 How It Works

### The Problem

VAD (Voice Activity Detection) is faster than STT (Speech-to-Text). When VAD triggers, we might only have partial transcript:

```
Timeline:    0ms      300ms     500ms     700ms
User says:   "yeah...............but.......wait"
VAD fires:   ▲ HERE!
STT has:     ""       "yeah"   "yeah but" "yeah but wait"
```

If we check only when VAD fires, we might wrongly ignore "yeah but wait" because we only see "yeah".

### Our Solution: Accumulation-Based State Machine

1. **VAD START** → Check if agent is speaking → Activate filter if yes
2. **Each transcript update** → Check each word → Interrupt if non-filler found
3. **VAD END** → If all fillers → Drop buffer, agent continues

```python
# Pseudocode
on_speech_start(agent_is_speaking):
    if agent_is_speaking:
        activate_filter()
        start_accumulating()

on_transcript_update(text):
    if filter_active:
        for word in new_words:
            if word not in FILLER_WORDS:
                return INTERRUPT  # Real word found!
        return WAIT  # All fillers, keep waiting

on_speech_end():
    if filter_active and all_fillers:
        return IGNORE  # Drop buffer, agent continues
```

## 📁 File Structure

```
livekit-agents/livekit/agents/voice/
├── __init__.py                 # Updated exports
├── interruption_filter.py      # NEW: Core filter logic
├── agent_activity.py           # Modified: Integration
└── agent_session.py            # Modified: Configuration

livekit-agents/tests/
└── test_interruption_filter.py # NEW: Comprehensive tests
```

## 🔌 Integration Points

The filter integrates at three existing hooks in `agent_activity.py`:

| Hook | Filter Method | Purpose |
|------|---------------|---------|
| `on_start_of_speech()` | `filter.on_speech_start()` | Activate/deactivate filter |
| `on_interim_transcript()` | `filter.on_transcript_update()` | Check each word |
| `on_end_of_speech()` | `filter.on_speech_end()` | Final decision |

## ⚡ Performance

| Metric | Value |
|--------|-------|
| Lookup Time | O(1) - Set membership check |
| Memory | ~1KB for default filler words |
| Latency Added | < 0.001ms per word |

The filter adds **imperceptible latency** because:
- No external API calls
- No ML inference
- Simple Python set lookup

## 🎨 Design Decisions

### Why Accumulation-Based?

Other approaches check once at VAD trigger. Our approach:
- **Buffers** the entire speech segment
- **Checks each word** as it arrives
- **Interrupts immediately** when non-filler found
- **Drops buffer** if user stops and all were fillers

This handles the "yeah but wait" case correctly.

### Why Context-Aware?

The same word ("yeah") should behave differently:
- **Agent speaking**: Ignore it (passive acknowledgment)
- **Agent silent**: Process it (valid response)

We achieve this by checking `agent_is_speaking` before activating the filter.

### Why No VAD Modification?

The assignment explicitly states: *"Do not rewrite the low-level VAD kernel."*

Our solution is a **logic layer** integrated at the event loop level, not VAD changes.

## 🔄 What Makes This Different?

Compared to other implementations:

| Approach | Check Point | Problem |
|----------|-------------|---------|
| **One-time check** | At VAD trigger | Might only see "yeah" when user says "yeah but wait" |
| **Final transcript only** | When STT finalizes | Too late, agent already paused/interrupted |
| **Our approach** | Every word, continuously | Catches "but" the moment it arrives |

## 📞 Support

For questions or issues, please refer to the [LiveKit documentation](https://docs.livekit.io/) or open an issue in the repository.

---

**Made for Salescode.ai Interview Assignment** | Filler Word Interruption Detection
