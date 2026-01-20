# Context-Aware Interruption Handling for LiveKit Voice Agents

##  Overview

In real conversational settings, users often speak short acknowledgement words such as:

- “okay”
- “yeah”
- “uh-huh”
- “hmm”

while an AI agent is speaking.
These words are not intended to interrupt, but LiveKit’s default Voice Activity Detection (VAD) triggers on any audio activity.

## 1. Observed Problem

When the agent is speaking and the user says a filler word:

- The agent pauses or stops
- Speech may restart from the beginning
- Audio segments may close incorrectly
- Logs show errors such as resume called after close

This results in a broken conversational experience.

## 2. Objective

Implement a context-aware interruption handling system that:

- Ignores backchannel words while the agent is speaking
- Allows real interruption commands like:
    - “stop”
    - “wait”
    - “no”
- Works in real time
- Does not modify VAD
- Avoids pause/resume hacks or speculative interruption

## 3. High-Level Architecture

User audio
   ↓
VAD fires (signal only)
   ↓
Interim transcript (display only)
   ↓
Final transcript
   ↓
Semantic decision:
   ├─ Backchannel → ignore
   ├─ Interrupt command → interrupt
   └─ Normal input → respond

There is exactly one decision point.

## 4. Backchannel Filtering Logic

A dedicated logic layer (BackchannelFilter) classifies user input into:
A. Backchannel (ignore while agent is speaking)
Examples:
“okay”, “yeah”, “uh-huh”, “mm”

B. Interruption commands
Examples:“stop”, “wait”, “hold on”, “no”

C. Mixed input
Example:“yeah okay but wait” → interrupt

## 5. Context Awareness

Backchannel filtering is applied only when the agent is speaking.

Agent State |	User Input	      |     Behavior    
Speaking	|“okay”	              |   Ignore
Speaking	|“wait”	              |   Interrupt
Speaking	|“yeah okay  but wait”|	  Interrupt
Silent	    |“okay”	              |   Normal response

## 6. Implementation Details

### Key Changes
1. _interrupt_by_audio_activity

- Reduced to a VAD-only signal
- No transcript inspection
- No pause / resume
- No interruption logic

2. on_final_transcript

- Single authority for interruption decisions
- Uses BackchannelFilter
- Commits user input only after filtering
- No timers or speculative state

3. BackchannelFilter

- Normalizes text
- Separates backchannels from interrupt commands
- Handles mixed utterances correctly

4. Example Interrupt Handler

Added under examples/voice_agents/interrupt_handler.py

Demonstrates behavior without modifying core logic

## 7. Files Modified / Added
File	                        Description
agent_activity.py	            Centralized interruption logic
agent_session.py	            Configuration support
backchannel_filter.py	        Semantic filtering logic
examples/interrupt_handler.py	Demonstration example

## 8. Test Cases 

###  Test Case 1: Backchannel While Agent Speaks

Agent: Explaining a long topic
User: “okay”, “uh-huh”
Result: Agent continues speaking ✔

###  Test Case 2: Interruption Command

Agent: Speaking
User: “stop”
Result: Agent stops immediately ✔

### Test Case 3: Mixed Input

Agent: Speaking
User: “yeah okay but wait”
Result: Agent interrupts ✔

### Test Case 4: Backchannel While Agent Silent

Agent: Silent
User: “okay”
Result: Agent responds normally ✔

## 9. Conclusion

This solution fixes the interruption problem at the architectural level, not by patching symptoms.
By:

- Separating signal detection from semantic intent
- Using final transcripts as the decision boundary
- Eliminating speculative interruption

the agent achieves stable, natural, human-like conversation behavior.

## 12. Run the Example and test the model
- python examples/voice_agents/basic_agent.py
- python examples/voice_agents/interrupt_handler.py




