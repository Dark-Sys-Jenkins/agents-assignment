# LiveKit Voice Agent with Intelligent Interruption Logic

This project implements a LiveKit Voice Agent with advanced interruption logic, designed to solve the "Backchannel Problem" in conversational AI. Unlike standard voice agents that stop speaking at any detected noise, this agent listens to the content of the user's speech before deciding to interrupt.

## 🧠 What Problem Does It Solve?

Typical voice agents will stop talking as soon as they detect any sound (via VAD), which means even a simple backchannel like "Yeah" or "Okay" can cut off the agent. This project allows users to give natural feedback without accidentally interrupting, while still letting them issue clear commands to stop the agent.

## 🚀 How It Works

The agent uses a custom "Logic Gate" built on top of the LiveKit `AgentSession`. Instead of relying on raw Voice Activity Detection (VAD) to trigger interruptions, the default interruption behavior is disabled and the audio stream is manually controlled based on the Speech-to-Text (STT) transcript.

### Logic Flow
- **VAD Ignored:** `allow_interruptions=False` is set in the session. The agent is "deaf" to raw noise, preventing false starts from coughs or background sounds.
- **STT Analysis:** The code listens to the `user_transcript` event in real-time.
- **Rule 1: Length Check:** Any input that is 1 word or less is automatically ignored.
  - User says: "Stop" (1 word) → Agent keeps talking.
  - User says: "Yeah" (1 word) → Agent keeps talking.
- **Rule 2: Filler Check:** If the input is 2+ words, the agent checks if every word belongs to a "Safe List" (e.g., "yeah", "ok", "uh-huh").
  - User says: "Yeah okay" → All words are safe → Agent keeps talking.
  - User says: "Wait please" → 'Wait' is not safe → Agent interrupts.

### 🛠️ Technical Implementation

#### Key Code Snippet (Logic Gate)
```python
# Rule 1: Ignore single-word utterances to prevent accidental cutoffs
if len(words) <= 1:
    logger.info(f"Ignored 1-word input: '{text}'")
    return

# Rule 2: Check for phrases that are purely filler words
is_only_filler = all(word in IGNORE_WORDS for word in words)

if is_only_filler:
    logger.info(f"Ignored filler phrase: '{text}'")
    return

# Execution: Only interrupt if it passes both checks
session.interrupt()
```

## 📦 Dependencies
- **LiveKit Agents:** Core framework for the voice pipeline

### Running the Agent
Run the agent file directly from your terminal. Replace `intelligent_agent.py` with your actual filename if different.

```powershell
python .\examples\voice_agents\intelligent_agent.py dev
```

> **Note:** The `dev` command connects the agent to a local LiveKit sandbox session.

## 🧪 Testing the Logic

1. **Start the Agent:** Connect to the room.
2. **Scenario A (Backchanneling):** Ask the agent to tell a story. While she speaks, say "Yeah... okay."
   - **Result:** She should continue speaking without pausing.
3. **Scenario B (Interruption):** While she speaks, say "Wait, stop." (2 words).
   - **Result:** She should stop immediately and listen to you.

### Proof of Logic (Logs)
When running the agent, watch the terminal logs to see the decision-making process in action:

- **The Ignore Log:**
  - `INFO:basic-agent:Ignored filler phrase: 'yeah okay'`
- **The Success Log:**
  - `INFO:basic-agent:Valid Interruption (2+ words): 'stop talking'`

---

For more details, see the code in `intelligent_agent.py`.
