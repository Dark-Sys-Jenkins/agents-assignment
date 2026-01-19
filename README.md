Interrupt Handling for LiveKit Voice Agent

Overview
This project enhances a LiveKit-based voice agent with robust interrupt-handling logic.
The agent can intelligently differentiate between filler acknowledgements and true interruptions,
ensuring a natural conversational flow without unintended pauses.

Features Implemented

1. Ignore While Speaking
While the agent is actively speaking, short acknowledgements such as:
- "yeah"
- "right"
- "okay"

are ignored and do not interrupt the agent’s speech.

2. Respond When Silent
When the agent is not speaking, the same phrases are treated as valid user input,
allowing the conversation to continue naturally.

3. Explicit Interrupt Handling
Commands such as:
- "stop"
- "pause"
- "wait"

immediately interrupt and stop the agent’s speech.


Key Logic Components:

`IGNORE_WORDS`: Phrases treated as filler acknowledgements
`INTERRUPT_WORDS`: Explicit commands to stop speech

- `on_final_transcript`:

	to create the logic control for ignore, interrupt and silent. 
	Handles real-time STT events and decides whether the agent should: Ignore input, Interrupt speech, Accept normal user input

- `on_end_of_turn`:

	to finetune such that ignore doesn't have a long pause.
	Controls whether a user turn should be considered complete or ignored at the dialogue level.


Behavior Scenarios Covered:

User says "yeah" while agent is speaking Agent continues speaking 
User says "yeah" while agent is silent Agent responds 
User says "stop" at any time Agent stops immediately 

How to Run:

set your livkit url, apikey and secret and on the terminal run,
python examples/voice_agents/basic_agent.py 
recommended to use the LivKit Agent Playground.