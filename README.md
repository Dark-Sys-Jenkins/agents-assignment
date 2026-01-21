# LiveKit Intelligent Interruption Agent ("Kelly")

This repository contains a LiveKit Voice Agent customized to handle "Intelligent Interruptions." The goal is to solve the "Backchannel Problem"—where users saying "Yeah," "Okay," or "Uh-huh" accidentally trigger a full interruption, causing the agent to stop speaking and regenerate its thought process.

## ⚠️ The Core Challenge (Technical Constraints)

In modern versions of the LiveKit Agents framework, direct access to the low-level `VoicePipelineAgent` or the raw VAD audio loop has been abstracted away. This means we cannot easily inject logic *inside* the VAD to conditionally suppress "Stop" signals based on audio features.

**The Dilemma:**
1.  **Strict VAD:** If we allow standard interruptions, "Okay" cuts the audio immediately.
2.  **No VAD:** If we disable interruptions entirely, the user cannot stop the agent at all.
3.  **The Latency Trade-off:** To distinguish between "Okay" and "Stop," we **must** wait for the Speech-to-Text (STT) transcript. This inevitably introduces a slight latency (the "VAD wait time") because the system cannot know *what* was said until the user finishes saying it.

## 🧠 The Solution: Semantic Filtering Layer

We implemented a logic layer that sits **between the Transcription (STT) and the Intelligence (LLM)**.

### 1. VAD Configuration (The 0.5s Rule)
We rely on a standard `min_interruption_duration` of `0.5` seconds.
* **Logic:** Any noise shorter than 0.5s is ignored by the hardware automatically.
* **Effect:** Determining if an utterance is speech vs. noise happens here. Once it crosses 0.5s, it is sent to our semantic filter.

### 2. The Semantic Filter (The "Brain Guard")
Since we cannot block the VAD signal at the hardware level without losing "Stop" functionality, we allow the signal to pass but **block it from reaching the LLM's context window.**

**The Workflow:**
1.  **User Speaks:** "Yeah, sure."
2.  **Transcription:** The STT engine converts audio to text.
3.  **Embedding Check:**
    * We generate vector embeddings for the input using `SentenceTransformer`.
    * We compare these against a pre-computed list of "Passive Words" (e.g., *yeah, uh-huh, ok, right*).
4.  **The Fork:**
    * **Case A (Similarity > 0.60):** The input is classified as "Backchanneling."
        * **Action:** We **prevent** the input from reaching the LLM. The agent's current speech stream is maintained (or resumed immediately), and the agent *does not* reconsider its thought process. It effectively "hears" you but ignores the interruption.
    * **Case B (No Similarity):** The input is a valid command (e.g., "Stop," "Wait," "Change topic").
        * **Action:** We manually trigger a `StopResponse`, clear the audio buffer, and allow the LLM to generate a new reply.

## 🚀 Setup & Installation

### 1. Prerequisites
* Python 3.9+
* LiveKit Cloud Project
* API Keys: Groq (LLM/STT), Murf (TTS)

### 2. Installation
```bash
pip install -r requirements.txt
