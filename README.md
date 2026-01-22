<!--BEGIN_BANNER_IMAGE-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/.github/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/.github/banner_light.png">
  <img style="width:100%;" alt="The LiveKit icon, the name of the repository and some sample code in the background." src="https://raw.githubusercontent.com/livekit/agents/main/.github/banner_light.png">
</picture>

<!--END_BANNER_IMAGE-->
<br />

![PyPI - Version](https://img.shields.io/pypi/v/livekit-agents)
[![PyPI Downloads](https://static.pepy.tech/badge/livekit-agents/month)](https://pepy.tech/projects/livekit-agents)
[![Slack community](https://img.shields.io/endpoint?url=https%3A%2F%2Flivekit.io%2Fbadges%2Fslack)](https://livekit.io/join-slack)
[![License](https://img.shields.io/github/license/livekit/livekit)](https://github.com/livekit/livekit/blob/master/LICENSE)

<br />

## What is Agents?

The Agent Framework is designed for building realtime, programmable participants that run on servers. Use it to create conversational, multi-modal voice agents that can see, hear, and understand.

## Installation

This repository uses `uv` for dependency management. Install dependencies with:

```bash
cd agents-assignment

# Install uv (one-time, macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates .venv/)
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

## Environment Setup

Create a `.env` file in the project root with your API keys:

```bash
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Required for dev mode
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Optional: Customize interruption handling word lists
# Note: Only single words are supported (not phrases). The system processes words individually.
BACKCHANNELING_WORDS=yeah,yep,yup,ok,okay,okey,alright,sure,right,uh-huh,mhm,mm-hmm,mm,mmm,aha,ah,oh,hmm,hmmm,gotcha,understood,correct,exactly,absolutely,definitely,indeed,true
INTERRUPT_WORDS=stop,wait,no,hold,pause,cancel,halt,cease
```

## Running the Agent

### Console Mode (Recommended for Testing)

Test the agent locally with terminal audio:

```bash
cd examples/voice_agents
python test_interrupt_handler.py console
```

Or use the basic agent:

```bash
python basic_agent.py console
```


## Intelligent Interruption Handling

This implementation adds a logic layer to distinguish between **passive acknowledgements** (backchanneling) and **active interruptions** (commands) based on whether the agent is currently speaking or silent.

### Problem Statement

- **VAD (Voice Activity Detection)** is fast (~50ms) and detects speech immediately
- **STT (Speech-to-Text)** is slower (~200-500ms) but provides semantic content
- When a user says "yeah" or "ok" while the agent is speaking, VAD triggers an interruption before STT can identify it as backchanneling
- This causes unwanted pauses, stutters, or stops in agent speech

### Solution Architecture

The solution implements **three-layer filtering** to prevent false interruptions:

#### Layer 1: Interruption Gate (`_interrupt_by_audio_activity()`)

**Location:** `livekit/agents/voice/agent_activity.py`

- **When:** Both VAD and STT events route through this function
- **Logic:** 
  - If agent is speaking AND transcript contains only backchanneling words → **ignore** (return early, no pause)
  - If transcript contains any interrupt word (even mixed) → **interrupt immediately**
  - Otherwise → **interrupt** (treat as real input)

**Key Code:**
```python
if self._session.agent_state == "speaking":
    if self._should_ignore_backchanneling(current_text):
        return  # No interruption, agent continues speaking
```

#### Layer 2: LLM Forwarding Prevention

**Location:** `on_interim_transcript()` and `on_final_transcript()` in `agent_activity.py`

- **When:** STT provides interim or final transcripts
- **Logic:**
  - Check if transcript is backchanneling BEFORE calling `_user_input_transcribed()`
  - If backchanneling → skip forwarding to LLM
  - **Prevents:** LLM from generating a response to "Okay" or "Yep"

**Key Code:**
```python
if self._should_ignore_backchanneling(transcript_text):
    should_forward_to_llm = False
    logger.info("User: %s [backchanneling - ignored]", transcript)
```

#### Layer 3: Conversation Context Prevention

**Location:** `audio_recognition.py` → `_on_stt_event()`

- **When:** Final transcript arrives from STT
- **Logic:**
  - Call `should_ignore_transcript()` hook BEFORE adding to `_audio_transcript`
  - If backchanneling → don't add to `_audio_transcript`
  - **Prevents:** Transcript from entering conversation context and triggering EOU detection

**Key Code:**
```python
if should_ignore:
    # Don't add to _audio_transcript
    # This prevents EOU detection from seeing it
else:
    self._audio_transcript += f" {transcript}"
```

### How It Works

1. **VAD fires first** → Calls `_interrupt_by_audio_activity()` with empty transcript
   - Empty transcript → Returns early (no pause)
   
2. **STT arrives** → Provides transcript text
   - If backchanneling → All three layers filter it out
   - If interrupt word → All layers allow interruption
   
3. **Result:**
   - Backchanneling: Agent continues speaking seamlessly
   - Commands: Agent interrupts immediately

### Semantic Filtering Logic

The `_should_ignore_backchanneling()` function:

1. **Checks for interrupt words first** (highest priority)
   - If transcript contains "stop", "wait", "no" → **don't ignore** (interrupt)
   
2. **Checks if all words are backchanneling**
   - If transcript is only "yeah", "ok", "hmm" → **ignore** (don't interrupt)
   
3. **Handles punctuation**
   - Strips punctuation: "Okay." → "okay" → matches backchanneling list
   
4. **Handles mixed input**
   - "yeah wait" → Contains interrupt word → **interrupt**
   - "yeah ok" → All backchanneling → **ignore**

### Configuration

Word lists are configurable via environment variables (comma-separated):

- `BACKCHANNELING_WORDS`: Single words to ignore when agent is speaking (default: yeah, ok, okay, hmm, etc.)
  - **Note:** Only single words are supported, not phrases. The system processes words individually.
- `INTERRUPT_WORDS`: Single words that always interrupt (default: stop, wait, no, etc.)
  - **Note:** Only single words are supported, not phrases.

## Testing

### ⚠️ Important Testing Notes

**For accurate backchanneling detection, please follow these guidelines:**

1. **Speak clearly and close to the microphone**
   - The backchanneling filter only works if STT (Speech-to-Text) can accurately transcribe your words
   - If you say "okay" but the microphone only captures "K", the backchanneling detection will fail
   - Poor audio quality or distance from the mic can result in incomplete transcriptions

2. **Monitor the STT transcript in console logs**
   - Always check the console output to see what STT actually transcribed
   - Look for: `User: <transcript>` in the logs
   - **Only the words that STT successfully transcribes will be validated for backchanneling**
   - If STT captures "K" instead of "okay", the system will not recognize it as backchanneling

3. **Example scenarios:**
   - ✅ **Good:** You say "okay" clearly → STT transcribes "okay" → Backchanneling detected → Agent continues
   - ❌ **Bad:** You say "okay" but too far from mic → STT transcribes "K" → Not recognized → Agent may pause
   - ✅ **Good:** You say "yeah" clearly → STT transcribes "yeah" → Backchanneling detected → Agent continues
   - ❌ **Bad:** You mumble "yeah" → STT transcribes "ah" → Not recognized → Agent may pause

**Tip:** If backchanneling isn't working, check the console logs first to verify what STT actually captured. The system validates backchanneling based on the **actual STT transcript**, not what you intended to say.

### Test Scenarios

1. **Backchanneling while agent speaks** ✅
   - Agent is speaking → Say "yeah" or "ok"
   - **Expected:** Agent continues without pause
   - **Check logs:** `User: yeah [backchanneling - ignored]`

2. **Real interruption** ✅
   - Agent is speaking → Say "stop" or "wait"
   - **Expected:** Agent stops immediately

3. **Mixed input** ✅
   - Agent is speaking → Say "yeah wait"
   - **Expected:** Agent stops (contains interrupt word)

4. **Backchanneling when agent is silent** ✅
   - Agent finished speaking → Say "yeah" or "ok"
   - **Expected:** Agent responds normally

### Success Indicators

- ✅ Agent continues speaking smoothly when you say "yeah/ok" while it's talking
- ✅ Agent stops immediately when you say "stop/wait" while it's talking
- ✅ No pauses, stutters, or hiccups in agent speech
- ✅ Agent responds normally to "yeah" when it's silent
- ✅ Console shows: `User: <transcript>` for all user speech

### Failure Indicators

- ❌ Agent stops or pauses when you say "yeah" while it's speaking
- ❌ Agent doesn't stop when you say "stop" while it's speaking
- ❌ Agent stutters or resumes after pausing

## Implementation Details

### Files Modified

1. **`livekit/agents/voice/agent_activity.py`**
   - Added `_get_backchanneling_words()` and `_get_interrupt_words()` methods
   - Added `_should_ignore_backchanneling()` semantic filtering logic
   - Modified `_interrupt_by_audio_activity()` to filter backchanneling
   - Modified `on_interim_transcript()` and `on_final_transcript()` to prevent LLM forwarding
   - Added `should_ignore_transcript()` hook implementation

2. **`livekit/agents/voice/audio_recognition.py`**
   - Added `should_ignore_transcript()` to `RecognitionHooks` protocol
   - Modified `_on_stt_event()` to check before adding transcript to conversation context

### Key Design Decisions

- **No VAD modification:** All logic is in the high-level `AgentActivity` class
- **State-based filtering:** Only applies when `agent_state == "speaking"`
- **Early return pattern:** Returns before any pause logic executes
- **Three-layer defense:** Prevents interruption at VAD/STT, LLM, and conversation context levels

## Examples

See `examples/voice_agents/` for:
- `test_interrupt_handler.py` - Dedicated test agent for interruption scenarios
- `basic_agent.py` - Standard voice agent example


