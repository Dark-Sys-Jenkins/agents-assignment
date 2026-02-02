# Intelligent Interruption Handling Implementation

## Overview
Context-aware interruption system for LiveKit voice agents that distinguishes between passive acknowledgments and active interruptions.

## Solution
Implements zero-pause filler word handling while maintaining instant command interruption.

**Zero-pause** means the agent's speech continues uninterrupted when filler words are detected - there is no audible pause or stutter in the agent's voice. The system processes and classifies user input in the background (< 0.1ms decision latency) without affecting the agent's ongoing speech output.

**Decision Matrix:**
| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "yeah", "ok", "hmm" | Speaking | **IGNORE** - Agent continues (zero pause) |
| "wait", "stop", "no" | Speaking | **INTERRUPT** - Agent stops immediately |
| Any input | Silent | **PROCESS** - Normal conversation |

## Implementation

### Core Components
- **`interrupt_handler/`** - Classification and decision logic
  - `config.py` - Configurable word lists
  - `handler.py` - State tracking and decision algorithm
  - `utils.py` - Text classification utilities
- **`examples/voice_agents/voice_agent_with_interruption.py`** - Main agent implementation
- **`tests/test_interruption_handler.py`** - 40 unit tests

### Key Technical Decisions
1. **Manual Turn Detection** - Set `turn_detection="manual"` and `allow_interruptions=False` to prevent VAD auto-pausing
2. **Parallel Transcript Processing** - STT runs while agent speaks without discarding audio (`discard_audio_if_uninterruptible=False`)
3. **Manual Interrupt Calls** - Only call `session.interrupt(force=True)` for real command words

### Integration with LiveKit
The handler integrates via two event listeners:

**1. Agent State Tracking:**
```python
@session.on("agent_state_changed")
def on_agent_state_changed(ev):
    if ev.new_state == "speaking":
        handler.on_agent_speech_started()
    elif ev.old_state == "speaking":
        handler.on_agent_speech_ended()
```

**2. Transcript Processing:**
```python
@session.on("user_input_transcribed")
def on_user_input(ev):
    should_interrupt = handler.should_interrupt(ev.transcript, ev.is_final)
    
    if handler.is_agent_speaking() and should_interrupt:
        session.interrupt(force=True)
    elif not handler.is_agent_speaking():
        session.commit_user_turn()
```

## Quick Start

```bash
# Install dependencies
pip install -e "livekit-agents[silero]"
pip install python-dotenv pytest

# Configure API keys
cp .env.example .env
# Edit .env with your LiveKit credentials

# Run tests
pytest tests/test_interruption_handler.py -v

# Run agent
python examples/voice_agents/voice_agent_with_interruption.py console
```

## Configuration

Customize via environment variables in `.env`:
```bash
FILLER_WORDS=yeah,ok,hmm,sure,right
INTERRUPT_WORDS=wait,stop,no,pause
INTERRUPTION_DEBUG=true
```

Or via code:
```python
from interrupt_handler import InterruptionHandler, InterruptionConfig

config = InterruptionConfig(
    filler_words={'yeah', 'ok'},
    interrupt_words={'stop', 'wait'},
    debug=True
)
handler = InterruptionHandler(config)
```

## Algorithm

```python
def should_interrupt(transcript, is_final):
    classification = classify_utterance(transcript)
    agent_speaking = is_agent_speaking()
    
    if not agent_speaking:
        return True  # Process all input when silent
    
    if classification == 'FILLER':
        return False  # Ignore - agent continues
    
    return True  # Interrupt for commands or mixed content
```

**Decision latency:** < 0.1ms

## Validation

All assignment scenarios verified:
- ✅ Long explanation - Filler words ignored (zero pause)
- ✅ Passive affirmation - "Yeah" processed when silent
- ✅ Command interruption - "Stop" causes immediate halt
- ✅ Mixed input - "Yeah but wait" interrupts correctly

## Demo Video

**Video demonstration:** [View on Google Drive](https://drive.google.com/file/d/10N3pGgeMLFbzmiTtyT-F3bs0hFKfLni9/view?usp=sharing)

The video shows all test scenarios in action, demonstrating zero-pause filler word handling and instant command interruption.

## Files Added/Modified
- New: `interrupt_handler/` package
- New: `examples/voice_agents/voice_agent_with_interruption.py`
- New: `tests/test_interruption_handler.py`
- New: `.env.example`
