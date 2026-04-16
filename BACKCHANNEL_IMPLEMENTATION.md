# Backchannel Filtering Implementation

## Overview

This implementation adds **context-aware backchannel filtering** to the LiveKit Agents framework. It allows AI voice agents to distinguish between **passive acknowledgements** (backchanneling) and **active interruptions**, enabling seamless conversations where the agent doesn't abruptly stop when users say "yeah," "ok," or "hmm" to indicate they're listening.

## The Problem

Without backchannel filtering:
- User says "yeah" while agent is explaining something important
- VAD (Voice Activity Detection) detects user speech immediately
- Agent interprets ANY user speech as an interruption
- Agent stops speaking mid-sentence

This breaks the conversational flow and creates a poor user experience.

## The Solution

A **two-phase interruption handling** system:

```
Phase 1 (Immediate - VAD fires):
  └─→ Mark backchannel evaluation as pending
  └─→ Start STT settling timer (~300ms)
  └─→ Audio continues WITHOUT pausing (no hiccup!)

Phase 2 (After delay - STT ready):
  └─→ Get transcript from STT
  └─→ Classify: backchannel vs. real interruption
  └─→ If backchannel: ignore, agent continues
  └─→ If real interruption: interrupt now
```

## Challenges and Problem Solving Logic

During the implementation of the backchannel filter, several core challenges arose. Here is a breakdown of the logic used to overcome them:

**1. The "False Start" Interruption (STT vs. VAD Latency)**
**Challenge:** Voice Activity Detection (VAD) triggers almost instantaneously upon detecting user audio, whereas Speech-to-Text (STT) requires a few hundred milliseconds to start producing readable words. If we rely strictly on VAD, the agent shuts down before we even know *what* the user said.
**Logic/Solution:** Implementing a "Delayed STT Settling Timer". By delaying the immediate stop function trigger by ~300ms, we queue the VAD event wait-state, and let STT gather the partial transcript. If the transcript strictly matches a soft/filler input ("yeah", "okay"), the agent never halts audio playout. 

**2. State-Aware Context Matching**
**Challenge:** A word acting as a backchannel when the agent is speaking (e.g., "Yeah") acts as a legitimate user response when the agent is waiting (e.g., "Are you there?" -> "Yeah"). The system could not use a basic global blocklist.
**Logic/Solution:** Incorporating cross-referencing against the agent's playback state. The filter evaluates `agent_is_speaking`. If the agent is silent, the logic immediately forces a "respond" route, allowing the backchannel word to act as standard prompt input.

**3. Mixed Input & Semantic Precedence**
**Challenge:** Users rarely speak perfectly. An utterance like "Yeah... wait I have a question" starts with a filler but holds an interruptive command. A naive counting filter or basic `.startswith()` string check would fail here.
**Logic/Solution:** A prioritization structure. The code parses the entire STT chunk using an `interruption_commands` regex set. If any high-priority command (like "wait" or "stop") exists in the text string, it overrides the backchannel logic, forcing an immediate 'interrupt' mode. 

**4. Achieving Real-Time Low Latency**
**Challenge:** Deep NLP approaches to text validation introduce imperceptible but notable delay.
**Logic/Solution:** Using optimized Regular Expression patterns to find keyword bounds (`\b`) mapped at object initialization. This reduces the check cost to O(1) string operations rather than API calls.

### Bugs Discovered & Fixed During Testing

During verification and integration testing, three critical bugs were uncovered and resolved:

**Bug 1: `split_words()` Tuple Return Type Mismatch**
**Symptom:** `AttributeError: 'tuple' object has no attribute 'strip'` when processing multi-word inputs.
**Root Cause:** The `is_backchannel()` method called `split_words(text, split_character=True)` from the framework's tokenizer, which returns `list[tuple[str, int, int]]` (word, start_offset, end_offset). The code treated each element as a plain string (`w.strip(".,!?")`) instead of extracting the word via `w[0]`.
**Fix:** Replaced the `split_words()` tokenizer approach entirely with a pure-regex strategy: `re.findall(r"\b\w+\b", remaining)`. This extracts plain word strings directly and avoids the tuple mismatch. The unused `split_words` import was also removed.

**Bug 2: Empty-Set Regex Pattern Matching Everything**
**Symptom:** `test_custom_backchannel_words` and `test_custom_interruption_commands` failed — custom configs with `interruption_commands=set()` caused *every* input to be classified as an interruption.
**Root Cause:** `_build_pattern(set())` produced the regex `\b()\b`, which matches zero-width positions at word boundaries. `re.findall()` returned empty-string matches, so `has_interruption_command()` always returned `True`.
**Fix:** Added an early return in `_build_pattern()` for empty sets: `return re.compile(r"(?!x)x", re.IGNORECASE)` — a pattern that can never match any string.

**Bug 3: Multi-Word & Hyphenated Backchannels Not Detected**
**Symptom:** Repeated backchannels like `"yeah yeah yeah"`, `"uh-huh mm-hmm"` were incorrectly triggering interruptions instead of being ignored.
**Root Cause:** The original `is_backchannel()` logic first checked if the *entire* text matched a *single* backchannel phrase via regex normalization. For multi-phrase inputs like `"uh-huh mm-hmm"`, the normalized text `"uhhuhmmhmm"` didn't equal any single match like `"uhhuh"`, so it fell through to the broken `split_words` path. With `split_character=True`, hyphens were split, producing tokens like `["uh", "huh", "mm", "hmm"]` — none of which are in `backchannel_words`.
**Fix:** Rewrote `is_backchannel()` using a **subtraction approach**: strip *all* matched backchannel phrases from the text using `self._backchannel_pattern.sub("", text)`, then count remaining meaningful words with `re.findall(r"\b\w+\b", remaining)`. If nothing meaningful remains, it's purely backchannel.

**Bug 4: Word Count Collapse During Threshold Check**
**Symptom:** `test_min_words_for_interruption` failed — `"hello world"` (2 words, threshold=2) was wrongly ignored.
**Root Cause:** In an intermediate fix, whitespace was stripped (`re.sub(r"[\s.,!?;:]+", "", remaining)`) *before* counting words, which merged `"hello world"` into `"helloworld"` (1 word), falling below the threshold.
**Fix:** Moved word counting (`re.findall(r"\b\w+\b", remaining)`) to happen directly on the backchannel-stripped text, before any whitespace removal.

### Updated `is_backchannel()` Logic (Post-Fix)

The corrected algorithm follows this flow:

```
Input: "uh-huh mm-hmm"
    ↓
1. Lowercase + strip → "uh-huh mm-hmm"
    ↓
2. Check interruption commands → None found
    ↓
3. Strip backchannel phrases via regex → "" (both removed)
    ↓
4. Count remaining words → 0
    ↓
5. 0 words remaining → is_backchannel = True → IGNORE
```

```python
def is_backchannel(self, text: str) -> bool:
    text_lower = text.lower().strip()
    if not text_lower:
        return False
    if self.has_interruption_command(text):
        return False

    # Strip all matched backchannel phrases
    remaining = self._backchannel_pattern.sub("", text_lower)
    remaining_words = re.findall(r"\b\w+\b", remaining)

    if not remaining_words:
        return True  # Pure backchannel

    return len(remaining_words) < self.config.min_words_for_interruption
```

### Environment Fix: OpenTelemetry Dependency

The venv shipped with `opentelemetry-sdk==1.39.1`, which removed the `LogData` export from `opentelemetry.sdk._logs`. The framework's `telemetry/traces.py` imports `LogData`, causing `ImportError` on any `livekit.agents` import.

**Fix:** Downgraded to compatible versions:
```bash
pip install opentelemetry-sdk==1.34.1 opentelemetry-api==1.34.1 \
    opentelemetry-exporter-otlp-proto-http==1.34.1 \
    opentelemetry-exporter-otlp-proto-grpc==1.34.1 \
    opentelemetry-semantic-conventions==0.55b1
```

## Architecture

### Files Modified

| File | Changes |
|------|---------|
| `livekit-agents/.../voice/backchannel.py` | Core filtering logic with `BackchannelConfig` and `BackchannelFilter` |
| `livekit-agents/.../voice/agent_session.py` | Added `backchannel_config` parameter to `AgentSession` |
| `livekit-agents/.../voice/agent_activity.py` | Two-phase interrupt handling in `_interrupt_by_audio_activity()` |

### Key Components

#### 1. `BackchannelConfig` (Configuration)

```python
from livekit.agents.voice.backchannel import BackchannelConfig

config = BackchannelConfig(
    enabled=True,                          # Enable/disable filtering
    backchannel_words={"yeah", "ok", "hmm"},  # Words to ignore during speech
    interruption_commands={"wait", "stop"},   # Words that always interrupt
    min_words_for_interruption=1,          # Min non-backchannel words to interrupt
    check_semantic_interruption=True,      # Detect mixed inputs like "yeah but wait"
    stt_settling_delay_ms=300,             # Delay to wait for STT (ms)
)
```

#### 2. `BackchannelFilter` (Classification)

```python
from livekit.agents.voice.backchannel import BackchannelFilter

filter = BackchannelFilter(config)
decision = filter.should_interrupt(
    text="yeah",
    agent_is_speaking=True
)
# Returns: "ignore", "interrupt", or "respond"
```

#### 3. Decision Matrix

| User Input | Agent State | Decision | Behavior |
|------------|-------------|----------|----------|
| "yeah" | Speaking | **ignore** | Agent continues without pause |
| "yeah" | Silent | **respond** | Agent treats as valid input |
| "wait" | Speaking | **interrupt** | Agent stops immediately |
| "yeah but wait" | Speaking | **interrupt** | Mixed input → interrupt |

## Usage

### Basic Example

```python
from livekit.agents import Agent, AgentSession
from livekit.agents.voice.backchannel import BackchannelConfig

class MyAgent(Agent):
    async def on_enter(self):
        # Long explanation - won't be interrupted by "yeah", "ok", etc.
        await self.say(
            "The history of computing spans many decades. "
            "First, there were mechanical calculators in the 1800s..."
        )

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=elevenlabs.TTS(),
        # Enable backchannel filtering (enabled by default)
        backchannel_config=BackchannelConfig(
            stt_settling_delay_ms=300,  # Adjust based on your STT speed
        )
    )
    await session.start(agent=MyAgent())
```

### Advanced Configuration

```python
# Custom word lists for specific use cases
config = BackchannelConfig(
    # Add domain-specific backchannel words
    backchannel_words={
        "yeah", "yes", "ok", "okay", "hmm", "right",
        "got it", "i see", "uh-huh", "mhm",
        # Medical domain example:
        "understood", "continue", "go on",
    },
    # Add domain-specific interruption commands
    interruption_commands={
        "wait", "stop", "no", "hold on", "pause",
        # Medical domain example:
        "doctor", "nurse", "emergency", "help",
    },
    # Slower STT provider → increase delay
    stt_settling_delay_ms=500,
)

session = AgentSession(
    # ... other config ...
    backchannel_config=config,
)
```

## How It Works

### Two-Phase Interruption Handling

**Before (problematic):**
```
User says "yeah"
    ↓
VAD detects speech (immediate)
    ↓
Agent interrupts immediately ← PROBLEM: Stops mid-sentence!
```

**After (fixed):**
```
User says "yeah"
    ↓
VAD detects speech (immediate)
    ↓
Backchannel evaluation starts
    ↓
Wait 300ms for STT transcript
    ↓
Transcript = "yeah"
    ↓
Classify as backchannel → IGNORE
    ↓
Agent continues speaking seamlessly ✓
```

### Key Code Flow

```
livekit-agents/voice/agent_activity.py:

1. on_vad_inference_done() → _interrupt_by_audio_activity()
   - VAD detects user speech

2. _interrupt_by_audio_activity()
   - Creates _pending_interrupt_task
   - Task will evaluate after STT settling delay

3. _delayed_interrupt_check() [after ~300ms]
   - Gets transcript from _audio_recognition
   - Calls _backchannel_filter.should_interrupt()
   - Returns: "ignore" (continue) or "interrupt" (stop)
```

## Testing

### Run Verification Script

```bash
python verify_backchannel.py
```

This runs:
1. Import verification
2. Filter logic tests
3. Scenario tests (all 4 required scenarios)
4. Configuration tests

### Run Integration Tests

```bash
# Using pytest
pytest tests/test_backchannel_integration.py -v

# With coverage
pytest tests/test_backchannel_integration.py --cov=backchannel -v
```

### Manual Testing

Create a test agent and run it:

```python
# examples/voice_agents/backchannel_demo.py
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.voice.backchannel import BackchannelConfig
from livekit.plugins import openai, deepgram, elevenlabs

class BackchannelDemoAgent(Agent):
    async def on_enter(self):
        await self.say(
            "Let me explain the history of computing. "
            "First, there were mechanical calculators in the 1800s. "
            "Then came vacuum tubes in the 1940s. "
            "Transistors arrived in the 1950s. "
            "Integrated circuits followed in the 1960s. "
            "Say 'wait' if you want me to stop.",
            allow_interruptions=True
        )

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=elevenlabs.TTS(),
        backchannel_config=BackchannelConfig(
            enabled=True,
            stt_settling_delay_ms=300,
        )
    )
    await session.start(agent=BackchannelDemoAgent())

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

```bash
python examples/voice_agents/backchannel_demo.py dev
```

**Test scenarios:**
1. Say "yeah" while agent talks → Agent should NOT stop
2. Say "wait" while agent talks → Agent SHOULD stop
3. Say "yeah" after agent finishes → Agent should respond

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `True` | Enable/disable backchannel filtering |
| `backchannel_words` | set[str] | 19 words | Words to ignore during agent speech |
| `interruption_commands` | set[str] | 20 commands | Words that always interrupt |
| `min_words_for_interruption` | int | `1` | Min non-backchannel words to interrupt |
| `check_semantic_interruption` | bool | `True` | Detect mixed inputs |
| `stt_settling_delay_ms` | int | `300` | Delay to wait for STT (ms) |

### Tuning `stt_settling_delay_ms`

This is the most important parameter for your specific setup:

| STT Provider | Recommended Delay |
|--------------|-------------------|
| Deepgram (streaming) | 200-300ms |
| Google Cloud STT | 300-400ms |
| AWS Transcribe | 300-500ms |
| Azure Speech | 300-400ms |
| Slow providers | 500-700ms |

**Too low:** Backchannel words may not be fully transcribed → false interrupts

**Too high:** Real interruptions have more latency → less responsive

## Default Word Lists

### Backchannel Words (ignored during speech)

```
yeah, yes, ok, okay, hmm, hm, right, uh-huh, uh huh,
mhm, aha, sure, got it, i see, yep, yup, mm-hmm, mm hmm
```

### Interruption Commands (always interrupt)

```
wait, stop, no, hold on, hang on, pause, slow down,
not yet, let me, can i, could i, i want, i need,
actually, sorry, excuse me, hey, hello, start, begin
```

## Troubleshooting

### Agent still interrupts on "yeah"

**Possible causes:**
1. `stt_settling_delay_ms` too low → Increase to 400-500ms
2. STT not producing transcripts → Check STT connection
3. Backchannel filtering disabled → Verify `enabled=True`

```python
# Debug: log the decision
import logging
logging.getLogger("livekit.agents.voice.agent_activity").setLevel(logging.DEBUG)
```

### Agent doesn't interrupt on "wait"

**Possible causes:**
1. `interruption_commands` missing the word → Add to set
2. `allow_interruptions=False` on speech → Check speech settings

### Agent has slight pause/hiccup on backchannel

**Cause:** Audio pause/resume happening before classification

**Fix:** The current implementation keeps audio playing during evaluation. If you still hear hiccups, ensure your audio output supports pause/resume:

```python
# Check if audio output supports pause
if session.output.audio and session.output.audio.can_pause:
    # Good - can pause/resume seamlessly
else:
    # Consider using an audio output that supports pause
```

## Performance Impact

- **Latency:** Real interruptions delayed by `stt_settling_delay_ms` (~300ms)
- **CPU:** Minimal - regex matching on short strings
- **Memory:** Minimal - small config dataclass

## Future Improvements

1. **Adaptive delay:** Adjust `stt_settling_delay_ms` based on observed STT speed
2. **Confidence scoring:** Use STT confidence to weight interrupt decisions
3. **Multi-language:** Support backchannel words in different languages
4. **ML-based classification:** Train a classifier for more nuanced detection

## References

- [Conversation Analysis: Backchanneling](https://en.wikipedia.org/wiki/Back-channel_(linguistics))
- LiveKit Agents Documentation: https://docs.livekit.io/agents/
