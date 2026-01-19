# Smart Interruption Handler for LiveKit Agents

**Author:** Aarav Dudeja  
**Repository:** https://github.com/RedtRocks/agents-assignment  
**Branch:** feature/interrupt-handler-aaravdudeja

A sophisticated interruption handling system for LiveKit voice agents that intelligently distinguishes between passive affirmations and command interruptions, creating natural conversation flows.

## Problem Statement

Standard voice agents interrupt their speech whenever they detect user audio, even for passive listening cues like "yeah", "uh-huh", or "okay". This creates an unnatural conversation flow where the agent restarts its response after every acknowledgment, making interactions feel robotic and frustrating.

## Solution

This implementation provides a **SmartInterruptionHandler** that:

1. **Continues seamlessly** for passive words (e.g., "yeah", "okay", "uh-huh")
2. **Interrupts immediately** for command words (e.g., "stop", "wait", "pause")
3. **Interrupts normally** for substantive content (e.g., questions, statements)
4. **Processes all input normally** when the agent is silent

## Architecture

### Core Components

#### 1. `handler.py` - SmartInterruptionHandler
The main logic for classifying user input:
- **Passive words**: 29 common listening cues (yeah, okay, uhuh, right, sure, etc.)
- **Passive phrases**: 5 multi-word affirmations (i see, got it, makes sense, etc.)
- **Command words**: 28 explicit interruption commands (stop, wait, pause, hold, etc.)
- **Command phrases**: 11 multi-word interruptions (hold on, excuse me, can you, etc.)
- **Decision engine**: Returns `INTERRUPT`, `IGNORE`, or `PROCESS` based on context

Key features:
- Context-aware analysis using agent speaking state
- Support for both single words and multi-word phrases
- Efficient transcript analysis with caching
- Configurable word/phrase lists via environment variables

#### 2. `config.py` - InterruptionConfig
Configuration management for passive and command word lists:
- Default word/phrase sets optimized for natural conversation
- Environment variable support for runtime customization
- Easy programmatic API for adding/removing words
- No redundant getter functions - clean, maintainable structure

#### 3. `patch_session_v2.py` - Deep Integration
Multi-level patching system that intercepts at three stages:

- **AudioRecognition._on_stt_event**: Drops passive transcripts before processing
- **AgentActivity.on_interim_transcript**: Fast detection for early interruption
- **AgentActivity.on_final_transcript**: Final filtering before LLM processing
- **AgentActivity._interrupt_by_audio_activity**: Smart interruption decision
- **AgentActivity.on_vad_inference_done**: Prevents premature VAD-triggered interruptions

#### 4. `interruption_demo_agent.py` - Demo Agent
A working example using:
- **Free LLM**: Groq's llama-3.3-70b-versatile (20 req/min)
- **Free TTS**: Azure Text-to-Speech (500k chars/month)
- **STT**: Deepgram Nova-3
- **VAD**: Silero VAD

## How It Works

### The Challenge

LiveKit's audio pipeline processes transcripts through multiple stages:

```
User Speech → VAD → STT → AudioRecognition → AgentActivity → LLM
```

Each stage can trigger an interruption, and even if we filter at one stage, the transcript has already been processed by earlier stages, causing:
- Transcript logs showing in UI
- Audio buffer updates
- LLM receiving the transcript
- Agent restarting current sentence

### The Solution

We patch **all critical stages** to prevent passive words from propagating:

```python
# 1. AudioRecognition level - DROP before processing
async def patched_on_stt_event(ev):
    if is_passive_word(transcript) and is_agent_speaking():
        return  # Skip entirely - no logging, no buffer updates

# 2. Interim transcript - Fast detection
def patched_on_interim_transcript(ev):
    if is_passive_word(transcript):
        return  # Don't call original handler

# 3. Final transcript - Last line of defense
def patched_on_final_transcript(ev):
    if is_passive_word(transcript):
        reset_transcript_only()  # Clear buffer without resetting STT
        return

# 4. Interruption logic - Smart decision
def smart_interrupt_by_audio_activity():
    if is_passive_word(transcript):
        return  # Don't interrupt
    original_interrupt()

# 5. VAD - Prevent early trigger
def patched_on_vad_inference_done(ev):
    if is_passive_word(transcript):
        return  # Wait for STT confirmation
```

### Key Insights

1. **Multi-stage filtering**: Filtering at one stage isn't enough - we need to intercept at all stages
2. **Early detection**: Interim transcripts provide fast detection for command words
3. **State management**: Track interrupted speech IDs to avoid double interruption
4. **STT buffer management**: Clear transcript buffer without resetting STT stream (which causes audio restart)
5. **VAD coordination**: Wait for STT transcript before VAD triggers interruption

## Setup

### 1. Install Dependencies

```bash
pip install livekit-agents livekit-plugins-deepgram livekit-plugins-groq livekit-plugins-azure livekit-plugins-silero
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your API keys:

```bash
# Required
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Free services
GROQ_API_KEY=your-groq-key  # Free: 20 req/min
AZURE_SPEECH_KEY=your-azure-key  # Free: 500k chars/month
AZURE_SPEECH_REGION=your-region
DEEPGRAM_API_KEY=your-deepgram-key
```

### 3. Run Demo Agent

#### Console Mode (Voice Input)
```bash
python interruption_demo_agent.py console
```

#### Development Mode (LiveKit Playground)
```bash
python interruption_demo_agent.py dev
```

Then connect at: https://agents-playground.livekit.io/

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
python -m pytest test_handler.py -v
```

Tests cover:
- ✅ Passive words (34 variations)
- ✅ Command words (28 variations)
- ✅ Mixed input (passive + command)
- ✅ Substantive content
- ✅ Agent silent vs speaking
- ✅ Edge cases

### Manual Testing

1. Start the agent in console mode
2. While the agent is speaking:
   - Say "yeah" or "okay" → Agent continues seamlessly
   - Say "stop" or "wait" → Agent stops immediately
   - Ask a question → Agent stops and responds

## Results

### Before
```
Agent: "Let me tell you about..."
User: "yeah"
Agent: [PAUSES] "Let me tell you about..."  ← Restarts!
```

### After
```
Agent: "Let me tell you about..."
User: "yeah"
Agent: "...the benefits of this approach..."  ← Continues seamlessly!
```

### Logs Showing Success

```
DEBUG  smart-interruption-v2 INTERIM DROP: passive 'Uh-huh.'
DEBUG  smart-interruption-v2 AUDIO DROP: 'Uh-huh.' - skipped at STT level
DEBUG  smart-interruption-v2 AUDIO DROP: 'Okay.' - skipped at STT level
DEBUG  smart-interruption-v2 INTERIM DROP: passive 'Sure.'
DEBUG  smart-interruption-v2 AUDIO DROP: 'Sure.' - skipped at STT level
DEBUG  smart-interruption-v2 FAST STOP: 'stop' - interrupting
DEBUG  smart-interruption-v2 STOP: substantive content 'what time is it'
```

## Project Structure

```
smart_interruption/
├── __init__.py              # Module exports and public API
├── config.py                # Configuration for word lists
├── handler.py               # Core interruption logic
├── patch_session_v2.py      # LiveKit integration patches
├── interruption_demo_agent.py  # Demo agent implementation
├── test_handler.py          # Unit tests
├── .env.example             # Environment variable template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Configuration

### Customize Passive Words

Edit `config.py` or use environment variables:

```python
# In config.py
DEFAULT_PASSIVE_WORDS: Set[str] = {
    "yeah", "yes", "yep", "yup",
    "okay", "ok", "alright",
    "uhuh", "mhm", "mmhm", "mhmm", "hmm",
    "right", "sure", "gotcha",
    # Add your own...
}

DEFAULT_PASSIVE_PHRASES: Set[str] = {
    "i see", "got it", "makes sense",
    "mm-hmm", "uh-huh"
}

# Or use environment variables
export SMART_INTERRUPT_PASSIVE_WORDS="yeah,okay,sure,custom1,custom2"
export SMART_INTERRUPT_PASSIVE_PHRASES="i see,got it,custom phrase"
```

### Customize Command Words

```python
DEFAULT_COMMAND_WORDS: Set[str] = {
    "stop", "wait", "pause",
    "hold", "no", "nope",
    "actually", "but", "however",
    # Add your own...
}

DEFAULT_COMMAND_PHRASES: Set[str] = {
    "hold on", "hold up", "hang on",
    "one moment", "excuse me",
    "can you", "could you", "would you"
}

# Or use environment variables
export SMART_INTERRUPT_COMMAND_WORDS="stop,wait,pause,custom1"
export SMART_INTERRUPT_COMMAND_PHRASES="hold on,custom phrase"
```

### Tune Interruption Timing

Edit `interruption_demo_agent.py`:

```python
agent_session = AgentSession(
    llm=llm,
    tts=tts,
    stt=deepgram.STT(
        min_silence_duration=0.2,  # Lower = more sensitive
        min_speech_duration=0.2,   # Lower = faster detection
    ),
    min_interruption_duration=0.1,  # Minimum audio to trigger check
    resume_false_interruption=False,  # Don't auto-resume
)
```

## Technical Details

### Why Multiple Patches?

1. **AudioRecognition._on_stt_event**: Prevents transcript from being logged or added to buffer
2. **on_interim_transcript**: Provides fast detection for command words (lower latency)
3. **on_final_transcript**: Catches cases where interim wasn't triggered
4. **_interrupt_by_audio_activity**: Controls actual interruption behavior
5. **on_vad_inference_done**: Prevents VAD from triggering before we have transcript

### State Management

```python
state = {
    "interrupted_speech_id": None,      # Track current interrupted speech
    "last_command_transcript": "",      # Avoid duplicate interruptions
    "skip_checks": False,               # Optimization: skip future checks
    "last_transcript": "",              # Avoid reprocessing same text
}
```

### Performance Optimizations

- **Skip flag**: Once passive is detected, skip all future checks until transcript changes
- **Transcript caching**: Don't reprocess the same transcript multiple times
- **Speech ID tracking**: Avoid interrupting the same speech multiple times

## Limitations

- Requires access to LiveKit Agents internals (uses private methods)
- Language-specific word lists (currently English only)
- May need tuning for different accents/dialects
- Free tier API limits apply (Groq: 20 req/min, Azure: 500k chars/month)

## Code Quality

All code follows PEP8 standards and best practices:
- ✅ Proper import organization (stdlib, third-party, local)
- ✅ 2 blank lines between top-level functions/classes
- ✅ Lines wrapped to reasonable lengths
- ✅ Comprehensive docstrings
- ✅ Type hints throughout
- ✅ Standardized snake_case naming
- ✅ Error handling with None checks
- ✅ Reduced logging verbosity in hot paths
- ✅ No duplicate code or redundant functions

## Future Enhancements

- [ ] Multi-language support
- [ ] ML-based passive/command classification
- [ ] User-specific learning (adapt to individual patterns)
- [ ] Context-aware interruption (topic-based rules)
- [ ] Emotion detection integration
- [ ] Real-time configuration updates
- [ ] Analytics and metrics dashboard

## Contributing

Contributions welcome! Please ensure:

1. All tests pass:
```bash
python -m pytest test_handler.py -v
```

2. Code follows PEP8:
```bash
python -m flake8 *.py
```

3. Type hints are added for new functions

## License

Same as LiveKit Agents (Apache 2.0)

## Credits

**Author:** Aarav Dudeja  
**Built for:** LiveKit Intelligent Interruption Handling Challenge  
**Repository:** https://github.com/RedtRocks/agents-assignment

Solves the problem of distinguishing between:
- Passive listening cues (continue speaking)
- Explicit interruption commands (stop immediately)
- Substantive content (normal interruption)

## Acknowledgments

- LiveKit team for the excellent agents framework
- Community feedback for word list refinements
- Open source contributors
