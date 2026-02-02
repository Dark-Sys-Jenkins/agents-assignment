# Quick Testing Guide

## Step 1: Install Dependencies First

```bash
cd "C:\Users\Sakash Srivastava\OneDrive\Desktop\Projects\agents-assignment"

# Install the package in development mode
cd livekit-agents
pip install -e ".[openai,silero,deepgram,cartesia,turn-detector]"
cd ..
```

## Step 2: Set Up API Keys

Create or edit `examples/.env` file:

```env
# Required for basic_agent.py
DEEPGRAM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  
CARTESIA_API_KEY=your_key_here

# Optional - interruption handler config (uses defaults if not set)
AGENT_IGNORE_WORDS=yeah,ok,hmm,right,uh-huh,aha,mm-hmm,yep,yup,okay
AGENT_STT_WAIT_TIMEOUT=0.5
```

**Get API Keys:**
- Deepgram: https://console.deepgram.com/
- OpenAI: https://platform.openai.com/api-keys
- Cartesia: https://cartesia.ai/

## Step 3: Test the Agent

### Option A: Console Mode (Easiest - No LiveKit Server)

```bash
cd examples/voice_agents
python basic_agent.py console
```

**What happens:**
- Agent starts and greets you
- You speak directly into your microphone
- Agent responds via your speakers

### Option B: With LiveKit (More Realistic)

If you have LiveKit Cloud account:

```bash
# Add to .env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret

# Run
python basic_agent.py dev
```

## Step 4: Test All 4 Scenarios

### ✅ Test 1: Agent Ignores "yeah" While Speaking

1. Start agent: `python basic_agent.py console`
2. Wait for agent to start speaking (it will greet you)
3. **While agent is speaking**, say: **"yeah"** or **"ok"**
4. **Expected**: Agent continues speaking without stopping
5. **If agent stops/pauses = FAIL ❌**

### ✅ Test 2: Agent Responds to "yeah" When Silent

1. Wait for agent to finish speaking
2. Say: **"yeah"**
3. **Expected**: Agent processes it and responds
4. **If agent ignores it = FAIL ❌**

### ✅ Test 3: Agent Stops for Commands

1. Let agent start speaking
2. Say: **"stop"** or **"no wait"**
3. **Expected**: Agent stops immediately
4. **If agent continues = FAIL ❌**

### ✅ Test 4: Mixed Input

1. Let agent start speaking
2. Say: **"yeah but wait"** or **"ok stop"**
3. **Expected**: Agent stops (recognizes command)
4. **If agent ignores = FAIL ❌**

## Troubleshooting

### "Module not found" errors
```bash
# Install dependencies
cd livekit-agents
pip install -e ".[openai,silero,deepgram,cartesia,turn-detector]"
```

### "API key not found" errors
- Check your `.env` file exists in `examples/` directory
- Verify API keys are correct
- Make sure you're using the right format (no quotes needed)

### Agent still stops on "yeah"
- Check console logs for: `"Ignoring interruption due to filler words"`
- Verify handler is loaded (should see no errors on startup)
- Make sure agent is actually speaking (not silent)

### Can't hear agent
- Check your speakers/headphones
- Verify audio output device in system settings
- Try: `python basic_agent.py console --verbose`

## Recording Proof

### Video Recording
1. Start screen recorder (OBS, Windows Game Bar, etc.)
2. Run all 4 test scenarios
3. Save as `proof_video.mp4`

### Log Transcript
1. Run agent with verbose logging
2. Copy console output showing all 4 scenarios
3. Save as `PROOF.md`

## Quick Verification

To verify handler is loaded, check the logs when agent starts. You should see:
- No import errors
- Agent starts normally
- When you say "yeah" while agent speaks, look for debug message: `"Ignoring interruption due to filler words"`
