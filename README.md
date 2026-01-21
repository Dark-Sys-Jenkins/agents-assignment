# LiveKit Intelligent Interruption Handling (Smart Backchanneling)

**Submitted by:** Divyanshu  
**College:** Indraprastha Institute of Information Technology Delhi (IIITD)  
**Branch:** CSAI (Computer Science and Artificial Intelligence)  
**Roll No:** 2023211  
**Email:** divyanshu23211@iiitd.ac.in  

---

## Overview

This repository contains a solution for the **LiveKit Intelligent Interruption Challenge**. The goal was to refine the conversational flow of a real-time AI agent by solving the issue of over-sensitive interruptions.

Previously, standard VAD (Voice Activity Detection) would cut off the agent if the user said passive listening cues like "Yeah", "Uh-huh", or "Okay". This solution implements a **Context-Aware Logic Layer** that distinguishes between **Passive Acknowledgement** (Backchanneling) and **Active Interruption**.

## Key Features

* **Smart Backchannel Filtering:** The agent continues speaking seamlessly if the user says filler words (e.g., "Yeah", "I see") while the agent is talking.
* **Semantic Interruption:** If the user mixes a backchannel with a command (e.g., "Yeah, wait a second"), the agent correctly interprets this as an interruption.
* **State Awareness:** The agent responds normally to "Yeah" or "Okay" if it is currently silent (treating it as a valid user turn).
* **Windows Compatibility:** Includes fixes for signal handling on Windows environments.
* **Modern Telemetry:** Updated OpenTelemetry implementation to support version 1.34+.

---

## How It Works (The Logic)

The solution is implemented via a "Greedy Phrase Consumption" algorithm injected into the agent's event loop. It operates on two specific checkpoints in `AgentActivity`:

### 1. The Algorithm (`nlp_utils.py`)
We moved away from simple keyword matching to a sequential token consumption approach to handle mixed inputs (Scenario 4).

1.  **Normalization:** The user's transcript is normalized (punctuation removed, lowercased).
2.  **Sorting:** The ignore list is sorted by length (longest phrases first) to prioritize specific phrases like "That makes sense" over generic words like "That".
3.  **Consumption:** The algorithm iteratively checks the start of the user's transcript against the allowed list.
    * If a match is found, that part of the transcript is "consumed" (removed).
    * This repeats until no matches are found at the start of the string.
4.  **Verdict:**
    * If the remaining string is **empty**, the input was purely backchanneling -> **IGNORE**.
    * If the remaining string contains **text** (e.g., "wait"), it contains a command -> **INTERRUPT**.

### 2. The Checkpoints (`agent_activity.py`)
The logic is applied in two places to ensure robustness against both VAD triggers and End-of-Utterance (EOU) triggers:

* **`_interrupt_by_audio_activity`:** This handles fast VAD interruptions. If the VAD triggers but the interim transcript is determined to be a backchannel, the interruption is **blocked**.
* **`on_end_of_turn`:** This handles the EOU model. If the user finishes speaking a backchannel word, the agent usually attempts to reply. We intercept this, return `True` (to clear the buffer), but **skip the reply generation**, allowing the agent to keep speaking.

### 3. State Awareness
All filtering logic is wrapped in a check: `if self._session.agent_state == "speaking"`.
* **If Agent is Speaking:** Filters are active (Backchanneling logic).
* **If Agent is Silent:** Filters are disabled. "Yeah" is treated as a valid answer/turn.

---

## Configuration

The list of ignored words and phrases is configurable in `livekit/agents/voice/agent_session.py`.

**Default Ignore List:**
```python
DEFAULT_IGNORE_WORDS: list[str] = [
    "yes","yeah", "ok", "okay", "hmm", "mhmm", "aha", "uh-huh", "yep", "yup", "sure", "cool","right","alright","oh","ohh",
    "i see",
    "all right",
    "go on",
    "keep going",
    "got it",
]
```

To change this per agent, you can pass an `ignore_words` list when initializing the `AgentSession`.

## DEMO LINK - https://drive.google.com/file/d/1Z2xeb-3N-W_az_PzAhZz6V6nKk6Zz2Kv/view?usp=sharing

### Test Scenarios & Results

| Scenario | User Input        | Agent State | Result      | Logic Applied                                   |
|----------|-------------------|-------------|-------------|------------------------------------------------|
| 1. Long Explanation | "Yeah... uh-huh" | Speaking    | IGNORES     | Transcript consumed entirely.                  |
| 2. Passive Affirmation | "Yeah"           | Silent      | RESPONDS    | State check bypasses filter.                   |
| 3. Correction | "No stop"       | Speaking    | INTERRUPTS  | "No" and "stop" not in ignore list.            |
| 4. Mixed Input | "Yeah wait"     | Speaking    | INTERRUPTS  | "Yeah" consumed, "wait" remains.               |


-------

## Installation & Running

**Prerequisites**

* Python 3.9+
* LiveKit Cloud Project (URL and API Key/Secret)

**Steps**

1. **Clone the Repository**
```bash
git clone <your-repo-url>
cd agents-assignment

```


2. **Install Base Dependencies**
First, install the standard requirements.
```bash
pip install -r examples/voice_agents/requirements.txt

```

3. **⚠️ IMPORTANT: Link Local Library**
To use the modified interruption logic, you **MUST** link your local version in editable mode.
```bash

pip install -e livekit-agents

```


4. **Update Telemetry**
Ensure modern OpenTelemetry packages are installed to match the updated code.
```bash
pip install "opentelemetry-api>=1.34" "opentelemetry-sdk>=1.34.1" "opentelemetry-exporter-otlp>=1.34.1"

```


5. **Environment Setup**
Create a `.env` file in the `\agents-assignment\examples\` directory:
```env
OPENAI_API_KEY=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=
```


6. **Download Models for your agent**

To download the models locally, run the following command:

```bash
python examples/voice_agents/basic_agent.py download-files
```


7. **Run the Agent**
```bash
python examples/voice_agents/basic_agent.py console

```

---


## Verification & Testing

To ensure the solution strictly adheres to the challenge requirements, a comprehensive test suite was implemented.

### 1. Install Test Dependencies
Ensure you have `pytest` and `pytest-asyncio` installed:
```bash
pip install pytest pytest-asyncio

```

### 2. Run the Test Suite

Run the tests with verbose output to see each scenario pass:

```bash
pytest -v tests/test_interruption_logic.py

```

### 3. What is Tested?

The test file (`tests/test_interruption_logic.py`) explicitly validates the **4 Core Challenge Scenarios**:

* **Scenario 1 (Long Explanation):**
* *Context:* Agent is speaking. User says: "Okay... yeah... uh-huh"
* *Result:* **IGNORED** (Agent continues speaking).


* **Scenario 2 (Passive Affirmation):**
* *Context:* Agent is silent. User says: "Yeah."
* *Result:* **RESPOND** (Agent treats it as a valid turn).


* **Scenario 3 (Correction):**
* *Context:* Agent is speaking. User says: "No stop."
* *Result:* **INTERRUPT** (Command detected).


* **Scenario 4 (Mixed Input):**
* *Context:* Agent is speaking. User says: "Yeah okay but wait."
* *Result:* **INTERRUPT** (Command found after backchannel).



### 4. Sample Output

You should see all tests passing:

```text
tests/test_interruption_logic.py::test_nlp_basic_backchannel PASSED          [ 10%]
tests/test_interruption_logic.py::test_nlp_phrase_backchannel PASSED         [ 20%]
tests/test_interruption_logic.py::test_nlp_normalization PASSED              [ 30%]
tests/test_interruption_logic.py::test_nlp_variants PASSED                   [ 40%]
tests/test_interruption_logic.py::test_nlp_empty_input PASSED                [ 50%]
tests/test_interruption_logic.py::test_scenario_1_long_explanation PASSED    [ 60%]
tests/test_interruption_logic.py::test_scenario_3_immediate_stop PASSED      [ 70%]
tests/test_interruption_logic.py::test_scenario_4_mixed_input PASSED         [ 80%]
tests/test_interruption_logic.py::test_interruption_blocked_when_speaking PASSED [ 90%]
tests/test_interruption_logic.py::test_scenario_2_response_when_silent PASSED [100%]

============================== 10 passed in 0.12s ===============================

```

----


## 🔧 Modifications Summary

### 1. Core Logic
* **`livekit/agents/voice/nlp_utils.py`**: Created new utility file containing the `is_backchannel` consumption algorithm.
* **`livekit/agents/voice/agent_activity.py`**: Integrated `nlp_utils` into interruption handlers. Added specific logging to trace "BLOCKED" vs "ALLOWED" interruptions.

### 2. Infrastructure
* **`livekit/agents/voice/agent_session.py`**: Added `ignore_words` to `AgentSessionOptions` dataclass and initialization arguments to allow configuration.
* **`livekit/agents/ipc/supervised_proc.py`**: **Windows Fix.** Added a `try/except` block around `signal.signal` to prevent crashes when running in background threads on Windows.
* **`livekit/agents/telemetry/traces.py`**: **Telemetry Fix.** Updated imports to use `opentelemetry.logs` and `opentelemetry.sdk.logs` (stable API) instead of the deprecated `_logs` module, ensuring compatibility with modern dependencies.


----

## LOGS

```python
PS C:\College\SEM6\Salescode\agents-assignment> python examples/voice_agents/basic_agent.py console
    Agents   Starting console mode 🚀

    23:36:07 DEBUG  asyncio          Using proactor: IocpProactor  
             INFO   livekit.agents   starting worker {"version": "1.3.3", "rtc-version": "1.0.23"}
             INFO   livekit.agents   starting inference executor  
             INFO   livekit.agents   initializing process {"pid": 3476, "inference": true}
    23:36:16 INFO   livekit.agents   process initialized {"pid": 3476, "inference": true, "elapsed_time": 9.17}
             INFO   livekit.agents   initializing job runner {"tid": 26480}
             DEBUG  asyncio          Using proactor: IocpProactor  
             INFO   livekit.agents   job runner initialized {"tid": 26480, "elapsed_time": 0.1}
    23:36:17 DEBUG  livekit.agents   http_session(): creating a new httpclient ctx {"room": "mock_room"}
             DEBUG  livekit.agents   using audio io: `Console` -> `AgentSession` -> `Console` {"room": "mock_room"}
             WARNI… livekit.agents   resume_false_interruption is enabled but audio output does not support pause, it will be ignored {"room": "mock_room", "audio_output": "Console"}
             DEBUG  livekit.agents   using transcript io: `AgentSession` -> (none) {"room": "mock_room"}
    23:36:18 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 1.07, "prompt_tokens": 151, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 30, "tokens_per_second": 18.31}
    23:36:22 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.3758798000017123, "audio_duration": 7.01}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25}
    23:36:26 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.6}
    23:36:29 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.9}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Tell me a really long story", "language": "en", "transcript_delay": 0.023302078247070312}
    23:36:31 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.0}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "about a cat and a dog.", "language": "en", "transcript_delay": 0.5394020080566406}
             INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.77, "prompt_tokens": 0, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 0, "tokens_per_second": 0.0}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.25621894001960754, "duration": 0.041, "input": "<|im_start|>assistant\nhey there what can i do for you today want to  
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a dog"}
             DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 0.06612420082092285}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.61, "transcription_delay": 0.54}
    23:36:35 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.69, "prompt_tokens": 201, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 258, "tokens_per_second": 57.0}
    23:36:36 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:36:38 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.5}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Okay.' identified as backchannel. {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Okay.", "language": "en", "transcript_delay": 0.4976639747619629}
             INFO   livekit.agents   INTERRUPTION BLOCKED: 'Okay.' identified as backchannel. {"room": "mock_room"}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.3587372601032257, "duration": 0.034, "input": "<|im_start|>assistant\nhey there what can i do for you today want to   
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a dog okay"}
             INFO   livekit.agents   EOU BLOCKED: Final transcript 'Okay.' is a backchannel. Resetting buffer. {"room": "mock_room"}
    23:36:41 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
    23:36:42 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.5}
             INFO   livekit.agents   INTERRUPTION BLOCKED: ' Yeah.' identified as backchannel. {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Yeah.", "language": "en", "transcript_delay": 0.7164530754089355}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.1598750203847885, "duration": 0.052, "input": "<|im_start|>assistant\nhey there what can i do for you today want to   
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a dog yeah"}
             INFO   livekit.agents   EOU BLOCKED: Final transcript 'Yeah.' is a backchannel. Resetting buffer. {"room": "mock_room"}
    23:36:45 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.7}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "I see.", "language": "en", "transcript_delay": 0.6017708778381348}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.06979262828826904, "duration": 0.043, "input": "<|im_start|>assistant\nhey there what can i do for you today want to  
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a dog i see"}
             INFO   livekit.agents   EOU BLOCKED: Final transcript 'I see.' is a backchannel. Resetting buffer. {"room": "mock_room"}
    23:36:50 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:36:52 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.9}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Okay.", "language": "en", "transcript_delay": 0.5040163993835449}
             INFO   livekit.agents   INTERRUPTION BLOCKED: 'Okay.' identified as backchannel. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: 'Okay.' identified as backchannel. {"room": "mock_room"}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.3587372601032257, "duration": 0.043, "input": "<|im_start|>assistant\nhey there what can i do for you today want to   
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a dog okay"}
             INFO   livekit.agents   EOU BLOCKED: Final transcript 'Okay.' is a backchannel. Resetting buffer. {"room": "mock_room"}
    23:36:57 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.9}
    23:37:00 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION ALLOWED: ' Okay. But wait.' contains content/commands. {"room": "mock_room"}
             INFO   livekit.agents   TRIGGERING INTERRUPTION: Pausing/Stopping current speech. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION ALLOWED: ' Okay. But wait.' contains content/commands. {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION ALLOWED: ' Okay. But wait.' contains content/commands. {"room": "mock_room"}
    23:37:01 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.6}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Okay. But wait. Stop.", "language": "en", "transcript_delay": 0.5010230541229248}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.01466901320964098, "duration": 0.1, "input": "<|im_start|>assistant\nhey there what can i do for you today want to    
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a
                                                    dog<|im_end|>\n<|im_start|>assistant\nalright get comfy once upon a time in a small town there was a clever cat named whiskers and a goofy dog named buster      
                                                    whiskers loved to explore rooftops while buster preferred chasing his tail in the yard one day they both spotted a mysterious glowing ball in the forest
                                                    curiosity got the best of them and they decided to team up as they ventured deeper they met a wise old owl who said the glowing ball held a secret to happiness  
                                                    to unlock it they had to pass three challenges courage kindness and teamwork the courage test had them facing a spooky cave whiskers quick thinking and busters  
                                                    bravery saved the day next was kindnesshelping a lost squirrel find its way home which they did by sharing their snacks and comforting it finally the teamwork   
                                                    challenge required them to build a bridge over a rushing stream whiskers planned the bridge and buster gathered sticks and stones together they crossed safely   
                                                    and the glowing ball revealed a treasure friendship was the true secret to happiness whiskers and buster returned home best friends forever proving cats and dogs
                                                    can get along just fine so what do you think want a sequel<|im_end|>\n<|im_start|>user\nokay but wait stop"}
             DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 0.20284795761108398}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.7, "transcription_delay": 0.5}
    23:37:02 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.73, "prompt_tokens": 473, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 21, "tokens_per_second": 19.66}
    23:37:04 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.3132162999972934, "audio_duration": 5.57}
    23:37:06 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.9}
    23:37:09 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.9}
    23:37:10 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.8}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Yeah.", "language": "en", "transcript_delay": 0.6207971572875977}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.006160824093967676, "duration": 0.108, "input": "<|im_start|>assistant\nhey there what can i do for you today want to 
                                                    chat hear a joke or need some info just say the word<|im_end|>\n<|im_start|>user\ntell me a really long story about a cat and a
                                                    dog<|im_end|>\n<|im_start|>assistant\nalright get comfy once upon a time in a small town there was a clever cat named whiskers and a goofy dog named buster      
                                                    whiskers loved to explore rooftops while buster preferred chasing his tail in the yard one day they both spotted a mysterious glowing ball in the forest
                                                    curiosity got the best of them and they decided to team up as they ventured deeper they met a wise old owl who said the glowing ball held a secret to happiness  
                                                    to unlock it they had to pass three challenges courage kindness and teamwork the courage test had them facing a spooky cave whiskers quick thinking and busters  
                                                    bravery saved the day next was kindnesshelping a lost squirrel find its way home which they did by sharing their snacks and comforting it finally the teamwork   
                                                    challenge required them to build a bridge over a rushing stream whiskers planned the bridge and buster gathered sticks and stones together they crossed safely   
                                                    and the glowing ball revealed a treasure friendship was the true secret to happiness whiskers and buster returned home best friends forever proving cats and dogs
                                                    can get along just fine so what do you think want a sequel<|im_end|>\n<|im_start|>user\nokay but wait stop<|im_end|>\n<|im_start|>assistant\nstopping right here 
                                                    whats up want to switch gears or add a twist to the story<|im_end|>\n<|im_start|>user\nyeah"}
    23:37:11 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.79, "prompt_tokens": 503, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 18, "tokens_per_second": 18.25}
    23:37:12 DEBUG  livekit.agents   flush audio emitter due to slow audio generation {"room": "mock_room"}
             DEBUG  livekit.agents   flush audio emitter due to slow audio generation {"room": "mock_room"}
    23:37:13 DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 2.3765485286712646}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 3.0, "transcription_delay": 0.62}
    23:37:14 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.34067099999811035, "audio_duration": 4.88}
    23:37:15 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:37:19 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.1}
    23:37:21 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.0}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Can you", "language": "en", "transcript_delay": 0.12967848777770996}
    23:37:22 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.61, "prompt_tokens": 530, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 12, "tokens_per_second": 16.23}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.1}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "count from", "language": "en", "transcript_delay": 0.0530545711517334}
    23:37:23 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.72, "prompt_tokens": 532, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 12, "tokens_per_second": 12.75}
    23:37:24 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.6}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "one to fifty?", "language": "en", "transcript_delay": 0.5215988159179688}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.30998656153678894, "duration": 0.084, "input": "<|im_start|>assistant\nalright get comfy once upon a time in a small  
                                                    town there was a clever cat named whiskers and a goofy dog named buster whiskers loved to explore rooftops while buster preferred chasing his tail in the yard   
                                                    one day they both spotted a mysterious glowing ball in the forest curiosity got the best of them and they decided to team up as they ventured deeper they met a  
                                                    wise old owl who said the glowing ball held a secret to happiness to unlock it they had to pass three challenges courage kindness and teamwork the courage test  
                                                    had them facing a spooky cave whiskers quick thinking and busters bravery saved the day next was kindnesshelping a lost squirrel find its way home which they did
                                                    by sharing their snacks and comforting it finally the teamwork challenge required them to build a bridge over a rushing stream whiskers planned the bridge and   
                                                    buster gathered sticks and stones together they crossed safely and the glowing ball revealed a treasure friendship was the true secret to happiness whiskers and 
                                                    buster returned home best friends forever proving cats and dogs can get along just fine so what do you think want a sequel<|im_end|>\n<|im_start|>user\nokay but 
                                                    wait stop<|im_end|>\n<|im_start|>assistant\nstopping right here whats up want to switch gears or add a twist to the
                                                    story<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\ncool what twist or new direction do you have in mind spill the
                                                    beans<|im_end|>\n<|im_start|>user\ncan you count from one to fifty"}
             DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 0.16917967796325684}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.69, "transcription_delay": 0.52}
    23:37:26 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.65, "prompt_tokens": 536, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 142, "tokens_per_second": 60.48}
    23:37:29 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.95}
    23:37:31 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
    23:37:32 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.85}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "No. Stop.", "language": "en", "transcript_delay": 0.6129879951477051}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.36350759863853455, "duration": 0.059, "input": "<|im_start|>user\nokay but wait
                                                    stop<|im_end|>\n<|im_start|>assistant\nstopping right here whats up want to switch gears or add a twist to the
                                                    story<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\ncool what twist or new direction do you have in mind spill the
                                                    beans<|im_end|>\n<|im_start|>user\ncan you count from one to fifty no stop"}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.68, "transcription_delay": 0.61}
    23:37:33 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.82, "prompt_tokens": 689, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 10, "tokens_per_second": 10.48}
    23:37:34 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.33092630000101053, "audio_duration": 2.0}
    23:37:37 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:37:39 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.4}
    23:37:41 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.8}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "How to make haka noodles?", "language": "en", "transcript_delay": 0.8087854385375977}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.696202278137207, "duration": 0.096, "input": "<|im_start|>assistant\ncool what twist or new direction do you have in  
                                                    mind spill the beans<|im_end|>\n<|im_start|>user\ncan you count from one to fifty<|im_end|>\n<|im_start|>assistant\nsure thing here we go one two three four five
                                                    six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twenty-one twenty-two twenty-three twenty-four       
                                                    twenty-five twenty-six twenty-seven twenty-eight twenty-nine thirty thirty-one thirty-two thirty-three thirty-four thirty-five thirty-six thirty-seven
                                                    thirty-eight thirty-nine forty forty-one forty-two forty-three forty-four forty-five forty-six forty-seven forty-eight forty-nine fifty want me to sing it       
                                                    next<|im_end|>\n<|im_start|>user\nno stop<|im_end|>\n<|im_start|>assistant\nstopped whats next on the menu<|im_end|>\n<|im_start|>user\nhow to make haka
                                                    noodles"}
             DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 0.10594844818115234}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.92, "transcription_delay": 0.81}
    23:37:43 INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.63, "prompt_tokens": 712, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 103, "tokens_per_second": 47.96}
    23:37:46 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:37:51 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:37:52 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.0}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Okay.", "language": "en", "transcript_delay": 0.6142752170562744}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.2553194463253021, "duration": 0.102, "input": "<|im_start|>user\ncan you count from one to
                                                    fifty<|im_end|>\n<|im_start|>assistant\nsure thing here we go one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen   
                                                    seventeen eighteen nineteen twenty twenty-one twenty-two twenty-three twenty-four twenty-five twenty-six twenty-seven twenty-eight twenty-nine thirty thirty-one 
                                                    thirty-two thirty-three thirty-four thirty-five thirty-six thirty-seven thirty-eight thirty-nine forty forty-one forty-two forty-three forty-four forty-five     
                                                    forty-six forty-seven forty-eight forty-nine fifty want me to sing it next<|im_end|>\n<|im_start|>user\nno stop<|im_end|>\n<|im_start|>assistant\nstopped whats  
                                                    next on the menu<|im_end|>\n<|im_start|>user\nhow to make haka noodles okay"}
             INFO   livekit.agents   EOU BLOCKED: Final transcript 'Okay.' is a backchannel. Resetting buffer. {"room": "mock_room"}
    23:37:56 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.3647906000005605, "audio_duration": 26.42}
    23:37:57 INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.9}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION BLOCKED: False Start (VAD triggered, no text). {"room": "mock_room"}
             INFO   livekit.agents   INTERRUPTION ALLOWED: ' Okay. But' contains content/commands. {"room": "mock_room"}
             INFO   livekit.agents   TRIGGERING INTERRUPTION: Pausing/Stopping current speech. {"room": "mock_room"}
    23:37:58 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.6}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "Okay. But stop.", "language": "en", "transcript_delay": 0.6624100208282471}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.029948048293590546, "duration": 0.096, "input": "<|im_start|>assistant\nsure thing here we go one two three four five 
                                                    six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twenty-one twenty-two twenty-three twenty-four       
                                                    twenty-five twenty-six twenty-seven twenty-eight twenty-nine thirty thirty-one thirty-two thirty-three thirty-four thirty-five thirty-six thirty-seven
                                                    thirty-eight thirty-nine forty forty-one forty-two forty-three forty-four forty-five forty-six forty-seven forty-eight forty-nine fifty want me to sing it       
                                                    next<|im_end|>\n<|im_start|>user\nno stop<|im_end|>\n<|im_start|>assistant\nstopped whats next on the menu<|im_end|>\n<|im_start|>user\nhow to make haka
                                                    noodles<|im_end|>\n<|im_start|>assistant\nto make hakka noodles start by boiling noodles until they're just tender then drain and set aside in a pan heat oil and
                                                    sauté chopped garlic ginger and green chilies add chopped veggies like carrots capsicum and cabbage stir-fry them until slightly soft toss in the noodles soy    
                                                    sauce a little vinegar salt and pepper stir well to combine and cook for a couple more minutes garnish with spring onions and serve hot want the detailed        
                                                    recipe<|im_end|>\n<|im_start|>user\nokay but stop"}
             DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 0.10879063606262207}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.77, "transcription_delay": 0.66}
             INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.68, "prompt_tokens": 827, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 17, "tokens_per_second": 19.99}
    23:37:59 DEBUG  livekit.agents   flush audio emitter due to slow audio generation {"room": "mock_room"}
    23:38:01 INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.3016693999998097, "audio_duration": 5.29}
    23:38:03 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0}
    23:38:07 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.0}
    23:38:10 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.0}
    23:38:14 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.0}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.7}
             DEBUG  livekit.agents   received user transcript {"room": "mock_room", "user_transcript": "I", "language": "en", "transcript_delay": 0.6109449863433838}
             DEBUG  livekit.plugins… eou prediction {"room": "mock_room", "eou_probability": 0.00015331842587329447, "duration": 0.151, "input": "<|im_start|>assistant\nstopped whats next on the
                                                    menu<|im_end|>\n<|im_start|>user\nhow to make haka noodles<|im_end|>\n<|im_start|>assistant\nto make hakka noodles start by boiling noodles until they're just   
                                                    tender then drain and set aside in a pan heat oil and sauté chopped garlic ginger and green chilies add chopped veggies like carrots capsicum and cabbage        
                                                    stir-fry them until slightly soft toss in the noodles soy sauce a little vinegar salt and pepper stir well to combine and cook for a couple more minutes garnish 
                                                    with spring onions and serve hot want the detailed recipe<|im_end|>\n<|im_start|>user\nokay but stop<|im_end|>\n<|im_start|>assistant\npaused the recipe just say
                                                    when you want to resume or try something else<|im_end|>\n<|im_start|>user\ni"}
    23:38:15 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.3}
             INFO   livekit.agents   LLM metrics {"room": "mock_room", "model_name": "openai/gpt-4.1-mini", "model_provider": "livekit", "ttft": 0.7, "prompt_tokens": 852, "prompt_cached_tokens": 0,
                                                 "completion_tokens": 16, "tokens_per_second": 17.29}
             INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.9}
    23:38:16 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.4}
    23:38:17 DEBUG  livekit.agents   using preemptive generation {"room": "mock_room", "preemptive_lead_time": 2.3833842277526855}
             INFO   livekit.agents   EOU metrics {"room": "mock_room", "model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 3.0, "transcription_delay": 0.61}
             INFO   livekit.agents   TTS metrics {"room": "mock_room", "model_name": "cartesia/sonic-2", "model_provider": "livekit", "ttfb": 0.3289517999983218, "audio_duration": 3.53}
    23:38:18 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.0}
    23:38:22 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.8}
    23:38:23 INFO   livekit.agents   STT metrics {"room": "mock_room", "model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.3}
    ```