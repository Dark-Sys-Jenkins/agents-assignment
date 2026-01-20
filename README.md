# Intelligent Interruption Handling for Voice Agents

For salescode.ai, the project implements a layer between the agent, which classifies user input text based on context
Here's a link to the demo: https://youtu.be/6qzTORLv35s
## Problem

Standard voice agents treat all user speech the same way. When a user says "yeah" or "uh-huh" while the agent is speaking, the agent stops and tries to respond. This creates an unnatural conversation flow since these are just acknowledgements, not requests for a response.

## Solution

The implementation classifies user utterances into three categories:

1. **Backchannels** - Passive acknowledgements like "yeah", "ok", "uh-huh", "mm-hmm"
2. **Commands** - Explicit interruption requests like "stop", "wait", "hold on", "no"
3. **Other content** - Genuine new input that warrants a response

### Behavior

| Agent State | User Says | Action |
|-------------|-----------|--------|
| Speaking | "yeah", "ok", "hmm" | Ignore (continue speaking) |
| Speaking | "stop", "wait", "no" | Interrupt and stop |
| Speaking | "actually I have a question" | Interrupt and respond |
| Listening | "yeah", "ok" | Ignore (no response needed) |
| Listening | Any other input | Respond normally |

## Files

```
examples/voice_agents/
    intelligent_interruption_agent.py   # Main agent implementation
    interruption_classifier.py          # Utterance classification logic

tests/
    test_intelligent_interruption.py    # Integration tests
    test_interruption_classifier.py     # Unit tests for classifier
```

## How It Works

### 1. Classifier (`interruption_classifier.py`)

The `InterruptionClassifier` takes a transcript and returns one of three intents:

```python
class InterruptionIntent(Enum):
    IGNORE_BACKCHANNEL = "ignore_backchannel"
    INTERRUPT_COMMAND = "interrupt_command"
    INTERRUPT_OTHER = "interrupt_other"
```

Classification logic:
1. Check if transcript contains a command phrase (highest priority)
2. Check if transcript consists only of backchannel words
3. Otherwise, treat as new content

The classifier normalizes text (lowercase, remove punctuation) and uses regex for matching.

### 2. Handler (`intelligent_interruption_agent.py`)

The handler listens to `user_input_transcribed` events and decides what to do:

```python
def on_user_input_transcribed(ev):
    intent = classifier.classify(ev.transcript)
    
    if session.agent_state == "speaking":
        if intent == IGNORE_BACKCHANNEL:
            session.clear_user_turn()  # Ignore
        elif intent == INTERRUPT_COMMAND:
            session.interrupt(force=True)
            session.clear_user_turn()  # Stop but don't respond
        elif intent == INTERRUPT_OTHER:
            session.interrupt(force=True)  # Stop and respond
```

### 3. Session Configuration

Two critical settings make this work:

```python
session = AgentSession(
    allow_interruptions=False,              # Disable automatic interruptions
    discard_audio_if_uninterruptible=False, # Keep processing audio while speaking
)
```

## Customization

You can customize the word lists in `InterruptionClassifierConfig`:

```python
config = InterruptionClassifierConfig(
    backchannel_words={"yeah", "ok", "uh-huh", ...},
    command_phrases={"stop", "wait", "hold on", ...},
    interrupt_on_non_backchannel=True,  # Whether non-backchannels should interrupt
)
```

The default lists include English and some Hindi words.

## Running

```bash
# Set environment variables
export DEEPGRAM_API_KEY=your_key
export GOOGLE_API_KEY=your_key

python examples/voice_agents/intelligent_interruption_agent.py console

## Dependencies

- LiveKit Agents framework
- Deepgram (STT and TTS)
- Google Gemini (LLM)
- Silero VAD
