# LiveKit Voice Agent: Intelligent Interruption Layer

A custom wrapper for LiveKit's `AgentSession` that solves the "over-sensitive interruption" problem. It distinguishes between **Backchanneling** (meaningless filler words like "yeah", "uh-huh") and **True Interruptions** (commands like "stop", "wait").

## 🚀 Quick Start

### 1. Setup

Ensure your custom classes (`IntelligentInterruptSession` and `CustomAgentActivity`) are saved in a file named `interrupt_layer.py`.

### 2. Implementation

Replace your standard `AgentSession` with `IntelligentInterruptSession`.

```python
from interrupt_layer import IntelligentInterruptSession
from livekit.agents import JobContext, WorkerOptions

async def entrypoint(ctx: JobContext):
    # Initialize the session with your custom logic
    session = IntelligentInterruptSession(
        interrupt_words={"stop", "wait", "hold", "cancel"},  # Force stop words
        ignored_words={"yeah", "ok", "hmm", "right", "uh-huh"} # Backchannel words
    )
    
    # Start your agent as normal
    await session.start(ctx, ...)

```

## ⚙️ How It Works

This implementation overrides two critical lifecycle methods in `AgentActivity` to filter user input before it triggers a reaction.

### 1. The Audio Interruption Guard (`_interrupt_by_audio_activity`)

**Standard Behavior:** Any VAD (Voice Activity Detection) trigger immediately stops the agent's audio.
**Custom Behavior:** * When VAD triggers, we peek at the STT (Speech-to-Text) transcript.

* If the transcript contains **only** words from the `ignored_words` list, we **block the interruption**. The agent continues speaking over the user.
* If the transcript contains any word from `interrupt_words`, we force an immediate stop.

### 2. The LLM Generation Guard (`on_end_of_turn`)

**Standard Behavior:** Even if we ignore the audio interruption, the standard system would still send "Yeah" to the LLM. The LLM would then awkwardly reply "Yes?" or "Go on" after the agent finishes speaking.
**Custom Behavior:** * We intercept the final turn event.

* If the user text matches the ignore list, we **return `False**`, effectively deleting the turn. The LLM never sees the "Yeah," and no ghost reply is generated.

## 🛠 Configuration

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `ignored_words` | `Set[str]` | `{'yeah', 'ok', ...}` | Words that will NOT stop the agent and will NOT be sent to the LLM. |
| `interrupt_words` | `Set[str]` | `{'stop', 'wait', ...}` | Words that trigger an immediate hard stop, regardless of surrounding noise. |
