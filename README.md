Here's a professional rephrasing of the README.md file:

***

# Context-Aware Interruption Logic

This agent features an intelligent interruption detection system that differentiates between passive acknowledgments (e.g., "yeah", "ok") and substantive user interruptions.

## Architecture Overview

The system employs a two-layer interruption strategy:

1. **Voice Activity Detection (VAD) Configuration**: Sets `min_interruption_duration=1000.0ms` to allow sufficient time for transcript analysis before interrupting ongoing speech.
2. **Custom Interruption Logic**: Monkey-patches `AgentActivity._interrupt_by_audio_activity()` to:
   - Filter out passive acknowledgments ("yeah", "ok", "uh-huh") during active speech
   - Allow immediate interruption for substantive inputs ("stop", "wait", "yeah but...")

## Deployment Instructions

### Prerequisites
- Ensure the virtual environment is activated

### Launch Agent
```bash
# Option 1: Direct execution from venv
./venv/bin/python examples/voice_agents/context_aware_agent.py start

# Option 2: Activate venv first
source venv/bin/activate
python examples/voice_agents/context_aware_agent.py start
```

### Client Connection
Connect via LiveKit Playground or compatible client applications.

## Test Scenarios

| User Input | Agent State | Expected Behavior |
|------------|-------------|------------------|
| "Yeah" | Speaking | Continue speaking |
| "Stop" | Speaking | Interrupt immediately |
| "Yeah wait" | Speaking | Interrupt (substantive content) |
| "Yeah" | Silent | Normal response |

## Verification Process

### Unit Test Suite (Primary Verification)
```bash
./venv/bin/python tests/test_context_logic.py
```

**Expected Result:**
```
Ran 4 tests in 0.002s
OK
```

This validates:
- Passive acknowledgment filtering
- Active interruption triggers  
- Monkey-patch integration

## Technical Implementation

### Core Requirements Mapping

**Strict Functionality (70%)**
- Custom `_should_ignore()` logic blocks interruptions for configured ignore list during active speech
- Unit test `test_ignore_logic` validates filtering behavior

**State Awareness (10%)**
- Logic activates only when `self._current_speech` is active
- Falls back to standard turn-taking when agent is silent

**Code Quality (10%)**
```
- Modular _should_ignore() function
- Configurable IGNORE_WORDS via environment variable
- Clean monkey-patch injection
```

**Documentation (10%)**
- Comprehensive deployment and verification instructions
- Clear architecture explanation

## Configuration Options

### Custom Ignore List
Override default ignore words via environment variable:

```bash
export IGNORE_WORDS="yeah,ok,uh-huh,right,gotcha"
python examples/voice_agents/context_aware_agent.py start
```

The system maintains default values `["yeah", "ok", "uh-huh", "right", "got it"]` when no override is specified.

***