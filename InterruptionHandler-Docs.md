# Filler Word Interruption Handler

A built-in AgentSession feature that makes voice agents **ignore filler words** (like "yeah", "ok", "mm-hmm") while still responding to commands and real speech.

## Quick Start

```python
session = AgentSession(
    stt="deepgram/nova-3",
    llm="openai/gpt-4.1-mini",
    tts="cartesia/sonic-2:...",
    vad=silero.VAD.load(),
    
    # Enable filler word filtering
    turn_detection="manual",
    ignore_filler_interruptions=True,
)
```

## How It Works

### The Problem
VAD (Voice Activity Detection) pauses the agent whenever it detects speech. But many utterances like "yeah", "okay", "mm-hmm" are just passive acknowledgements, not real interruptions.

### The Solution
1. `turn_detection="manual"` prevents automatic VAD-triggered pauses
2. `ignore_filler_interruptions=True` enables transcript classification
3. On final transcript:
   - **Filler words** → Ignored, agent continues speaking
   - **Commands/Speech** → `commit_user_turn()` triggers response

### Classification Logic
```python
def _classify_transcript(text, filler_words, command_words) -> str:
    words = set(text.lower().split())
    if command_words and (words & command_words):
        return 'command'
    if filler_words and words.issubset(filler_words):
        return 'filler'
    return 'speech'
```

| Input | Classification | Action |
|-------|---------------|--------|
| "Yeah", "Okay", "Mm-hmm" | filler | Ignored |
| "Wait", "Stop", "No" | command | Interrupts |
| "Tell me more" | speech | Interrupts |

## Default Word Lists

**Filler Words:**
```
yeah, ok, okay, hmm, hmmm, hmmmm, uh-huh, right, aha, ahaa,
mm, mmm, mhm, mhmm, mhmmm, uh, uhh, uhm, um, umm,
yep, yes, sure, got it, i see, aah, aaha, aah-ha
```

**Command Words:**
```
wait, stop, no, hold, pause
```

## Custom Word Lists

```python
session = AgentSession(
    turn_detection="manual",
    ignore_filler_interruptions=True,
    filler_words=["yeah", "ok", "custom"],
    command_words=["wait", "stop", "halt"],
)
```

---

## Files Modified

### 1. `livekit/agents/voice/agent_session.py`

**Added to `AgentSessionOptions` dataclass:**
```python
@dataclass
class AgentSessionOptions:
    # ... existing fields ...
    ignore_filler_interruptions: bool
    filler_words: set[str] | None
    command_words: set[str] | None
```

**Added constructor parameters:**
```python
def __init__(
    # ... existing params ...
    ignore_filler_interruptions: bool = False,
    filler_words: NotGivenOr[list[str] | None] = NOT_GIVEN,
    command_words: NotGivenOr[list[str] | None] = NOT_GIVEN,
):
```

**Added default word lists:**
```python
DEFAULT_FILLER_WORDS: set[str] = {
    "yeah", "ok", "okay", "hmm", "hmmm", "hmmmm", "uh-huh", ...
}
DEFAULT_COMMAND_WORDS: set[str] = {"wait", "stop", "no", "hold", "pause"}
```

---

### 2. `livekit/agents/voice/agent_activity.py`

**Added classification helper:**
```python
def _classify_transcript(
    text: str,
    filler_words: set[str] | None,
    command_words: set[str] | None
) -> str:
    if not text or not text.strip():
        return 'filler'
    words = set(text.lower().replace(",", "").replace(".", "").replace("?", "").split())
    if command_words and (words & command_words):
        return 'command'
    if filler_words and words.issubset(filler_words):
        return 'filler'
    return 'speech'
```

**Modified `on_final_transcript`:**
```python
def on_final_transcript(self, ev, *, speaking=None):
    # ... existing code ...
    
    opt = self._session.options
    
    # FILLER WORD HANDLING
    if self._turn_detection == "manual" and opt.ignore_filler_interruptions:
        transcript = ev.alternatives[0].text
        classification = _classify_transcript(
            transcript, opt.filler_words, opt.command_words
        )
        if classification != 'filler':
            self._session.commit_user_turn()
        return
    
    # ... existing code ...
```

---

## Example: basic_agent.py

```python
@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        
        # FILLER WORD HANDLING
        turn_detection="manual",
        ignore_filler_interruptions=True,
    )
    
    await session.start(agent=MyAgent(), room=ctx.room)
```

---

## Alternative: Manual Handler (Demo)

See `interrupt-handeler-test/voice-agent.py` for a standalone implementation using `ManualTurnHandler` - this demonstrates the solution approach without framework modifications.
