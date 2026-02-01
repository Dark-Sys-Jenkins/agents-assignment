# Context-Aware Interruption Handler

A voice agent implementation that intelligently distinguishes between filler words and actual commands, achieving **true deafness to filler words** while maintaining responsive interruption behavior.


Uses `turn_detection="manual"` to disable automatic VAD/STT-triggered pauses. We then manually control turns via `commit_user_turn()`, calling it **only for non-filler speech**.


## How It Works

### Classification System
| Input | Classification | Action |
|-------|---------------|--------|
| "Yeah", "Okay", "Mm-hmm" | Filler | Ignore completely |
| "Wait", "Stop", "No" | Command | Interrupt immediately |
| "Tell me more" | Speech | Commit turn |


## Setup

1. Install dependencies:
```bash
uv sync
```

2. Configure `.env`:
```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

3. Run the agent:
```bash
uv run python voice-agent.py start
```
