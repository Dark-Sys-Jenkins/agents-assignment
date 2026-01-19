# LiveKit Intelligent Interruption Handler

## How to Run the Agent

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the agent
python main.py


How the Logic Works?

This agent prevents unwanted interruptions when the user says backchannel words
like “yeah” or “ok” while the agent is speaking.

Rules

When the agent is speaking:

Voice Activity Detection (VAD) interruptions are bypassed

Backchannel words are ignored

Random words are ignored

Only explicit interrupt words (e.g. “stop”, “wait”) stop the agent

When the agent is silent:

All user input is processed normally

Implementation Summary

The agent tracks whether it is currently speaking.

VAD interrupt signals are ignored while speaking to avoid pauses.

Speech-to-text is used only to detect explicit interrupt commands.

Audio generation continues seamlessly until a stop command is detected.
