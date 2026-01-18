# Intelligent Interrupt Agent

So basically this is a voice agent that knows when to listen and when to ignore you. 

## The Problem

Regular voice assistants are dumb about interruptions. Like if you're listening to it talk and you go "uh huh" or "yeah" just to show you're following along, most assistants will either:
1. Stop completely thinking you want to say something
2. Or just ignore everything you say

Neither is great. We want something smarter.

## What This Agent Does

This agent can tell the difference between:
- **Backchannels** - stuff like "yeah", "ok", "hmm", "uh-huh" (you're just acknowledging, not actually trying to interrupt)
- **Real interrupts** - like when you say "stop" or ask a new question

### The Logic 

Here's how it works:

1. **When the agent IS talking:**
   - If you say "yeah" or "ok" → it ignores you (backchannel, you're just nodding along)
   - If you say "stop" or something new → it actually stops and listens

2. **When the agent is NOT talking:**
   - If you say "yeah" → it responds! (because now you're actually trying to talk to it)
   - Basically treats everything as a real input

The list of words it considers as backchannels:
```
yeah, yep, yes, ok, okay, right, uh-huh, hmm, sure, got it, mhm, ah, oh, i see
```

## How to Run

### 1. Setup your environment

Make a `.env` file with these keys:
```
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
GROQ_API_KEY=your_groq_key
```

### 2. Install dependencies

```bash
pip install livekit-agents livekit-plugins-deepgram livekit-plugins-cartesia livekit-plugins-groq livekit-plugins-silero python-dotenv
```

### 3. Start LiveKit server locally

You need LiveKit running. Easiest way is docker:
```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp livekit/livekit-server --dev
```

### 4. Run the agent

```bash
python intelligent_interrupt_agent.py dev
```

The `dev` flag enables hot reload so you can edit the code and it restarts automatically.

### 5. Connect to it

Go to https://agents-playground.livekit.io/

You'll need a token. Generate one with this python snippet:
```python
from livekit.api import AccessToken, VideoGrants
import os
from dotenv import load_dotenv

load_dotenv()

token = AccessToken(
    os.getenv('LIVEKIT_API_KEY'), 
    os.getenv('LIVEKIT_API_SECRET')
).with_identity('user-test').with_grants(
    VideoGrants(room_join=True, room='test-room')
)

print(token.to_jwt())
```

Paste that token in the playground, use `ws://localhost:7880` as the URL, and you're in!

## Code Breakdown

### The Backchannel Filter

```python
IGNORE_WORDS = {
    "yeah", "yep", "yes", "ok", "okay", "right",
    "uh-huh", "hmm", "sure", "got it", "mhm", "ah", "oh", "i see",
}

def should_interrupt(text: str) -> bool:
    # Clean up the text
    clean_text = text.strip().lower()
    clean_text = clean_text.replace(".", "").replace("!", "").replace("?", "").replace(",", "")
    
    if not clean_text:
        return False

    words = clean_text.split()
    # If ANY word is not in ignore list, it's a real interrupt
    return any(word not in IGNORE_WORDS for word in words)
```

If the user says something that's ONLY backchannel words, `should_interrupt` returns `False`. If there's anything else, it returns `True`.

### Tracking Speaking State

The tricky part is knowing if the agent was speaking when the user said something. We track this with a flag:

```python
self._was_speaking_during_input = False
```

When transcription comes in, we check if agent is speaking and save that:
```python
is_speaking = session.current_speech is not None
agent.set_speaking_context(is_speaking)
```

Then in `on_user_turn_completed`, we use that saved state to decide whether to ignore the backchannel or respond to it.

## Testing It

1. Ask the agent a question
2. While it's talking, say "yeah" or "ok" → should be ignored
3. While it's talking, say "stop" → should interrupt
4. When it's silent, say "yeah" → should get a response


