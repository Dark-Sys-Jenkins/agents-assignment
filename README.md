# LiveKit Intelligent Interruption Handling

## Problem
LiveKit’s VAD interrupts agent speech on passive acknowledgements like
"yeah" or "ok", breaking conversational flow.

## Solution
A semantic interruption handling layer that delays interruption decisions
until STT text is available, allowing the agent to distinguish between
backchanneling and true interruptions.

## Key Features
- Context-aware interruption handling
- Configurable ignore word list
- Semantic interruption detection
- No modification to LiveKit VAD
- Zero stutter or resume artifacts

## How It Works
1. VAD fires when user speaks
2. Agent audio is NOT stopped immediately
3. System waits briefly for STT text
4. If text is filler → ignored
5. If text contains command → interrupt

## Running the Agent
```bash
pip install -r requirements.txt
python main.py
