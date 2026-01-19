# LiveKit Voice Agent – Backchannel-Safe Conversation Flow

## Overview

This project implements a **real-time voice assistant** using **LiveKit Agents**, **OpenAI STT & TTS**, and **Silero VAD**, with a focus on solving a common voice-AI problem:

> Backchannel or filler words like **“yeah”**, **“ok”**, or **“hmm”** should **not** pause the agent, restart sentences, or trigger new responses.

The final code ensures **smooth, natural conversation** where the agent continues speaking unless the user clearly intends to interrupt.

---

## Problem Statement

In a typical real-time voice pipeline:
- STT converts every sound into text
- Even short acknowledgements are treated as user input
- This causes the agent to:
  - Pause mid-sentence
  - Restart responses
  - Call the LLM unnecessarily

This breaks conversational flow and feels unnatural.

---

## Solution Approach

The solution is implemented **at the session and transcript-handling level**, not just through prompts.

### Key Ideas
1. **Backchannel words are not intent**
2. **Only semantic commands should interrupt**
3. **LLM should not be called while the agent is speaking**
4. **Greeting should not create a new LLM turn**

---

## Process Steps

### 1. Session Setup
- Use:
  - OpenAI STT for speech recognition
  - OpenAI TTS for speech synthesis
  - Silero VAD for voice activity detection
- Disable speculative behavior:
  - `preemptive_generation = False`

---

### 2. Agent Greeting
- On user connection, the agent immediately says:
  > **“Hey, how can I help you?”**
- Implemented using `on_enter()` and `session.say()`
- This avoids creating an unnecessary LLM turn

---

### 3. Backchannel Filtering
A fixed set of filler words (e.g. *yeah, ok, hmm*) is defined.

When a transcript arrives:
- If it contains **only backchannel words** → **ignore completely**
- Do **not** interrupt
- Do **not** call the LLM

---

### 4. Interrupt Handling
- Interruptions are allowed **only** when:
  - The agent is speaking **and**
  - The transcript contains explicit command words (e.g. *stop*, *wait*, *pause*)

This ensures:
- Natural acknowledgements don’t break speech
- Real interruptions still work instantly

---

### 5. LLM Invocation Rules
`session.generate_reply()` is called **only when**:
- The agent is **not speaking**
- The user input is **not a backchannel**
- The input contains meaningful intent

This prevents sentence restarts and audio hiccups.

---

## Outcome

After applying these steps, the agent behavior is:

| User Action | Agent Behavior |
|-----------|----------------|
Says “yeah” / “ok” | Ignored, no pause |
Says filler while agent speaks | Agent continues naturally |
Says “stop” or “wait” | Agent interrupts immediately |
Asks a question | Agent responds normally |
Joins the room | Agent greets automatically |

---

## Result

- No pauses caused by backchannel words  
- No sentence restarts  
- No unnecessary LLM calls  
- Natural, human-like conversation flow  

This makes the agent suitable for **production-grade real-time voice applications** using LiveKit Cloud.

---

## Summary

This project demonstrates how **careful session-level control**—rather than relying only on prompts—can significantly improve conversational quality in voice agents. By separating **acknowledgements** from **intent**, the final system delivers a smooth and realistic voice interaction experience.
