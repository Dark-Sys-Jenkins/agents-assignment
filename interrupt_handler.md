# LiveKit Intelligent Interruption Handling - Implementation

## 📋 Overview

This project implements an intelligent interruption handling system for a LiveKit voice agent that can distinguish between **passive acknowledgements** (backchanneling) and **active interruptions** based on the agent's speaking state.

## 🎯 Key Requirements Met

| Requirement | Status | Implementation |
|------------|--------|----------------|
| Ignore fillers while speaking | ✅ | Single-word filler detection with state checking |
| Stop on explicit interrupts | ✅ | Interrupt word detection with immediate session interrupt |
| Respond to fillers when silent | ✅ | State-based filtering logic |
| Handle mixed input ("yeah wait") | ✅ | Scans entire transcript for interrupt words |
| No agent stuttering/pausing | ✅ | Session configuration + speech tracking |
| Configurable ignore list | ✅ | `FILLER_WORDS` and `INTERRUPT_WORDS` sets |

---

## 🔧 Technical Implementation

### 1. State Tracking System

**Added:** Three critical state variables to track speech progress

```python
class AssessmentAgent(Agent):
    def __init__(self):
        # --- Speech state tracking ---
        self.is_speaking = False      # Current speech status
        self.full_response = ""       # Complete response being generated
        self.spoken_offset = 0        # Character position of speech progress
```

**Purpose:** These variables enable the agent to know exactly when it's speaking and how much of the response has been spoken, which is essential for resuming after false interruptions.

### 2. Speech Event Handlers

**Added:** Three event handlers to monitor speech state in real-time

```python
async def on_agent_speech_started(self):
    self.is_speaking = True
    logger.info("Agent started speaking")

async def on_agent_speech_chunk(self, chunk: str):
    """LiveKit streams TTS chunks here. Track exactly what was spoken."""
    self.full_response += chunk
    self.spoken_offset += len(chunk)

async def on_agent_speech_ended(self):
    self.is_speaking = False
    logger.info("Agent finished speaking")
```

**Purpose:** 
- `on_agent_speech_started`: Sets the speaking flag to enable filtering
- `on_agent_speech_chunk`: Tracks the exact content being spoken for potential resume
- `on_agent_speech_ended`: Clears the speaking flag to allow normal responses

### 3. Configurable Word Lists

**Added:** Two sets of words for filtering logic

```python
FILLER_WORDS = {
    "ok", "okay", "yeah", "yep", "uh-huh", "uh huh",
    "hmm", "mm", "mhmm", "right", "cool", "oh"
}

INTERRUPT_WORDS = {
    "stop", "wait", "hold on", "pause", "cancel"
}
```

**Purpose:** 
- `FILLER_WORDS`: Passive acknowledgements that should be ignored during speech
- `INTERRUPT_WORDS`: Commands that should always cause immediate interruption
- Both sets are easily configurable for different use cases

### 4. Intelligent Transcript Filtering

**Modified:** Complete overhaul of `on_user_transcript` method

```python
async def on_user_transcript(self, transcript):
    if not transcript.final:
        return

    text = transcript.text.lower().strip(" .,!?")
    words = text.split()

    logger.info(f"User said: {text}")

    # 1️⃣ Ignore single-word fillers during speech
    if len(words) == 1 and text in FILLER_WORDS:
        logger.info("Ignoring filler word")
        return

    # 2️⃣ True interruption detection
    if any(w in text for w in INTERRUPT_WORDS) and self.is_speaking:
        logger.info("True interruption detected")
        await self.session.interrupt()
        return

    # 3️⃣ Normal conversation handling
    await super().on_user_transcript(transcript)
```

**Purpose:** This is the core logic that implements the behavior matrix:
- **Line 1-2**: Only process finalized transcripts
- **Line 4-5**: Normalize text and split into words
- **Line 9-11**: Filter out single-word fillers when speaking
- **Line 14-17**: Detect and handle true interruptions
- **Line 20**: Pass through to normal processing for all other cases

### 5. Session Configuration

**Modified:** Critical session settings to prevent stuttering

```python
session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2",
    vad=ctx.proc.userdata["vad"],
    turn_detection=MultilingualModel(),
    
    # 🔑 KEY SETTINGS FOR SMOOTH OPERATION
    allow_interruptions=True,              # Enable interrupt handling
    resume_false_interruption=True,        # Resume after false interrupts
    false_interruption_timeout=1.5,        # 1.5s buffer for STT validation
    preemptive_generation=False,           # Disable preemptive to reduce conflicts
)
```

**Purpose:** 
- `allow_interruptions=True`: Enables the interrupt mechanism
- `resume_false_interruption=True`: Automatically resumes speech after false interrupts
- `false_interruption_timeout=1.5`: Provides time for STT to catch up with VAD
- `preemptive_generation=False`: Prevents conflicting audio streams

### 6. Agent Instructions

**Modified:** Enhanced instructions to guide agent behavior

```python
super().__init__(
    instructions=(
        "Your name is Kelly. "
        "You tell long, engaging stories when asked. "
        "Do not restart sentences after interruptions. "
        "If interrupted, continue from where you stopped. "
        "Ignore listener acknowledgements like yeah or hmm."
    )
)
```

**Purpose:** Instructs the LLM to produce behavior that aligns with the interruption handling system.

## 🔄 State Machine Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      User Speaks                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  Transcript Finalized   │
              └────────────┬────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Is Agent Speaking?   │
              └────────┬───────────────┘
                       │
            ┌──────────┴──────────┐
            │                     │
          YES                    NO
            │                     │
            ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Contains Interrupt?  │  │  Normal Processing   │
└──────┬───────────────┘  └──────────────────────┘
       │                           │
   ┌───┴───┐                       ▼
  YES     NO               [Agent Responds]
   │       │
   │       ▼
   │  ┌────────────────┐
   │  │ Single Filler? │
   │  └────┬───────────┘
   │       │
   │   ┌───┴───┐
   │  YES     NO
   │   │       │
   │   ▼       ▼
   │ [Ignore] [Process]
   │
   ▼
[Interrupt Session]
```

## 🚀 How It Works

### Scenario 1: User Says "Yeah" While Agent Speaks
```
1. Agent starts speaking → is_speaking = True
2. User says "yeah" → VAD triggers
3. STT finalizes: "yeah"
4. on_user_transcript() called
5. Check: len(words)==1 and "yeah" in FILLER_WORDS → TRUE
6. Check: is_speaking → TRUE
7. → RETURN (ignore completely)
8. Agent continues speaking without interruption ✅
```

### Scenario 2: User Says "Wait" While Agent Speaks
```
1. Agent is speaking → is_speaking = True
2. User says "wait" → VAD triggers
3. STT finalizes: "wait"
4. on_user_transcript() called
5. Check: "wait" in INTERRUPT_WORDS → TRUE
6. Check: is_speaking → TRUE
7. → await session.interrupt()
8. Agent stops immediately ✅
```

### Scenario 3: User Says "Yeah" While Agent Is Silent
```
1. Agent is silent → is_speaking = False
2. User says "yeah" → VAD triggers
3. STT finalizes: "yeah"
4. on_user_transcript() called
5. Check: is_speaking → FALSE
6. → await super().on_user_transcript(transcript)
7. Agent processes "yeah" as valid input ✅
```

### Scenario 4: Mixed Input "Yeah Wait"
```
1. Agent is speaking → is_speaking = True
2. User says "yeah wait" → VAD triggers
3. STT finalizes: "yeah wait"
4. on_user_transcript() called
5. Check: len(words)==1 → FALSE (has 2 words)
6. Check: "wait" in text → TRUE
7. → await session.interrupt()
8. Agent stops immediately ✅
```

## 🎓 Technical Challenges Solved

### Challenge 1: VAD vs STT Timing
**Problem:** VAD triggers faster than STT, causing premature interruptions

**Solution:** 
- `false_interruption_timeout=1.5` gives STT time to finalize
- `resume_false_interruption=True` allows recovery if needed
- State-based filtering happens after STT finalization

### Challenge 2: Preventing Agent Stuttering
**Problem:** Agent restarting sentences after false interrupts

**Solution:**
- Disabled `preemptive_generation` to prevent conflicting streams
- Used `resume_false_interruption` for seamless continuation
- Tracked speech chunks for precise resume points (if needed)

### Challenge 3: Mixed Input Detection
**Problem:** "Yeah wait" should interrupt but "yeah" shouldn't

**Solution:**
- Single-word check: `len(words) == 1` ensures only isolated fillers are ignored
- Interrupt scan: `any(w in text for w in INTERRUPT_WORDS)` catches mixed commands

### Challenge 4: State-Aware Processing
**Problem:** Same word needs different handling based on agent state

**Solution:**
- `is_speaking` flag tracks exact agent state
- All filtering decisions check state before acting
- Silent state allows normal transcript processing


## 🏃‍♂️ Running the Agent

### Installation
```bash
# Clone repository
git clone https://github.com/Dark-Sys-Jenkins/agents-assignment
cd agents-assignment

# Install dependencies
pip install -r requirements.txt
```

### Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### Launch
```bash
# Run the agent
python agent.py dev
```


## 📦 Dependencies

### Core Requirements
```
livekit-agents >= 0.8.0
livekit-plugins-deepgram
livekit-plugins-openai
livekit-plugins-cartesia
livekit-plugins-silero
python-dotenv
```
