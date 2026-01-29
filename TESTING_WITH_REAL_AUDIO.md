# How to Test the Interrupt Handler with Real Audio

## Quick Start (5 minutes)

### Step 1: Get API Keys

You need 3 API keys (free tier available for all):

**OpenAI (LLM - Agent's Brain)**
- Go to: https://platform.openai.com/api-keys
- Click "Create new secret key"
- Copy the key

**Deepgram (STT - Speech Recognition)**
- Go to: https://console.deepgram.com/
- Create account → API Keys
- Copy the key

**Cartesia (TTS - Voice Output)**
- Go to: https://play.cartesia.ai/
- Sign up → API Keys
- Copy the key

### Step 2: Create `.env` File

Create a file at `c:\Users\Amit\Desktop\agents-assignment\.env` with:

```
OPENAI_API_KEY=sk-...your_key_here...
DEEPGRAM_API_KEY=...your_key_here...
CARTESIA_API_KEY=...your_key_here...
```

**Important**: Keep this file private! Never commit it to git.

### Step 3: Install Dependencies

```bash
cd c:\Users\Amit\Desktop\agents-assignment
pip install python-dotenv livekit-agents[openai,deepgram,cartesia,silero,turn-detector]
```

### Step 4: Run the Test

```bash
python test_interrupt_handler_live.py
```

Or use one of the existing examples:

```bash
cd examples/voice_agents
python basic_agent.py dev
```

---

## What to Expect

### Scenario 1: Backchanneling Test ✓
1. Agent starts speaking: "Hello, how can I help you today?"
2. **You say: "Yeah"**
3. **Expected**: Agent continues speaking (backchanneling word ignored)

### Scenario 2: Real Interruption Test ✓
1. Agent starts speaking: "Let me tell you about..."
2. **You say: "Stop!"**
3. **Expected**: Agent stops immediately and waits for your input

### Other Backchanneling Words That Won't Interrupt:
- "Yeah", "yep", "yes", "ok", "okay"
- "Right", "got it", "gotcha"
- "Hmm", "mm-hmm", "uh-huh"
- "Sure", "fine", "cool", "good", "great"

### Words That WILL Interrupt:
- "Stop", "wait", "hold on"
- "I disagree", "that's wrong"
- Any sentence with meaningful content

---

## Alternative: No API Keys? Test Locally

If you don't want to use API keys yet, you can test with fake/local components:

```python
# In your test script, use local models:
session = AgentSession(
    stt="silero",  # Local speech recognition
    llm="openai/gpt-4-mini",  # Still needs API key
    tts="silero",  # Local TTS
    vad=silero.VAD.load(),  # Local VAD
)
```

---

## Troubleshooting

### "No module named 'livekit'"
```bash
pip install livekit-agents
```

### "OPENAI_API_KEY not found"
Make sure:
1. `.env` file exists at project root
2. File contains: `OPENAI_API_KEY=sk-...`
3. Run `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"`

### "No audio input device found"
- Check your microphone is connected
- Check audio permissions (Windows: Settings > Privacy > Microphone)
- Run: `python -c "import sounddevice; print(sounddevice.query_devices())"`

### "Connection failed"
- This is expected if no LiveKit server is running
- For local testing, you need to modify the session setup
- Check: https://docs.livekit.io/agents/examples/

---

## Live Testing with LiveKit Server (Advanced)

If you want to test in a real room:

1. Start a LiveKit server (Docker recommended):
```bash
docker run --rm \
  -p 7880:7880 \
  -p 7881:7881 \
  -p 7882:7882/udp \
  livekit/livekit-server \
  --dev \
  --bind localhost
```

2. Create a LiveKit session in a room

3. Connect your agent to the room and test!

---

## Expected Test Output

```
INFO:test-interrupt-handler:Starting interrupt handler test...
======================================================================
TEST: Interrupt Handler with Real Audio
======================================================================

This test demonstrates:
  1. Agent speaking with real audio output
  2. Backchanneling words (yeah, ok) NOT interrupting the agent
  3. Real interruptions (stop, I disagree) DO interrupt the agent

======================================================================

INFO:test-interrupt-handler:Starting session...
INFO:test-interrupt-handler:Waiting for audio input...

INFO:test-interrupt-handler:Session started! Listening for audio...
INFO:test-interrupt-handler:Press Ctrl+C to exit.

[Listen for audio input...]
[Agent responds to your voice...]
```

---

## Next Steps

Once you verify the interrupt handler works:

1. ✓ Test backchanneling: Say "yeah" while agent speaks
2. ✓ Test interruption: Say "stop" while agent speaks
3. ✓ Test normal flow: Say something meaningful
4. Modify backchanneling words in `agent_activity.py` if needed
5. Deploy to production with your LiveKit setup

Happy testing! 🎉
