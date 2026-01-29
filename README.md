# LiveKit Agents – Turn Interruption Handling Fix

## Overview

This PR improves turn-taking behavior in the LiveKit Agents runtime by preventing
short user backchannels (e.g. “yeah”, “uh-huh”, “okay”) from interrupting an agent’s
speech, while still allowing meaningful user interruptions.

The change results in more natural conversational flow and matches the behavior
expected from production-grade voice assistants.

---

## Problem

In the default configuration, very short user utterances such as:

- “yeah”
- “uh huh”
- “okay”

were causing the agent to stop speaking.

This occurs because turn detection happens at the **audio level** before transcript
callbacks (`on_user_message`) are executed. Filtering text alone is therefore
insufficient, as the interruption has already occurred by the time text handlers run.

---

## Solution

The fix introduces **audio-level interruption gating** using
`min_interruption_duration`.

### Key Configuration

```python
AgentSession(
    min_interruption_duration=0.6,
    ...
)
