# Quick Reference: Testing Interrupt Handler

## 1️⃣ Get API Keys (5 min)

| Service | Link | Free Tier |
|---------|------|-----------|
| **OpenAI (LLM)** | https://platform.openai.com/api-keys | $5 free credit |
| **Deepgram (STT)** | https://console.deepgram.com/ | 1,000 min/month |
| **Cartesia (TTS)** | https://play.cartesia.ai/ | Free tier available |

## 2️⃣ Create `.env` File

```bash
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
```

## 3️⃣ Install & Run

```bash
# Install dependencies
pip install python-dotenv livekit-agents[openai,deepgram,cartesia,silero,turn-detector]

# Run test
python test_interrupt_handler_live.py
```

## 4️⃣ Test Scenarios

| Test | Your Input | Expected Result |
|------|-----------|-----------------|
| **Backchanneling** | Say "yeah" or "ok" | ✓ Agent continues |
| **Real Interrupt** | Say "stop" or "wait" | ✓ Agent stops |
| **Normal Chat** | Say anything else | ✓ Agent responds |

## Backchanneling Words (Won't Interrupt)

```
yeah, yep, yes, yup, ok, okay, right, got it, gotcha
hmm, mm-hmm, mmhmm, uh-huh, uhuh, huh, um, uh, ah
sure, fine, cool, good, great
```

## Useful Commands

```bash
# Check if keys are loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Keys loaded:', bool(os.getenv('OPENAI_API_KEY')))"

# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Test a specific example
cd examples/voice_agents
python basic_agent.py dev

# Run tests
pytest tests/test_agent_session.py::test_events_and_metrics -v
```

## Where's My Code?

Your modifications are in:
- **Interrupt handler**: `livekit-agents/livekit/agents/voice/agent_activity.py` (lines 102-1224)
- **Documentation**: `INTERRUPT_HANDLER_SOLUTION.md`
- **Test guide**: `TESTING_WITH_REAL_AUDIO.md`

## Status Check

✅ Speaking state fix - DONE (test_events_and_metrics passes)
✅ Interrupt handler - DONE (filters backchanneling words)
✅ Documentation - DONE
⏳ Live audio testing - YOUR TURN!

---

**Questions?** Check `TESTING_WITH_REAL_AUDIO.md` for detailed troubleshooting!
