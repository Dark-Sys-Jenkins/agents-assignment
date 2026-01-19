# Intelligent Interruption Filter

## The Problem We're Solving

So here's the annoying thing - when the AI agent is explaining something and you say "okay" or "yeah" just to show you're listening, it thinks you want to interrupt and stops talking. Super frustrating right?

But here's the tricky part - when the agent is SILENT and you say "yeah", it should actually respond to that! Same word, completely different meaning based on context.

## How We Actually Solved It

The key insight: **we never even tell the speaking LLM that user started speaking until we're sure it's a real interruption.**

Here's what happens step by step:

### Step 1: User Starts Speaking
VAD (Voice Activity Detection) detects your voice. But we DON'T tell the LLM yet! The agent keeps talking as if nothing happened.

### Step 2: We Store Everything
As STT (Speech-to-Text) gives us words one by one, we store ALL of them:
- "okay" → stored
- "okay yeah" → stored  
- "okay yeah wait" → stored

### Step 3: Check Each Word
Every new word we ask: is this a filler word?
- "okay" → filler, keep storing, agent keeps talking
- "yeah" → filler, keep storing, agent keeps talking
- "wait" → NOT a filler! NOW we interrupt!

### Step 4: When We Find a Non-Filler
We tell the LLM "hey user said: okay yeah wait" - the ENTIRE transcript, not just "wait". This way the LLM knows everything user said.

### Step 5: If All Words Were Fillers
User stops speaking and all words were just fillers? We drop EVERYTHING. Agent never knows user spoke. Zero pause, zero stutter.

## The Magic Part

The old way was: VAD detects voice → immediately pause agent → wait for STT → too late, already paused!

Our way: VAD detects voice → we secretly start listening → STT comes in → check each word → only interrupt if it's actually important.

The agent never pauses for fillers because we never told it someone was speaking in the first place!

## Real Examples

### Example 1: Agent Explaining, You're Just Listening
```
Agent: "So computers work by processing binary data and..."
You: "okay"
Agent: "...converting it into meaningful information through..."
You: "yeah"
Agent: "...various hardware and software components."
```
Result: Agent keeps talking. You never interrupted anything.

### Example 2: Agent Asks Question
```
Agent: "Are you ready to continue?"
(Agent goes silent)
You: "yeah"
Agent: "Great! Let me explain the next part..."
```
Result: Agent responds to "yeah" because when agent is silent, filter is OFF.

### Example 3: You Actually Want to Interrupt
```
Agent: "So the first thing you need to do is..."
You: "okay wait"
Agent: (stops)
LLM receives: "okay wait"
```
Result: Agent stops on "wait" and gets the full message "okay wait".

### Example 4: Strong Interrupt
```
Agent: "Let me explain this in detail..."
You: "no stop"
Agent: (stops immediately)
```
Result: "no" and "stop" are not fillers - immediate interrupt.

## What Words Are Fillers?

We have about 100 filler words including:

**Affirmations:** yeah, yep, yes, okay, ok, sure, right, alright, cool, nice, good, great

**Backchannels:** hmm, mm, mhm, uh-huh, aha, oh

**Hesitations:** uh, um, er, eh

**International variants:** ja (German), si (Spanish), oui (French), hai (Japanese)

We also use pattern matching for variants like:
- "mhm", "mm-hmm", "mmhm", "mm hm" → all match
- "uh-huh", "uhuh", "uh huh" → all match
- "yeah", "yea", "yah", "ya" → all match

## How to Use

### Basic Usage
The filter is automatically integrated into the agent. Just run:
```bash
python demo_agent.py dev
```

### Custom Filler Words
Want to add your own filler words?

```python
session = AgentSession(
    vad=silero.VAD.load(),
    stt=openai.STT(),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=openai.TTS(),
    filler_words=["totally", "absolutely", "for sure"],  # Your custom words
)
```

### How It Works in Code

```python
from livekit.agents.voice import InterruptionFilter, FilterDecision

# Create the filter
filter = InterruptionFilter()

# User starts speaking while agent is talking
filter.on_speech_start(agent_is_speaking=True)  # Filter activates

# STT gives us words
filter.on_transcript_update("okay")      # Returns WAIT (filler)
filter.on_transcript_update("okay yeah") # Returns WAIT (still fillers)
filter.on_transcript_update("okay yeah wait") # Returns INTERRUPT! (wait is not a filler)

# If user stops and all were fillers
filter.on_speech_end()  # Returns IGNORE - drop everything
```

## Files We Changed

| File | What It Does |
|------|--------------|
| `interruption_filter.py` | The brain - stores words, checks fillers, makes decisions |
| `agent_activity.py` | Integration - only tells LLM when filter says INTERRUPT |
| `audio_recognition.py` | Hooks into the audio pipeline |
| `test_interruption_filter.py` | Tests all the scenarios |

## Technical Stuff (If You're Curious)

- No VAD modification at all - this is a pure logic layer on top
- Zero latency impact - just string matching, no ML calls
- Works with any STT service (tested with OpenAI Whisper, Deepgram)
- Filter is stateful - tracks everything from speech start to speech end

## Run Tests

```bash
cd livekit-agents
python -m pytest tests/test_interruption_filter.py -v
```

All tests verify the core scenarios plus edge cases like punctuation handling, case insensitivity, and filter state resets.

---

That's it! The agent now knows the difference between you just saying "yeah" to show you're listening vs actually wanting to say something. Pretty cool right?
