# LiveKit Intelligent Interruption Handling

A voice agent that knows the difference between "yeah, I'm listening" and "wait, stop talking."

## Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Demo](#demo)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

---

## Problem

LiveKit's default Voice Activity Detection treats every sound as an interruption. When you say "yeah" or "okay" to show you're listening (backchanneling), the agent thinks you want to interrupt and stops talking mid-sentence.

The goal was to fix this: make the agent smart enough to ignore casual acknowledgments while still responding immediately to actual commands like "wait" or "stop."

The catch: the agent can't pause or stutter when it hears a filler word. It needs to keep talking smoothly, like a human would.

---

## Solution

The solution uses three layers:

**1. VAD Threshold Tuning**  
Set the interruption thresholds higher (0.6 seconds, 2 words minimum). This filters out most quick "yeah" or "okay" responses before they even trigger an interruption.

**2. Auto-Resume**  
If VAD does interrupt on a filler word, LiveKit's `resume_false_interruption` feature kicks in and the agent continues talking without missing a beat.

**3. Transcript Analysis**  
When speech is detected, we wait for the actual transcription to come through. Then we check: is this a filler word or a real command? If it's a filler, suppress it. If it's a command like "stop", force an interruption even if VAD missed it.

### Why This Works

There's a timing problem: VAD detects sound almost instantly (~10ms), but speech-to-text takes longer (~200-500ms). By the time we know what was said, VAD might have already interrupted.

The solution handles this by:
- Fast fillers (under 0.6s) never trigger VAD in the first place
- Slow fillers (over 0.6s) trigger VAD but get auto-resumed when we realize they're fillers
- Commands work at any speed because we manually interrupt when we detect them in the transcript

---

## Installation

### Requirements

- Python 3.9+
- LiveKit account (free tier works fine)

### Install Dependencies

```bash
pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0"
```

---

## Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Required - Get these from LiveKit Cloud
LIVEKIT_API_SECRET="your-api-secret-here"
LIVEKIT_API_KEY="your-api-key-here"
LIVEKIT_URL="wss://your-project.livekit.cloud"

# Optional - For model providers
OPENAI_API_KEY="your-openai-key"
DEEPGRAM_API_KEY="your-deepgram-key"
CARTESIA_API_KEY="your-cartesia-key"
```

To get LiveKit credentials:
1. Go to [cloud.livekit.io](https://cloud.livekit.io)
2. Create a project
3. Copy the API key, secret, and WebSocket URL from Settings



---

## Usage

Run the agent locally:

```bash
python basic_agent.py dev
```

The agent starts in console mode. Just start talking - it'll respond.

---

## How It Works

### The Flow

```
User says "yeah" while agent talks
    ↓
VAD detects speech in ~10ms
    ↓
Is it under 0.6 seconds? → Agent keeps talking
Is it over 0.6 seconds? → VAD interrupts
    ↓
STT finishes transcribing (~200-500ms later)
    ↓
Our code checks the transcript:
    - Filler word? → Resume immediately
    - Command word? → Stay stopped
    ↓
Result: No awkward pauses
```

### State-Based Logic

The same word behaves differently based on context:

| What user says | Agent state | What happens |
|----------------|-------------|--------------|
| "yeah" / "okay" / "hmm" | Speaking | Ignored completely |
| "wait" / "stop" | Speaking | Stops immediately |
| "yeah" / "okay" | Silent | Suppressed (doesn't trigger response) |
| "tell me more" | Silent | Normal response |

### Filler Detection

We check if something is a filler in two ways:

1. **No-space check**: "uh-huh" becomes "uhhuh" and matches our list
2. **All-words check**: "all right" splits to ["all", "right"], both are in our list, so it's a filler

This handles things like "got it", "i see", "all right" automatically.

### Command Detection

For commands, we look for:
- Stop word at the start: "stop", "wait please"
- Filler + stop word: "yeah wait", "okay stop"  
- Conjunction + stop word: "but wait", "and hold on"

We skip long sentences (over 3 words) to avoid false positives like "I have no idea".

---

## Demo

**[https://drive.google.com/file/d/1IHqKgqxAG2ZHRwWsDxhksyp3En5qv5iM/view?usp=sharing]**

The demo shows:
- Agent continuing to talk when hearing "yeah", "okay", "uh-huh"
- Agent stopping immediately when hearing "stop" or "wait"
- Handling mixed inputs like "yeah but wait"

See `demo_logs.txt` for the full transcript from test runs.

---

## Customization

### Adding More Filler Words

Edit `FILLER_WORDS` in `basic_agent.py`:

```python
FILLER_WORDS = {
    "yeah", "yep", "ok", "hmm", "uh", "um",
    # Add your own here
    "absolutely", "indeed", "totally"
}
```

### Adding More Command Words

Edit `STOP_WORDS`:

```python
STOP_WORDS = {
    "wait", "stop", "hold", "pause",
    # Add your own
    "interrupt", "enough"
}
```

### Tuning Sensitivity

In the `AgentSession` configuration:

```python
min_interruption_duration=0.6,  # Lower = more responsive, higher = fewer interruptions
min_interruption_words=2,        # Minimum words before triggering interrupt
```

Tuning guide:
- Want fewer interruptions? Set duration to 0.8-1.0 seconds
- Want faster response to commands? Set duration to 0.4-0.5 seconds
- Want stricter filtering? Increase min_interruption_words to 3

---

## Troubleshooting

### Agent doesn't stop for commands

Check the logs for `🛑 STOP COMMAND` messages. If you don't see them:
- Make sure the word is in `STOP_WORDS`
- Try saying shorter commands (under 3 words)
- Verify `session.interrupt()` is being called

### Agent pauses briefly on fillers

This means the auto-resume isn't working:
- Increase `min_interruption_duration` to 0.8
- Check that `resume_false_interruption=True` in the session config
- Look for "FALSE INTERRUPTION AUTO-RESUMED" in logs

### Fillers still triggering responses

Check what STT is actually transcribing (look at the `📝 TRANSCRIPT` logs). Sometimes "yeah" comes through as "yea" or other variations. Add those to `FILLER_WORDS`.


---

## Additional Resources

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [Assignment Repo](https://github.com/Dark-Sys-Jenkins/agents-assignment)

---

**Last Updated**: February 2026  
**LiveKit Version**: 1.3.12