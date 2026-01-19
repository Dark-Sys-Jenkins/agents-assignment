# Intelligent Interruption Handling Agent

This project implements a **context-aware voice agent** using LiveKit.  
The agent correctly distinguishes between **passive acknowledgements** (backchanneling such as “yeah”, “ok”) and **active interruptions** (such as “stop”, “wait”) during real-time speech playback.

The primary goal is to ensure that **filler words never interrupt the agent while it is speaking**, while **explicit commands interrupt immediately**, as required by the assignment.

---

## Features

- **Context-Aware Interruption Logic**  
  The agent’s behavior depends on whether it is *currently speaking* or *silent*.

- **Semantic Gating (Not VAD-Based)**  
  Interruption decisions are based on **finalized STT text**, not raw audio activity, eliminating false positives from short acknowledgements.

- **Zero-Hiccup Backchannel Handling**  
  Passive words such as “yeah”, “ok”, or “uh-huh” are ignored *without pausing, stuttering, or restarting audio*.

- **Pause–Resume with State Memory**  
  The agent stores its current playback position and resumes from the correct frame when instructed.

- **Frame-Level Audio Control**  
  Speech is streamed as PCM frames, enabling precise interruption without buffer corruption.

- **Configurable Words List**  
  All types of words can be modified easily.

---

## High-Level Flow

1. **User Audio Input**  
   Audio is streamed to the agent through LiveKit.

2. **Speech-to-Text (STT)**  
   The user’s speech is transcribed using Deepgram.

3. **Semantic Logic Layer**  
   The transcript is analyzed together with the agent’s current state:
   - speaking
   - silent
   - paused

4. **Decision**
   - **IGNORE** passive acknowledgements while speaking
   - **INTERRUPT** on explicit or mixed commands
   - **PROCESS** input normally when silent

5. **Speech Output**
   The agent speaks using locally generated TTS streamed as PCM frames.

---

## Decision Logic

The agent follows strict, state-dependent rules:

| User Input | Agent State | Action | Reason |
|-----------|------------|--------|--------|
| filler words | Speaking | IGNORE | Passive backchannel |
| hard words | Speaking | INTERRUPT | Explicit command |
| compound words (including hard + filler words) | Speaking | INTERRUPT | Contains non-filler word |
| "yeah" | Silent | PROCESS | Valid conversational input |
| "continue" | Paused | RESUME | Continues from stored position |
| "repeat", "start again" | Any | RESTART | Begins from start |

This logic ensures **no pauses, hiccups, or restarts** occur due to filler words.

---

## Handling VAD vs STT

Voice Activity Detection (VAD) is faster than STT but lacks semantic understanding.  
Interrupting based on VAD alone would cause false stops.

To avoid this:
- VAD is **not used** to interrupt speech.
- Interruption decisions are made **only after STT text is finalized**.
- The delay is imperceptible and remains real-time (delay < 1000ms).

This satisfies the latency requirement of the assignment.

---

## Technology Stack

- **LiveKit Agents** – real-time audio transport
- **Deepgram STT** – low-latency transcription
- **Silero VAD** – preloaded but not used for interruption decisions
- **pyttsx3** – local, offline text-to-speech
- **AsyncIO** – non-blocking concurrency

No LLM is used for the interruption logic.

---

## Configuration

Environment variables are used for easy setup and modification.

### `.env`
```env
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
DEEPGRAM_API_KEY=...
```
1. **Set up the environment:**
It is recommended to use a virtual environment.
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run in development mode:**
```bash
python examples/voice_agents/intelligent_agent.py dev
```

4. **Connect:** Join the LiveKit room using the agent playground.

## Verification Scenarios

The logic can be verified against the following test cases:

* **Test 1 (Long Explanation):** While the agent is explaining a topic, say "Yeah... uh-huh."
* *Expected Result:* Agent ignores input and continues speaking seamlessly.


* **Test 2 (Correction):** While the agent is speaking, say "No Stop."
* *Expected Result:* Agent stops immediately.


* **Test 3 (Mixed Input):** While the agent is speaking, say "Yeah okay but wait."
* *Expected Result:* Agent interrupts (logic detects non-filler "wait").


* **Test 4 (Passive Affirmation):** When the agent is silent, say "Yeah."
* *Expected Result:* Agent treats "Yeah" as a valid response and replies.

## Video Link
https://drive.google.com/file/d/1uLiqhjhvFoRPE2KmiZFDXJj2T_vvJc59/view?usp=sharing
(Video attached covers all the test cases mentioned in the assignment)