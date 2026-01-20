# Testing Intelligent Interruption Handling

This guide explains how to test the backchanneling interruption filtering feature.

## Prerequisites

1. **Install dependencies using uv:**
   ```bash
   cd /Users/amankumaryadav/Desktop/salescode/agents-assignment
   uv sync
   source .venv/bin/activate
   ```
   
   **Note:** If your environment is in a different location, adjust the path accordingly.

2. **Set up environment variables:**
   
   Create a `.env` file in the project root (or use your existing one) with:
   ```bash
   OPENAI_API_KEY=your_openai_key
   DEEPGRAM_API_KEY=your_deepgram_key
   CARTESIA_API_KEY=your_cartesia_key
   LIVEKIT_URL=your_livekit_url  # If using dev mode
   LIVEKIT_API_KEY=your_api_key  # If using dev mode
   LIVEKIT_API_SECRET=your_api_secret  # If using dev mode
   
   # Optional: Customize word lists (defaults work if not set)
   BACKCHANNELING_WORDS=yeah,ok,okay,hmm,right,uh-huh,aha,mhm
   INTERRUPT_WORDS=stop,wait,no,hold,pause,cancel
   ```
   
   **Note:** The test agent uses `load_dotenv()` to automatically load variables from `.env` file. No need to export them manually.

## Testing Methods

### Method 1: Test Agent (Recommended - Specifically for Interruption Testing)

This uses a dedicated test agent that tells long stories, making it easier to test interruptions:

```bash
cd examples/voice_agents
python test_interrupt_handler.py console
```

**Test Scenarios:**

1. **Test 1: Backchanneling while agent speaks (MUST PASS)**
   - Wait for agent to start speaking (e.g., "Hello, I'm Kelly...")
   - While agent is speaking, say: **"yeah"** or **"ok"** or **"uh-huh"**
   - **Expected:** Agent continues speaking without pausing or stopping
   - **Fail if:** Agent stops, pauses, or stutters

2. **Test 2: Real interruption while agent speaks (MUST PASS)**
   - Wait for agent to start speaking
   - While agent is speaking, say: **"stop"** or **"wait"** or **"no"**
   - **Expected:** Agent stops immediately
   - **Fail if:** Agent continues speaking

3. **Test 3: Mixed input while agent speaks (MUST PASS)**
   - Wait for agent to start speaking
   - Say: **"yeah wait"** or **"ok but stop"**
   - **Expected:** Agent stops (because it contains interrupt word)
   - **Fail if:** Agent ignores it

4. **Test 4: Backchanneling when agent is silent (MUST PASS)**
   - Wait for agent to finish speaking and go silent
   - Say: **"yeah"** or **"ok"**
   - **Expected:** Agent responds normally (e.g., "Great, let's continue")
   - **Fail if:** Agent ignores it completely

5. **Test 5: Normal conversation when agent is silent**
   - Wait for agent to finish speaking
   - Say: **"hello"** or **"tell me a story"**
   - **Expected:** Agent responds normally
   - **Fail if:** Agent doesn't respond

### Method 2: Using Basic Agent (Alternative)

If you prefer to use the basic agent:

```bash
cd examples/voice_agents
python basic_agent.py console
```

### Method 3: Using LiveKit Dev Mode

For more realistic testing with multiple clients:

```bash
cd examples/voice_agents
python test_interrupt_handler.py dev
# OR
python basic_agent.py dev
```

Then connect using:
- [Agents Playground](https://agents-playground.livekit.io/)
- Any LiveKit client SDK
- Set environment variables: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

## What to Look For

### ✅ Success Indicators:
- Agent continues speaking smoothly when you say "yeah/ok" while it's talking
- Agent stops immediately when you say "stop/wait" while it's talking
- No pauses, stutters, or hiccups in agent speech
- Agent responds normally to "yeah" when it's silent

### ❌ Failure Indicators:
- Agent stops or pauses when you say "yeah" while it's speaking
- Agent doesn't stop when you say "stop" while it's speaking
- Agent stutters or resumes after pausing (partial solution)
- Agent ignores "yeah" when it's silent (should respond)

## Debugging

If tests fail, check:

1. **Console logs:** Look for interruption events
2. **STT accuracy:** Make sure STT is correctly transcribing your words
3. **Environment variables:** Verify `BACKCHANNELING_WORDS` and `INTERRUPT_WORDS` are set correctly
4. **Agent state:** The filtering only applies when `agent_state == "speaking"`

## Recording Test Evidence

For submission, record a short video showing:
- Agent ignoring "yeah" while talking (continues seamlessly)
- Agent responding to "yeah" when silent
- Agent stopping for "stop"

Or provide log transcripts showing the behavior.
