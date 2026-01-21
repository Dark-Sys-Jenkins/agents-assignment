# Filler Aware-Interaction Voice Agent
QUICK DEMO- https://drive.google.com/file/d/17o6SzJQ61ZEnhWcK2l1LQX6P_WZYA46t/view?usp=sharing where we have                 
○ The agent ignoring "yeah" while talking. 
○ The agent stopping for "stop."
○ The agent responding to "yeah" when silent.


Kelly(just a cute name given to basic_agent.py in it's filler aware form) is a high-performance voice agent that implements a robust interaction handling layer on top of the LiveKit framework. She processes interruptions with a sophisticated strategy that balances speed (VAD) with semantic understanding (STT).

## 🧠 Core Engineering Principles

### 1. Logic Layer vs. VAD Kernel
Unlike standard agents that immediately cut audio when the user speaks, Kelly maintains the **Core VAD Kernel unmodified**. 
- The VAD (Voice Activity Detection) remains fast and sensitive to noise.
- The **Logic Handling Layer** resides within the agent's event loop (`InteractionManager`).
- This allows for "Non-Destructive VAD": Kelly can decide *after* VAD triggers whether to actually commit to a silence or resume speaking.

### 2. STT-Stream Utilization & False-Start Mitigation
The biggest challenge in voice AI is the latency gap: **VAD is faster than STT.**
- **The Problem**: VAD detects sound instantly and might stop the agent, but it takes ~300-500ms for STT to tell us *what* was said (e.g., just a cough or a "yeah").
- **The Solution**: Kelly implements a **Debounced Commitment Strategy**.
    - When VAD triggers a "start of speech," the agent enters a high-alert state but doesn't immediately "forget" her place.
    - We utilize the **STT transcript stream** to validate the intent.
    - **350ms Window**: Kelly waits for the STT stream to provide context. If STT shows the word was on the `INTERACT_FILLERS` list, the interruption is "swallowed" and she continues her current thread.
    - **Real-Time Latency**: This decision happen in ~350ms, which is imperceptible to the user, ensuring the conversation feels fluid and never "laggy."

---

## ✨ Key Features

### 1. Configurable Ignore List (Fillers)
Kelly uses an intelligent filter to ignore "soft" inputs.
- **Example**: `['yeah', 'ok', 'hmm', 'right', 'uh-huh']`.
- **Behavior**: These words are recognized via the STT stream. If detected while Kelly is speaking, she treats them as affirmations and continues without interruption.

### 2. State-Based Intent Filtering
The filtering logic is context-aware:
- **Active State**: If Kelly is speaking or thinking, the "Ignore List" is strictly enforced to protect her flow.
- **Idle State**: If she is listening, she responds normally to any input.

### 3. Semantic Interruption Handling
Kelly does not just look for single words; she evaluates the **entire semantic phrase**.
- **The Mixed Sentence Problem**: If a user says "Yeah, wait a second," the system detects both a filler ("yeah") and a command ("wait").
- **Resolution**: Kelly's parsing logic strips fillers from the start of phrases. If a command remains (like "wait"), it triggers a **Semantic Interruption**. She will stop immediately, respecting the user's command even if it was preceded by a filler.

### 4. Continuous Context Protocol
Kelly is programmed to handle tangents without losing her focus.
- If you interrupt an explanation with a side-question, she follows the **Answer & Resume** protocol:
    1.  Address the interruption concisely.
    2.  Automatically return to the previous thread (e.g., "Anyway, as I was saying about the story...").

---

## ⚙️ Configuration (Environment Variables)

Customize the agent via the `.env` file or shell exports:

| Variable | Description | Default Example |
| :--- | :--- | :--- |
| `INTERACT_FILLERS` | Soft inputs to be ignored while active. | `yeah,ok,hmm,right,uh-huh` |
| `INTERACT_COMMANDS` | Words that trigger a hard stop. | `stop,wait,no,nah,cancel` |

---

## 🚀 Running the Agent

```bash
# 1. Install Dependencies (Python 3.9+)
uv sync

# 2. Run in Console Mode
python examples/voice_agents/basic_agent.py console
```

---

## 🛠️ Performance & Scalability
- **Latency**: The intent determination window is capped at 350ms.
- **Accuracy**: By combining STT-validation with a debounced commit, we eliminate "false starts" where an agent cuts off due to background chair noise or accidental fillers.
- **Safety**: The interaction lock prevents the agent from triggering twice in a rapid-fire sequence, protecting the LLM from redundant turns.



