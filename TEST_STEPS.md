# Step-by-Step Testing Guide

## Prerequisites Setup

### Step 1: Install Dependencies

```bash
cd "C:\Users\Sakash Srivastava\OneDrive\Desktop\Projects\agents-assignment"

# Install the livekit-agents package in development mode
cd livekit-agents
pip install -e ".[openai,silero,deepgram,cartesia,turn-detector]"
cd ..
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the `examples` directory (or use existing one):

```bash
cd examples
# Create .env file if it doesn't exist
```

Add these to your `.env` file:
```env
# Required API Keys
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
CARTESIA_API_KEY=your_cartesia_key_here

# Optional: Configure interruption handler (uses defaults if not set)
AGENT_IGNORE_WORDS=yeah,ok,hmm,right,uh-huh,aha,mm-hmm,yep,yup,okay
AGENT_STT_WAIT_TIMEOUT=0.5
```

### Step 3: Install Example Dependencies

```bash
cd examples/voice_agents
pip install -r requirements.txt
```

## Testing Methods

### Method 1: Console Mode (Easiest - No LiveKit Server Needed)

This runs the agent locally with your microphone:

```bash
cd "C:\Users\Sakash Srivastava\OneDrive\Desktop\Projects\agents-assignment\examples\voice_agents"
python basic_agent.py console
```

**What happens:**
- Agent starts and greets you
- You can speak directly to test scenarios
- No LiveKit server required

### Method 2: With LiveKit Server (More Realistic)

If you have LiveKit Cloud or local server:

```bash
# Set these in .env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret

# Run in dev mode
python basic_agent.py dev
```

## Test Scenarios

### Test 1: Agent Ignores "yeah" While Speaking ✅

**Steps:**
1. Start the agent: `python basic_agent.py console`
2. Wait for agent to start speaking (it will greet you)
3. **While agent is speaking**, say: "yeah" or "ok" or "hmm"
4. **Expected Result**: Agent continues speaking without pausing or stopping

**What to look for:**
- ✅ Agent doesn't pause
- ✅ Agent doesn't stutter
- ✅ Agent completes its sentence
- ❌ If agent stops/pauses = FAIL

### Test 2: Agent Responds to "yeah" When Silent ✅

**Steps:**
1. Start the agent
2. Wait for agent to finish speaking and go silent
3. Say: "yeah"
4. **Expected Result**: Agent processes "yeah" as valid input and responds

**What to look for:**
- ✅ Agent acknowledges "yeah"
- ✅ Agent continues conversation
- ❌ If agent ignores it completely = FAIL

### Test 3: Agent Stops for "stop" Command ✅

**Steps:**
1. Start the agent
2. Let agent start speaking
3. Say: "No stop" or "wait" or "stop"
4. **Expected Result**: Agent stops immediately

**What to look for:**
- ✅ Agent stops speaking immediately
- ✅ Agent listens for new input
- ❌ If agent continues = FAIL

### Test 4: Mixed Input Detection ✅

**Steps:**
1. Start the agent
2. Let agent start speaking
3. Say: "Yeah okay but wait" or "Yeah but stop"
4. **Expected Result**: Agent stops (recognizes "wait"/"stop" as command)

**What to look for:**
- ✅ Agent stops despite starting with "yeah"
- ✅ Agent recognizes the command in mixed input
- ❌ If agent ignores it = FAIL

## Debugging Tips

### Enable Debug Logging

Add this to see what's happening:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Logs

Look for these log messages:
- `"Ignoring interruption due to filler words"` - Handler is working!
- `"Async check: Ignoring interruption"` - Async handler working!

### Common Issues

1. **Agent still stops on "yeah"**
   - Check if transcript is being received
   - Verify handler is initialized (check logs)
   - Make sure agent is actually speaking (not silent)

2. **Agent ignores "yeah" when silent**
   - This is correct behavior! Handler only filters when agent is speaking
   - If it's ignoring when silent, check the state detection

3. **Import errors**
   - Make sure you installed: `pip install -e livekit-agents`
   - Check Python path includes the repo

## Recording Proof

### Option 1: Screen Recording
- Use OBS, Windows Game Bar, or any screen recorder
- Record all 4 test scenarios
- Save as `proof_video.mp4`

### Option 2: Log Transcript
- Enable detailed logging
- Save console output showing:
  - Agent ignoring "yeah" while speaking
  - Agent responding to "yeah" when silent
  - Agent stopping for "stop"
- Save as `PROOF.md`

## Quick Test Script

Create a simple test to verify handler is loaded:

```python
# test_handler.py
from livekit.agents.voice.interruption_handler import InterruptionHandler

handler = InterruptionHandler()
result, reason = handler.should_ignore_interruption(
    agent_is_speaking=True,
    transcript="yeah",
    wait_for_transcript=False
)
print(f"Should ignore: {result}, Reason: {reason}")
# Expected: Should ignore: True, Reason: only_filler_words: yeah
```

Run: `python test_handler.py`
