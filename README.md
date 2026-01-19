# Semantic Interruption Handling for Backchannel Speech

## Overview

This project implements a context-aware interruption handling mechanism for a real-time
voice AI agent. The goal is to distinguish **passive acknowledgements** (backchannel speech
such as "yeah", "ok", "hmm") from **active interruptions** (commands like "stop", "wait")
while the agent is speaking.

The implementation ensures that the agent continues speaking seamlessly during passive
acknowledgements and only interrupts when the user provides a meaningful command.

---

## Problem Statement

The default Voice Activity Detection (VAD) behavior is overly sensitive.  
When the agent is speaking and the user provides short feedback like:

- "yeah"
- "ok"
- "hmm"

the agent incorrectly treats this as an interruption and stops speaking abruptly.

This results in poor conversational flow and unnatural interactions.

---

## Solution Approach

A **semantic interruption filter** was added as a logic layer **above VAD and after STT**.

### Key Ideas:
- VAD detects sound but does not understand meaning
- STT provides semantic information (text)
- Interruption decisions should be based on **transcribed text**, not raw audio

The solution evaluates:
1. Whether the agent is currently speaking
2. The semantic meaning of the user transcript

---

## Core Logic

### While the agent is speaking:
- Ignore filler / backchannel words  
  (`"yeah"`, `"ok"`, `"hmm"`, `"uh-huh"`, etc.)
- Immediately interrupt on semantic commands  
  (`"stop"`, `"wait"`, `"no"`, `"pause"`)
- Interrupt on mixed inputs (e.g. `"yeah wait"`)

### While the agent is silent:
- Treat all user input as valid and respond normally

---

## Implementation Details

- A helper function `should_interrupt(...)` determines whether interruption should occur
- The transcription output stream is wrapped to filter backchannel speech
- Agent speaking state is detected using active TTS playback
- No modification was made to the VAD kernel
- No pause/resume or stutter is introduced
- The solution is real-time safe with no artificial latency

---

## Test Scenarios

| Scenario | Expected Behavior |
|--------|------------------|
| Agent speaking + "yeah / ok / hmm" | Agent continues speaking |
| Agent speaking + "stop / wait" | Agent stops immediately |
| Agent speaking + "yeah wait" | Agent stops |
| Agent silent + "yeah" | Agent responds normally |

---

## Requirements Satisfied

- ✅ No modification to low-level VAD
- ✅ Context-aware interruption handling
- ✅ Seamless agent speech (no hiccups or pauses)
- ✅ Real-time safe implementation
- ✅ Modular and configurable logic

---

## How to Run

This repository uses a fake session and test harness to simulate real-time agent behavior.
The implemented logic is exercised through the provided test scenarios.

No additional setup is required beyond the existing repository instructions.

---

## Summary

This implementation improves conversational quality by making the agent behave more
human-like, ignoring passive acknowledgements while speaking and responding correctly
to real interruptions.

