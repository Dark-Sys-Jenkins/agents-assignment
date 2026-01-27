# LiveKit Interruption Handling: complete workflow and implementation details

## Initial Setup

### 1: Sync Dependencies
```bash
clone the repo
cd agents-assignment
uv sync --dev
```

- **gives error**: `bithuman` package causes compatibility issues.

- **solution**: disable it in `pyproject.toml` (root directory)


### 2: Activate Virtual Environment
```bash
.venv\Scripts\activate
```
- **error**: threading error occurs on Windows.
- **solution**: Fix in `livekit-agents/livekit/agents/ipc/supervised_proc.py`:

### Step 3: Enviroment Variables
```bash
# create .env file inside examples/ directory
OPENAI_API_KEY= 
DEEPGRAM_API_KEY =
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

### Step 4: Run the basic agent
```bash
uv run examples/voice_agents/basic_agent.py console
```
Agent starts and listens for input.

---

### The Problem

When we run the basic_agent.py and the agent is speaking a long response:
```
Agent: "The weather today is sunny, with temperatures around..."

User: "yeah"    ← User provides passive feedback (backchanneling)

Result: Agent STOPS SPEAKING mid-sentence
```

### Why This Occurs

**Problem Flow:**

1. **VAD (Voice Activity Detection) Triggers Fast**
   - VAD detects ANY sound from the user in <50ms
   - It doesn't wait for complete transcription

2. **Agent Stops Immediately**
   - Without intelligent filtering, the agent stops as soon as VAD detects sound
   - This happens BEFORE STT (Speech-To-Text) understands what the user said

3. **User Just Said "Yeah"**
   - But it's too late - agent already stopped
   - Agent treats "yeah" as an interruption instead of acknowledgement

### The Core Issue

LiveKit's interruption logic is **state-blind**:
- It sees: *"User made a sound"*
- It does: *"Stop the agent immediately"*
- It ignores: *"What is the user actually saying?"*

Need **context-aware interruption logic** that:
- Checks WHAT the user said (via STT)
- Decides if it's passive (ignore) or active (interrupt)
- Only interrupts for explicit commands

---

## The Solution

### Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                     USER SPEAKS                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Component 1: VAD (Voice Activity Detection)                    │
│  - Detects speech activity in <100ms                            │
│  - Extremely sensitive by default                               │
│  - Can't tell backchanneling from interruptions                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Component 2: STT (Speech-to-Text)                              │
│  - Transcribes audio: "yeah" or "stop" or "yeah wait"           │
│  - Provides actual text content                                 │
│  - Takes 100-300ms depending on speech length                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Component 3: interruption_handler.py                           │
│  - Analyzes the transcribed text                                │
│  - Checks: is agent currently speaking?                         │
│  - Decides: backchanneling or real interruption?                │
│  - Decision time: <1ms (just string comparisons)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              Yes, ignore          No, proceed
           (backchanneling)      (real interruption)
                    │                   │
                    ↓                   ↓
         Agent continues      Agent stops & listens
```
---

## Implementation Details

### 1. Create `interruption_handler.py`

dir: `livekit-agents/livekit/agents/voice/interruption_handler.py`

**What It Does**:
- Defines lists of backchanneling words ("yeah", "ok", "hmm")
- Defines lists of interruption commands ("stop", "wait", "pause")
- Provides functions to classify user input

---

### 2: Modify `agent_activity.py`

dir: `livekit-agents/livekit/agents/voice/agent_activity.py`

**Why This Works**:
- Checks if agent is currently speaking (`self._current_speech is not None`)
- Gets the STT transcript (`ev.alternatives[0].text`)
- If it's backchanneling, returns early (NO interrupt)
- If it's a command, continues and interrupts normally

---

### 3: Configure `basic_agent.py`

dir: `examples/voice_agents/basic_agent.py`

#### `preemptive_generation=False`
- Agent waits for user to fully finish (end-of-turn detected)
- With `False`, we have a clearer state (agent speaking or not speaking)

#### `min_interruption_words=2`

- Commands typically need at least 2 words
- This threshold prevents accidental interruption from noise or single words
- Gives STT time to get better transcript

#### `min_interruption_duration=0.5`
- Prevents fast sounds (coughs, filler "uh") from triggering interruption
- Backchanneling ("yeah") typically takes <0.3 seconds
- Allows STT to gather more context for accurate transcription

---

### Complete Workflow

1. Setup → `uv sync --dev`

2. `.venv\Scripts\activate`

3. run `basic_agent.py`, say "yeah", see it stop

4. add interruption_handler.py with logic

5. modify agent_activity.py to use the logic

6. set optimal parameters in basic_agent.py

7. run modified basic_agent `uv run examples/voice_agents/basic_agent.py console`

---
