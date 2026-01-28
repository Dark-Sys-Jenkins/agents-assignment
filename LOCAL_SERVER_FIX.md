# LiveKit Local Server - Fix for 3rd Party Plugins Issue

## Problem Summary

The error you encountered shows 401 Unauthorized responses when connecting to cloud services:
```
WSServerHandshakeError: 401, message='Invalid response status'
url='wss://agent-gateway.livekit.cloud/v1/stt?model=deepgram/nova-3'
```

### Root Cause

The `basic_agent.py` was configured to use **cloud-based services**:
- **STT**: `deepgram/nova-3` (requires Deepgram API key)
- **LLM**: `google/gemini-3-flash` (requires Google API key)  
- **TTS**: `deepgram/aura` (requires Deepgram API key)

These cloud services route through LiveKit's cloud gateway, which requires proper API credentials set up in LiveKit's cloud system. For **local-only deployments**, these won't work.

## Solution

### 1. Use Local Plugins Instead of Cloud Services

Changed the agent configuration to use local plugins that don't require cloud APIs:

```python
# OLD (Cloud-based - doesn't work without credentials)
stt="deepgram/nova-3",
llm="google/gemini-3-flash",
tts="deepgram/aura",

# NEW (Local-friendly alternatives)
stt=silero.STT(),  # Local speech-to-text
llm=openai.LLM(),  # Requires OPENAI_API_KEY (or use ollama for fully local)
tts=openai.TTS(),  # Requires OPENAI_API_KEY (or use local TTS)
```

### 2. Alternative Fully-Local Setup (No Cloud Required)

For completely local deployment without any cloud APIs:

```python
from livekit.plugins import silero, elevenlabs
# Or use any local TTS alternative

stt=silero.STT(),  # Runs locally, no API key needed
llm=ollama.LLM(model="llama2"),  # Or any local LLM
tts=elevenlabs.TTS(),  # Or other local TTS options
```

### 3. Configuration

The `.env` file already has:
- `LIVEKIT_URL=http://localhost:7880` ✓
- `LIVEKIT_API_KEY=localdev1` ✓
- `LIVEKIT_API_SECRET=someverylongsecretstringthatissafely32chars` ✓

Add your API keys as needed:
```env
OPENAI_API_KEY=your_key_here  # If using OpenAI
DEEPGRAM_API_KEY=your_key_here  # If using Deepgram
```

## What Changed in basic_agent.py

1. **Added OpenAI import**: `from livekit.plugins import silero, openai`
2. **Updated STT**: Changed from `"deepgram/nova-3"` to `silero.STT()`
3. **Updated LLM**: Changed from `"google/gemini-3-flash"` to `openai.LLM()`
4. **Updated TTS**: Changed from `"deepgram/aura"` to `openai.TTS()`
5. **Added comments**: Documented the options for local deployment

## Available Plugin Options

### Speech-to-Text (STT)
- **Silero** (local, free): `silero.STT()`
- **Deepgram** (cloud, requires API key): `deepgram.STT(model="nova-3")`
- **OpenAI Whisper** (cloud): `openai.STT()`
- **Assembly AI** (cloud): `assemblyai.STT()`

### Language Model (LLM)
- **OpenAI** (cloud): `openai.LLM(model="gpt-4")`
- **Google Gemini** (cloud): `google.LLM(model="gemini-3-flash")`
- **Ollama** (fully local): `ollama.LLM(model="llama2")`
- **Groq** (cloud): `groq.LLM()`

### Text-to-Speech (TTS)
- **OpenAI** (cloud): `openai.TTS()`
- **Deepgram Aura** (cloud): `deepgram.TTS(voice="aura-en-us-female")`
- **ElevenLabs** (cloud): `elevenlabs.TTS()`
- **Cartesia** (cloud): `cartesia.TTS()`

## Testing the Fix

```bash
# Make sure your local LiveKit server is running on localhost:7880
python examples\voice_agents\basic_agent.py dev

# In another terminal, dispatch an agent job
python dispatch_agent.py
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `APIConnectionError: failed to connect to LiveKit STT` | Remove cloud-based models, use local alternatives like Silero |
| `401 Unauthorized` | Check that you're not using cloud services without proper API keys |
| `OPENAI_API_KEY not found` | Add `OPENAI_API_KEY=sk-...` to your `.env` file |
| Agent won't start | Verify `LIVEKIT_URL=http://localhost:7880` is correct and server is running |

## Next Steps

1. ✅ `basic_agent.py` has been updated to use `silero.STT()` + `openai.LLM()` + `openai.TTS()`
2. ✅ `.env` file has been updated with `OPENAI_API_KEY` placeholder
3. 📝 **TODO**: Add your actual OpenAI API key to `.env`
4. 🚀 Run the agent and test with local LiveKit server
