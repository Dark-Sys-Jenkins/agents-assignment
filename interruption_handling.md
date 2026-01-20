# Intelligent Interruption Handling

## Overview
This change adds a state-aware interruption filter for a LiveKit voice agent.
The goal is to prevent passive acknowledgements like “yeah”, “ok”, or “hmm” from
interrupting the agent while it is speaking, while still allowing real commands
such as “stop” or “wait” to interrupt immediately.

The solution works purely at the AgentSession level and does not modify LiveKit’s
VAD or any low-level audio behavior.


## Why this approach
I first looked at `basic_agent.py`, where the interruption issue can also be observed.
However, that file is meant to be a minimal demo of default agent behavior.

I chose to implement the logic in `resume_interrupted_agent.py` because it already
focuses on interruption handling and exposes the relevant AgentSession events and
SpeechHandle needed to reason about interruptions cleanly.


## Core idea: state awareness
The key idea is to make interruption handling depend on whether the agent is
currently speaking.

A simple flag (`agent_speaking`) is updated using the `agent_state_changed` event.
All filtering logic is gated on this state, so the same user input can be treated
differently depending on whether the agent is speaking or silent.


## Strict requirement: no pause, no stutter
When the agent is speaking and the user says only filler words, the input is ignored
completely using an early return.

Because no interrupt, pause, or resume call is issued in this path, the audio stream
is never touched. As a result, the agent continues speaking seamlessly, without
breaking, restarting, or stuttering.

This directly satisfies the strict requirement of the challenge.


## Active and mixed interruptions
If the user transcript contains an actual interrupt command such as “stop”, “wait”,
or “no”, the agent is interrupted immediately using the active `SpeechHandle`.

Mixed inputs like “yeah wait” are handled correctly as well. Even though a filler
word is present, the interrupt keyword takes priority and triggers an interruption.


## Silent agent behavior
When the agent is not speaking, the interruption filter does not apply. In this
state, short acknowledgements like “yeah” are treated as valid input and handled
normally by the agent.

## Configurability and code structure
The ignore list and interrupt keywords are defined as simple sets in one place,
making them easy to adjust or extend without changing the control flow.

This keeps the logic modular and makes it straightforward to add new filler words
or commands if needed.


## No VAD modification
This solution does not modify LiveKit’s VAD or any low-level audio processing.
It is implemented entirely as a lightweight logic layer using existing
AgentSession hooks and STT transcripts.


## Proof video
A short walkthrough video demonstrating the logic and explaining why filler words
cannot cause pauses or stutters is available here:

-> [View proof video](https://drive.google.com/file/d/18m9-Ah31Ahb8IuabSOsOcktm-xLhXW1t/view?usp=sharing)


The video walks through the relevant code paths and explains how each test case from
the assignment is handled.
