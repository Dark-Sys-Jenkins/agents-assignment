# Intelligent Interruption Handling

## What's added
- Backchannel-aware interruption logic for LiveKit voice agents.
- Configurable vocab for backchannels and interrupt words.
- Example agent demonstrating the behavior.

## What was the challenge
- Default VAD pauses on filler words ("yeah/ok/hmm") while the agent is speaking, causing hiccups.
- We need to ignore passive acknowledgements during agent speech but still interrupt on real commands or mixed input.

## Why it works
- State-aware filter (`BackchannelFilter`) plus gating in `agent_activity.py`: only pause speech when STT confirms the user said something other than a pure backchannel.
- Backchannels while speaking are ignored; commands or mixed phrases interrupt; when silent, all input (including "yeah") is processed.
- Fast path on interim transcripts for interrupt words; otherwise defer to final STT to avoid stutters.
- Vocab is configurable via `AgentSession(backchannel_words=..., interrupt_words=...)` or env vars `LIVEKIT_BACKCHANNEL_WORDS` / `LIVEKIT_INTERRUPT_WORDS`.

## How to run (console)
1. Ensure env keys for your chosen STT/TTS/LLM and LiveKit (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`).
2. `uv run python examples/voice_agents/intelligent_interruption.py console`
3. While the agent speaks, say "yeah/ok/uh-huh" → it keeps talking. When silent, say "yeah" → it responds. Say "stop" or "yeah wait" → it interrupts.

## Proof video
- Demo run (ignores "yeah" while speaking, responds when silent, interrupts on "stop"): https://drive.google.com/file/d/10UVOjNTleis-KmO4hsQBLCw8g-pjdtAR/view?usp=drivesdk

## How to run (dev with Agents Playground)
1. Set env: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (and provider keys for STT/TTS/LLM in the example).
2. Start hot reload: `uv run python examples/voice_agents/intelligent_interruption.py dev` (Ctrl+C to restart if needed).
3. Open https://agents-playground.livekit.io, enter the same URL/key/secret and a room name; connect and talk to the agent to verify the backchannel behavior.

