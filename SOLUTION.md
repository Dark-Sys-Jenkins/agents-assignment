# Intelligent Interruption Handler – Solution Documentation

**Author:** Yash Mishra  
**GitHub:** @YashMishra0306  
**Branch:** `feature/interrupt-handler-YashMishra0306`

---

## Problem Statement

While working with LiveKit voice agents, I observed an issue with how interruptions are handled during conversations.

If the agent is speaking and the user says short acknowledgment phrases like **“yeah”**, **“ok”**, or **“hmm”**, LiveKit’s default Voice Activity Detection (VAD) treats this as a full interruption and immediately stops the agent. In real conversations, these phrases are usually just backchannel feedback and are not meant to interrupt the speaker.

**Objective:**  
Design a context-aware solution that allows the agent to:
- continue speaking when the user gives passive acknowledgments
- immediately stop when the user clearly intends to interrupt

---

## Solution Overview

To solve this, I implemented a **state-aware interruption filtering layer** that operates *on top of* LiveKit’s existing VAD.

Instead of modifying the VAD itself, the solution:
- waits for speech-to-text (STT) transcription
- analyzes the actual content of what the user said
- checks whether the agent is currently speaking
- decides whether the input should be ignored or treated as a real interruption

This approach keeps the system clean, modular, and easy to maintain.

---

## Architecture

User Speech
↓
VAD detects speech
↓
STT transcription
↓
InterruptionHandler (custom logic)
↓
Decision:

-IGNORE → agent continues speaking
-PROCESS → agent stops and responds


The key idea is that **not every detected speech event should interrupt the agent**.

---

## Implementation Details

### InterruptionHandler Class

**File:** `examples/voice_agents/basic_agent.py`

This class is responsible for all interruption-related decisions.

**Main responsibilities:**
- Track whether the agent is currently speaking
- Identify filler / acknowledgment phrases
- Detect explicit interruption commands
- Decide whether a user utterance should be ignored

**Key attributes:**
- `ignore_phrases`: filler words like “yeah”, “ok”, “hmm”
- `interrupt_keywords`: command words like “stop”, “wait”, “hold on”
- `agent_is_speaking`: boolean flag representing agent state

---

### Agent State Tracking

The handler listens to agent lifecycle events:

- `agent_speech_started` → `agent_is_speaking = True`
- `agent_speech_stopped` → `agent_is_speaking = False`

This context is essential because the same word can have different meanings depending on whether the agent is speaking or silent.

---

### Speech Event Interception

The logic hooks into the `user_speech_committed` event:
- This event fires after STT transcription is complete
- The transcribed text is passed to the interruption handler
- If the handler decides to ignore it, the function returns early
- Otherwise, the agent processes it as a valid interruption

---

## Core Logic

```python
def should_ignore_interruption(text):
    # If the agent is silent, always process user input
    if not agent_is_speaking:
        return False

    # Explicit interruption commands always stop the agent
    if contains_interrupt_keyword(text):
        return False

    # Ignore input if it only contains filler words
    if all_words_are_fillers(text):
        return True

    # Mixed or meaningful input is treated as a real interruption
    return False


Configuration
Filler / Ignore Phrases
self.ignore_phrases = {
    "yeah", "ok", "okay", "hmm", "uh-huh",
    "right", "aha", "mhm", "sure", "yep",
    "got it", "i see", "alright", "uh huh",
    "mm-hmm", "yeah yeah"
}

Interruption Keywords
self.interrupt_keywords = {
    "stop", "wait", "no", "hold", "pause",
    "hold on", "wait a second", "stop that",
    "hang on", "one second"
}


Testing

A dedicated test suite was added in:
File: test_interruption_handler.py
Test Coverage
-18 automated test cases
-All tests pass successfully
Key Scenarios Tested
| Input       | Agent State | Expected Behavior |
| ----------- | ----------- | ----------------- |
| "yeah"      | Speaking    | Ignored           |
| "yeah"      | Silent      | Processed         |
| "stop"      | Speaking    | Interrupt         |
| "yeah wait" | Speaking    | Interrupt         |

Additional tests cover:
-Case insensitivity
-Multiple filler words
-Mixed filler and command input
-Empty and whitespace-only input


Running the Project
Setup
git clone https://github.com/YashMishra0306/agents-assignment.git
cd agents-assignment
git checkout feature/interrupt-handler-YashMishra0306

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .


Environment Variables
Create a .env file in the project root:
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=

Run the Agent
cd examples/voice_agents
python basic_agent.py dev

Run Tests
python test_interruption_handler.py


Design Rationale
Why Not Modify VAD?
-VAD operates at the audio level
-Changing it would affect all speech detection
-This problem is semantic, not acoustic
-A logic-layer solution is safer and more maintainable

Why Use STT-Based Filtering?
-We need to know what the user said, not just that they spoke
-Enables detection of mixed intent (e.g., “yeah but stop”)
-STT latency is acceptable in conversational systems

Why Track Agent State?
-Words like “yeah” are context-dependent
-Timing matters in conversation
-This approach reflects natural human dialogue patterns


Conclusion

This solution addresses a real conversational UX issue without modifying low-level audio components.
It is lightweight, easy to test, and easy to extend.

Most importantly, it allows the voice agent to behave in a more natural and human-like way.
For questions or follow-ups:
GitHub: @YashMishra0306

