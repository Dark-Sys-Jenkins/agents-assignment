# LiveKit Agents – Turn Interruption Handling Fix

## Overview

This PR improves turn-taking behavior in the LiveKit Agents runtime by preventing
short user backchannels (e.g. “yeah”, “uh-huh”, “okay”) from interrupting an agent’s
speech, while still allowing meaningful user interruptions.

The fix aligns with production voice-assistant behavior and avoids premature
speech cancellation caused by brief acknowledgements.

---

## Problem

In the default configuration, very short user utterances such as:

- “yeah”
- “uh huh”
- “okay”

were triggering interruptions because turn detection occurs before transcript
handlers (`on_user_message`) are invoked.

Filtering these messages at the text level alone is insufficient, as the agent
speech is already interrupted by the time the handler runs.

---

## Solution

The solution introduces **interruption gating at the audio level** using
`min_interruption_duration`.

### Key Change

```python
AgentSession(
    min_interruption_duration=0.6,
    ...
)
