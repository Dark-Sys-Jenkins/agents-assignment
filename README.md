# Smart Voice Agent with Context-Aware Interruption Handling

This project implements a **voice-based AI agent** using **LiveKit Agents** that supports **semantic interruption handling**.  
The agent can distinguish between *acknowledgment words* (e.g. “yeah”, “ok”) and *actual user intent*, allowing for **natural backchanneling without unwanted pauses**.

---

## Problem Statement

In standard voice agent pipelines, **any detected user speech** (via VAD or STT) is treated as an interruption.  
This causes the agent to:

- Pause or stop when the user says filler words
- Break conversational flow
- Require delay-based resume hacks
- Exhibit race conditions between STT, VAD, and TTS

---

## Solution Overview

This implementation uses **manual turn detection** combined with **semantic transcript classification**.

Key idea:

> **Interruptions are decided by intent, not by audio detection.**

The agent:
- Receives transcripts continuously
- Classifies them into semantic categories
- Explicitly decides when to commit a user turn

Only a committed turn can interrupt the agent.

---

## Features

- Manual turn detection (`turn_detection="manual"`)
- Zero interruption for acknowledgment words while agent is speaking
- Immediate interruption for command words
- Normal response behavior when agent is silent
- Deterministic, event-driven control flow
- No VAD-triggered pauses
- No resume or delay-based hacks

---

## Transcript Classification

User transcripts are classified into three types:

| Type | Description | Examples |
|----|----|----|
| ACKNOWLEDGMENT | Backchanneling / active listening | yeah, ok, mm-hmm |
| INTERRUPT | Explicit stop or correction | stop, wait, cancel |
| MESSAGE | Normal user input | full sentences |

Classification priority:
1. INTERRUPT
2. ACKNOWLEDGMENT
3. MESSAGE

---

## Interruption Decision Logic

| Transcript Type | Agent Speaking | Action |
|---|---|---|
| ACKNOWLEDGMENT | Yes | Ignore |
| ACKNOWLEDGMENT | No | Commit turn |
| INTERRUPT | Yes / No | Commit turn |
| MESSAGE | Yes / No | Commit turn |

---

## Architecture

User Audio
->
Speech-to-Text (STT)
->
TranscriptAnalyzer
->
AgentStateManager
->
InteractionController
->
commit_user_turn() ← only interruption mechanism
