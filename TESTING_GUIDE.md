# Testing Guide for Interruption Handler

## Prerequisites

1. Set up environment variables (if needed):
```bash
# Optional - uses defaults if not set
export AGENT_IGNORE_WORDS="yeah,ok,hmm,right,uh-huh,aha,mm-hmm,yep,yup,okay"
export AGENT_STT_WAIT_TIMEOUT=0.5
```

2. Install dependencies:
```bash
cd livekit-agents
pip install -e .
```

3. Set up API keys:
- DEEPGRAM_API_KEY (for STT)
- OPENAI_API_KEY (for LLM)
- CARTESIA_API_KEY or ELEVEN_API_KEY (for TTS)

## Test Scenarios

### Scenario 1: Agent ignores "yeah" while speaking
1. Start the agent
2. Let agent start speaking (e.g., reading a long paragraph)
3. While agent is speaking, say "yeah" or "ok" or "hmm"
4. **Expected**: Agent continues speaking without interruption

### Scenario 2: Agent responds to "yeah" when silent
1. Start the agent
2. Wait for agent to finish speaking and go silent
3. Say "yeah"
4. **Expected**: Agent processes "yeah" as valid input and responds

### Scenario 3: Agent stops for "stop" command
1. Start the agent
2. Let agent start speaking
3. Say "No stop" or "wait"
4. **Expected**: Agent stops immediately

### Scenario 4: Mixed input detection
1. Start the agent
2. Let agent start speaking
3. Say "Yeah okay but wait"
4. **Expected**: Agent stops (recognizes "wait" as command)

## Running Tests

### Option 1: Use existing example
```bash
cd examples/voice_agents
python basic_agent.py console
```

### Option 2: Create test script
Create a simple test file to verify the handler works.

## Recording Proof

Record a video or create logs showing:
- Agent ignoring "yeah" while talking
- Agent responding to "yeah" when silent  
- Agent stopping for "stop"

Save as `PROOF.md` or `proof_video.mp4` in the repository root.
