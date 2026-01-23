## Intelligent Interruption Handling

This repository includes a context-aware intelligent interruption handler
implemented as part of a campus assignment.

### Behavior
- While the agent is speaking, passive acknowledgements such as "yeah",
  "ok", and "hmm" are ignored so the agent continues speaking naturally.
- Explicit commands like "stop" or "wait" immediately interrupt the agent.
- When the agent is not speaking, short responses such as "yeah" are treated
  as valid user input and are not ignored.

### Implementation Details
- Implemented as a modular handler (`IntelligentInterruptionHandler`)
- Attached at session creation time
- Logic is state-aware and does not modify the VAD
- Ignored and interrupt words are configurable via simple word lists

### Running the Agent
Running the agent locally without LiveKit credentials may result in an
expected error: "cannot simulate job, the worker is closed".
This is unrelated to the interruption logic and does not affect correctness.
