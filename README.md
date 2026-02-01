# Intelligent Interruption Handling for LiveKit Agents

This repository contains a refined implementation of a LiveKit Voice Agent featuring **context-aware interruption logic**.

Demo: [Here is the link to the demo video]
(https://drive.google.com/file/d/1EqTcxZdwQQEfg_ePEyiz3DGoNyLKQahR/view?usp=sharing)

Standard Voice Activity Detection (VAD) is often too sensitive, cutting off the agent when a user simply says "Yeah" or "Uh-huh" (backchanneling). This solution implements a logic layer that distinguishes between **passive listening** (which should be ignored) and **active interruption** (which should stop the agent), ensuring a smooth, natural conversational flow.

## 🚀 Key Features

1. **Context-Aware Filtering**: The agent ignores filler words (e.g., "Yeah", "Uh-huh") *only* while it is actively speaking.
2. **Semantic Interruptions**: The agent correctly interrupts for commands ("Stop") or mixed intent ("Yeah, wait a second") even if they start with a filler word.
3. **False-Start Prevention**: Solves the VAD vs. STT race condition by deferring interruption decisions until the transcript is analyzed.
4. **Windows Compatibility**: Includes specific patches for threading and dependency management on Windows systems.

## 🧠 The Logic Matrix

The agent's behavior is governed by the following logic state machine implemented in `agent_activity.py`:

| User Input | Agent State | Action | Reasoning |
| --- | --- | --- | --- |
| **"Yeah / Uh-huh"** | **Speaking** | **IGNORE** | User is just listening (Backchanneling). Agent continues seamlessly. |
| **"Stop / Wait"** | **Speaking** | **INTERRUPT** | User explicitly commanded a stop. |
| **"Yeah wait..."** | **Speaking** | **INTERRUPT** | Mixed input contains an intent to interrupt. |
| **"Yeah / Ok"** | **Silent** | **RESPOND** | Agent is waiting for input. Treats this as a valid answer. |

## 🛠️ Setup & Installation

### Prerequisites

* Python 3.9+
* `uv` (Python package manager)
* LiveKit Cloud Project (URL & API Key)

### Installation

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd agents-assignment

```


2. **Install dependencies:**
```bash
uv sync --all-extras --dev

```


> **Note for Windows Users:** The `bithuman` dependency (used for avatars) has been removed from `pyproject.toml` to prevent installation errors, as it currently lacks Windows support.


3. **Environment Configuration:**
Create a `.env` file (copy from `.env.example`) and add your keys:
```bash
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

```



### Running the Agent

To test the interruption logic interactively via the terminal:

```bash
uv run examples/voice_agents/basic_agent.py console

```

* Press `Space` to simulate speaking.
* Type text to simulate STT input.

## ⚙️ Configuration

The interruption logic is defined at the top of `livekit/agents/voice/agent_activity.py`. You can modify the word lists directly in the **Config Array**:

```python
# livekit/agents/voice/agent_activity.py

# 1. Hard Interrupts: Words that ALWAYS stop the agent
HARD_INTERRUPT_KEYWORDS = "stop,wait,pause,hold,cancel,halt,abort,no"

# 2. Passive Fillers: Words to IGNORE while the agent is speaking
PASSIVE_FILLER_WORDS = "okay,ok,yeah,yes,yep,uh,um,hmm,hm,huh,ah,uh,uhhuh,right,sure,gotcha,great"

```

* **To add a filler word:** Simply append it to the `PASSIVE_FILLER_WORDS` string.
* **To add a command:** Append it to `HARD_INTERRUPT_KEYWORDS`.

## 🔧 Technical Implementation Details

### 1. The "False Start" Fix

Standard VAD triggers an interruption immediately upon detecting sound. This creates a "stutter" where the agent stops, realizes the user just said "Yeah", and then resumes.

We modified `on_vad_inference_done` in `AgentActivity` to **defer** the interruption signal if an STT engine is connected. The agent keeps speaking until the STT transcript arrives, allowing us to analyze the *content* of the speech before deciding to stop.

### 2. Windows Compatibility Patch

Python's `signal` library throws a `ValueError` on Windows when `signal.signal()` is called from a worker thread. We patched `livekit/agents/ipc/supervised_proc.py` to handle this gracefully:

```python
# Patch in supervised_proc.py
@contextlib.contextmanager
def _mask_ctrl_c():
    try:
        old = signal.signal(signal.SIGINT, signal.SIG_IGN)
    except ValueError:
        # Graceful fallback for Windows worker threads
        yield
        return
    # ...

```

## 🧪 Testing Scenarios

To verify the logic, run the agent in console mode and try the following:

1. **The Long Explanation:** Ask the agent to tell a story. While it speaks, type "Yeah", "Uh-huh", or "Right".
* *Result:* Agent should **continue printing text** without stopping.


2. **The Stop Command:** While the agent is speaking, type "Stop".
* *Result:* Agent should **stop immediately**.


3. **The Mixed Input:** While the agent is speaking, type "Yeah wait a second".
* *Result:* Agent should **stop immediately** (logic detects "wait").


4. **The Passive Affirmation:** Wait for the agent to finish asking a question. Type "Yeah".
* *Result:* Agent should **respond** to the input (e.g., "Great, let's proceed").