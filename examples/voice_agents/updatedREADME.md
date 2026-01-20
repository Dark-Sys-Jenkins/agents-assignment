# Intelligent Interruption Handling for LiveKit Voice Agents

## 📋 Project Overview

This project implements an intelligent interruption handling system for LiveKit voice agents that distinguishes between **passive acknowledgments** (backchanneling) and **active interruptions** based on conversational context.

### The Problem

In default LiveKit configurations, Voice Activity Detection (VAD) is overly sensitive to user feedback. When users say "yeah," "ok," or "hmm" while the agent is speaking (a natural conversational behavior called **backchanneling**), the agent incorrectly interprets this as an interruption and stops mid-sentence.

### The Solution

This implementation adds a **context-aware logic layer** that filters speech-to-text events before they trigger interruptions. The agent now:
- ✅ **Continues speaking** when users say backchannel words like "yeah" or "ok"
- ✅ **Stops immediately** when users say command words like "stop" or "wait"
- ✅ **Responds normally** to "yeah" when the agent is silent (e.g., answering a question)

---

## 🎯 Key Features

### 1. **Configurable Ignore List**
Pre-defined sets of words that are treated differently:

```python
IGNORE_WORDS = {"yeah", "ok", "hmm", "uh-huh", "right", ...}  # Backchanneling
STOP_WORDS = {"stop", "wait", "no", "pause", ...}            # Commands
```

### 2. **State-Based Filtering**
Filtering logic only applies when the agent is actively speaking:
- **Agent speaking** + User says "yeah" → Ignored completely
- **Agent silent** + User says "yeah" → Processed as valid input

### 3. **Semantic Interruption**
Mixed sentences containing commands always interrupt:
- "Yeah wait a second" → Contains "wait" → Agent stops immediately

### 4. **No VAD Modification**
Implementation works as a logic layer on top of existing VAD, without modifying the low-level Voice Activity Detection kernel.

---

## 🏗️ Architecture & Implementation

### Core Logic Flow

```
User Speech
    ↓
Voice Activity Detection (VAD) - Detects speech/silence
    ↓
Speech-to-Text (STT) - Transcribes audio
    ↓
[FILTERING LAYER] ← Our Implementation
    ↓
    ├─→ Agent Speaking? 
    │      ├─→ Pure backchannel? → DROP (ignore completely)
    │      └─→ Contains command? → PASS (interrupt agent)
    │
    └─→ Agent Silent? → PASS (process as normal input)
    ↓
Agent Response / Interruption Handler
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10 or higher
- LiveKit account with API credentials
- OpenAI API key

### 1. Clone the Repository
```bash
git clone https://github.com/Dark-Sys-Jenkins/agents-assignment.git
cd agents-assignment/examples/voice_agents
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the `voice_agents` directory:

```env
# LiveKit Credentials
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key
```

**Note**: You can also export these as environment variables(preferred):
```bash
export LIVEKIT_URL="wss://your-project.livekit.cloud"
export LIVEKIT_API_KEY="your_api_key"
export LIVEKIT_API_SECRET="your_api_secret"
export OPENAI_API_KEY="your_openai_api_key"
```

---

## 🎮 Running the Agent

### Development Mode (Local Testing)
```bash
python basic_agent.py dev
```

This starts the agent in development mode with:
- File watching enabled (auto-reload on code changes)
- Debug logging
- Local HTTP server on a random port

### Connect to the Agent

1. Open the **LiveKit Agents Playground**: https://agents-playground.livekit.io/
2. Enter your LiveKit credentials (URL, API Key, API Secret)
3. Click "Connect" to join the room
4. The agent will automatically initialize and greet you

---

## 🧪 Testing the Implementation

### Test Case 1: Backchannel While Speaking
**Scenario**: Agent is explaining something and user provides passive feedback

```
Agent: "I will count to twenty. One, two, three, four, five..."
User: "yeah"  ← Said while agent is counting
Result: ✅ Agent continues: "...six, seven, eight..."
```

**Expected Logs**:
```
🛡️  COMPLETELY IGNORING: 'yeah' (agent speaking=True)
```

---

### Test Case 2: Valid Answer When Silent
**Scenario**: Agent asks a question and waits for response

```
Agent: "Should I continue with another test?"
User: "yeah"  ← Said after agent finishes
Result: ✅ Agent processes: "Great! Let me continue..."
```

**Expected Logs**:
```
✅ PASSING transcript: 'yeah' (agent speaking=False)
✉️  User speech COMMITTED to conversation: 'yeah'
```

---

### Test Case 3: Immediate Stop Command
**Scenario**: User wants to interrupt with a command

```
Agent: "One, two, three, four..."
User: "stop"  ← Said while agent is counting
Result: ✅ Agent stops immediately
```

**Expected Logs**:
```
🔍 Contains stop word - NOT filtering
✅ PASSING transcript: 'stop' (agent speaking=True)
```

---

### Test Case 4: Mixed Sentence with Command
**Scenario**: User acknowledges but also wants to interrupt

```
Agent: "One, two, three, four..."
User: "yeah wait a second"  ← Contains command word
Result: ✅ Agent stops (because "wait" is a command)
```

**Expected Logs**:
```
🔍 Contains stop word - NOT filtering
✅ PASSING transcript: 'yeah wait a second' (agent speaking=True)
```

---

### Modified File: `basic_agent.py`

**Key Sections**:

1. **Configuration (Lines 15-28)**
   ```python
   IGNORE_WORDS = {...}  # Backchannel words
   STOP_WORDS = {...}    # Command words
   ```

2. **IntelligentAgent Class (Lines 31-276)**
   - `on_enter()`: Initial greeting and test scenario
   - `stt_node()`: STT pipeline override
   - `_filter_stt_events()`: Event filtering logic
   - `_should_filter_transcript()`: Decision logic

3. **Session Setup (Lines 287-327)**
   - Agent state tracking
   - Session configuration
   - Event handlers

---

## 🔧 Configuration Options

### Customizing Backchannel Words

Edit the `IGNORE_WORDS` set in `basic_agent.py` (lines 16-27):

```python
IGNORE_WORDS = {
    "yeah", "yep", "yes",      # Add your words here
    "uh-huh", "uhhuh",         # Include variations
    "custom-word",             # Any custom backchannel
}
```

**Important**: Include all variations of hyphenated words:
- "uh-huh" → Add: "uh-huh", "uhhuh", "uh", "huh"
- "got it" → Add: "got", "it", "gotit"

### Customizing Command Words

Edit the `STOP_WORDS` set in `basic_agent.py` (lines 30-32):

```python
STOP_WORDS = {
    "stop", "wait", "pause",   # Default commands
    "interrupt",               # Add custom commands
}
```

### Session Parameters

Adjust in `AgentSession` configuration (lines 291-304):

```python
session = AgentSession(
    min_interruption_words=1,      # Min words before interruption
    min_interruption_duration=0.2,  # Min speech duration (seconds)
    # ... other parameters
)
```

---

## 📊 How It Works: Technical Deep Dive

### The Challenge: VAD Timing Issue

**Problem**: VAD (Voice Activity Detection) triggers **before** STT (Speech-to-Text) completes transcription.

```
Timeline:
0ms:   User starts saying "yeah"
50ms:  VAD detects voice activity → Signals interruption
200ms: STT completes → Returns "yeah"
```

By the time we know it's "yeah", the interruption signal has already been sent!

### The Solution: STT Event Interception

Instead of trying to "cancel" interruptions after they happen, we **prevent them from being triggered** in the first place:

1. **Override `stt_node()`** to intercept the STT event stream
2. **Filter events** before they reach the interruption handler
3. **Drop** backchannel events completely when agent is speaking

```python
# Normal flow (without our implementation):
STT Event → Interruption Handler → Agent Stops

# Our flow (with filtering):
STT Event → Filter (DROP if backchannel) → ∅ (nothing happens)
STT Event → Filter (PASS if command) → Interruption Handler → Agent Stops
```

### Why This Approach Works

✅ **No pauses or hiccups**: Filtered events never reach the agent
✅ **Real-time decision making**: Filtering happens as events stream in
✅ **State-aware**: Different behavior when speaking vs. silent
✅ **Semantic understanding**: Analyzes full transcript, not just individual words

---

## 📝 Assignment Requirements Checklist

- ✅ **Configurable Ignore List**: `IGNORE_WORDS` and `STOP_WORDS` sets
- ✅ **State-Based Filtering**: Only filters when `is_speaking == True`
- ✅ **Semantic Interruption**: Checks for command words in mixed sentences
- ✅ **No VAD Modification**: Logic layer implemented at STT event level
- ✅ **Seamless Continuation**: No pauses or stutters on backchannel words
- ✅ **Context-Aware Response**: Processes "yeah" as valid input when silent

---