# Intelligent Interruption Handler

## Overview

This implementation adds a context-aware interruption handling system to the LiveKit voice agent. It distinguishes between passive acknowledgements (backchanneling) and active interruptions, preventing the agent from stopping when users say filler words like "yeah", "ok", or "hmm" while the agent is speaking.

## Problem Statement

Previously, LiveKit's Voice Activity Detection (VAD) was too sensitive to user feedback. When users said backchanneling words like "yeah", "ok", or "hmm" to indicate they were listening, the agent would interpret this as an interruption and abruptly stop speaking.

## Solution

The solution implements a logic layer that:

1. **Defers interruptions** when VAD detects speech while the agent is speaking
2. **Validates with STT** (Speech-to-Text) to determine if the user input is a soft word (backchanneling) or a real interruption
3. **Ignores soft words** when the agent is speaking, allowing seamless continuation
4. **Processes soft words normally** when the agent is silent, treating them as valid user input

## Core Logic Matrix

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah" / "Ok" / "Hmm" | Speaking | **IGNORE**: Agent continues speaking without pausing or stopping |
| "Wait" / "Stop" / "No" | Speaking | **INTERRUPT**: Agent stops immediately and listens |
| "Yeah" / "Ok" / "Hmm" | Silent | **RESPOND**: Agent treats this as valid input (e.g., "Great, let's continue.") |
| "Start" / "Hello" | Silent | **RESPOND**: Normal conversational behavior |

## Key Features

### 1. Configurable Ignore List

Soft words (backchanneling) are defined in `agent_session.py` and can be customized via environment variables:

```python
# Default soft words
SOFT_WORDS = {"yeah", "ok", "okay", "hmm", "uh-huh", "aha", "right", "mhm", "yep", "sure"}

# Default hard interrupt words
HARD_INTERRUPT_WORDS = {"stop", "wait", "cancel", "hold", "hold on", "no", "don't", "dont"}
```

**Environment Variable Configuration:**

You can override these lists using environment variables:

```bash
# Set soft words (comma-separated)
export SOFT_WORDS="yeah,ok,okay,hmm,uh-huh,aha,right,mhm,yep,sure"

# Set hard interrupt words (comma-separated)
export HARD_INTERRUPT_WORDS="stop,wait,cancel,hold,hold on,no,dont"
```

### 2. State-Based Filtering

The filter only applies when the agent is actively generating or playing audio. When the agent is silent, all user input (including soft words) is processed normally.

### 3. Semantic Interruption Detection

If the user says a mixed sentence like "Yeah wait a second," the system detects the command word ("wait") and interrupts the agent, even if soft words are present.

### 4. No VAD Modification

This is implemented as a logic handling layer within the agent's event loop, without modifying the low-level VAD kernel.

## Technical Implementation

### Architecture

The solution works by:

1. **Pending Interrupt Flag**: When VAD detects speech while the agent is speaking, a `_pending_interrupt` flag is set instead of immediately interrupting.

2. **STT Validation**: The `_user_input_transcribed` handler validates the transcript:
   - If it contains only soft words → ignore and continue speaking
   - If it contains hard interrupt words → execute the interruption
   - If it's mixed → execute the interruption (err on the side of caution)

3. **Deferred Interruption**: The `_interrupt_by_audio_activity` method checks for pending interrupts and defers execution until STT validation is complete.

### Code Flow

```
User speaks while agent is speaking
    ↓
VAD detects speech → on_start_of_speech
    ↓
_set_pending_interrupt = True (defer interruption)
    ↓
STT provides transcript → _user_input_transcribed
    ↓
Check if soft words only?
    ├─ Yes → Ignore, clear pending interrupt, continue speaking
    └─ No → Execute interrupt, clear pending interrupt
```

### Key Files Modified

1. **`agent_session.py`**:
   - Added `SOFT_WORDS` and `HARD_INTERRUPT_WORDS` configuration
   - Modified `_update_user_state` to set pending interrupt flag
   - Enhanced `_user_input_transcribed` to validate and handle soft words

2. **`agent_activity.py`**:
   - Modified `_interrupt_by_audio_activity` to defer interruption when pending interrupt is set

## Example Scenarios

### Scenario 1: The Long Explanation
- **Context**: Agent is reading a long paragraph about history
- **User Action**: User says "Okay... yeah... uh-huh" while Agent is talking
- **Result**: ✅ Agent audio does not break. It ignores the user input completely.

### Scenario 2: The Passive Affirmation
- **Context**: Agent asks "Are you ready?" and goes silent
- **User Action**: User says "Yeah."
- **Result**: ✅ Agent processes "Yeah" as an answer and proceeds (e.g., "Okay, starting now").

### Scenario 3: The Correction
- **Context**: Agent is counting "One, two, three..."
- **User Action**: User says "No stop."
- **Result**: ✅ Agent cuts off immediately.

### Scenario 4: The Mixed Input
- **Context**: Agent is speaking
- **User Action**: User says "Yeah okay but wait."
- **Result**: ✅ Agent stops (because "but wait" contains interrupt words).

## Testing

To test the implementation:

1. **Test Soft Words During Agent Speech**:
   - Start the agent and have it speak a long response
   - While it's speaking, say "yeah", "ok", or "hmm"
   - Verify the agent continues speaking without interruption

2. **Test Soft Words When Agent is Silent**:
   - Wait for the agent to finish speaking
   - Say "yeah" or "ok"
   - Verify the agent responds appropriately

3. **Test Hard Interrupt Words**:
   - Start the agent speaking
   - Say "stop" or "wait"
   - Verify the agent stops immediately

4. **Test Mixed Input**:
   - Start the agent speaking
   - Say "yeah wait" or "ok but stop"
   - Verify the agent stops (interrupt words take precedence)

## Configuration

The system uses the following session options (already present in LiveKit):

- `allow_interruptions`: Whether interruptions are allowed (default: `True`)
- `discard_audio_if_uninterruptible`: Whether to discard audio when agent can't be interrupted (default: `False`)
- `false_interruption_timeout`: Timeout for false interruption detection (default: `None`)

The intelligent interruption handler works within these existing options and doesn't require additional configuration beyond the environment variables for soft/hard word lists.

## Latency Considerations

The solution maintains real-time performance by:

- Using async/await patterns for non-blocking operations
- Deferring interruption decisions only when necessary (agent speaking + user speaking)
- Processing transcripts as they arrive (interim and final)
- Making decisions on final transcripts to avoid false positives

The delay to determine if a word is "valid" or "ignored" is imperceptible because:
- VAD detection is immediate (sets pending flag)
- STT transcription happens in parallel
- Decision is made as soon as final transcript arrives
- No blocking operations in the critical path

## Future Enhancements

Potential improvements:

1. **Machine Learning**: Use ML to classify backchanneling vs. real interruptions
2. **Context Awareness**: Consider conversation context when determining interruption intent
3. **Multi-language Support**: Extend soft word lists to other languages
4. **Confidence Thresholds**: Use STT confidence scores to improve decision accuracy
5. **Customizable Timeouts**: Add configurable timeout for pending interrupt validation

## Troubleshooting

### Agent Still Interrupts on Soft Words

- Check that `allow_interruptions` is `True`
- Verify STT is working correctly (check logs for transcript events)
- Ensure the soft words are in the `SOFT_WORDS` set (case-insensitive matching)

### Agent Doesn't Respond to Soft Words When Silent

- This is expected behavior - soft words should be processed normally when agent is silent
- Check that the agent state is correctly tracked
- Verify user state transitions are working

### Interruptions Are Delayed

- This is by design - interruptions are deferred until STT validation
- If delays are too long, check STT latency
- Consider using faster STT models for lower latency

## License

This implementation is part of the LiveKit Agents framework and follows the same license terms.
