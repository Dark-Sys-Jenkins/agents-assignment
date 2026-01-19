#  LiveKit Intelligent Interruption Handler

 **Smarter conversations for voice agents**

This repository contains an enhanced version of the **LiveKit AI Agent**, specifically designed to handle conversational flow more naturally by distinguishing between **backchanneling** (passive fillers) and **active interruptions**.

---

##  The Challenge

Default **Voice Activity Detection (VAD)** systems are often *too sensitive*.  
They tend to interrupt the agent when users provide passive feedback such as:

> “yeah”, “uh-huh”, “hmm”

These utterances are not commands, but acknowledgments. Interrupting on them breaks conversational flow and makes agents feel unnatural.

---

## The Solution

This implementation introduces a **context-aware interruption layer** that allows the agent to:

-  Continue speaking during passive acknowledgments  
-  Immediately stop when the user issues a real command  
-  Correctly respond to short answers when the agent is silent  

The result is a **far more human-like voice interaction**.

---

## Implementation Logic

### State-Based Filtering

The system continuously monitors the agent’s internal `agent_state`.

- **Agent Speaking**
  - Soft inputs (fillers) → **Ignored**
  - Active commands → **Immediate interruption**

- **Agent Silent**
  - All inputs are treated as valid conversational turns  
  - Short replies like *“Yeah”* still receive a response

---

### Intelligent Intent Classification

A custom `_classify_interrupt_intent` function evaluates user transcripts using the matrix below:

| User Input            | Agent State | Desired Behavior |
|----------------------|-------------|------------------|
| “Yeah / Ok / Hmm”    | Speaking    | IGNORE – agent continues |
| “Wait / Stop / No”   | Speaking    | INTERRUPT immediately |
| “Yeah / Ok / Hmm”    | Silent      | RESPOND normally |

---

### Handling Mixed Inputs

The classifier prioritizes **active intent words**.

Example:
> “Yeah okay but **wait**”

Despite filler words being present, the command **“wait”** is detected and the agent stops instantly.

---

###  Configurable Ignore List

For clean and modular design, ignored filler words are defined as a configurable set:

```python
filler_words = {
    "yeah", "ok", "okay", "hmm",
    "uh-huh", "right", "aha"
}
