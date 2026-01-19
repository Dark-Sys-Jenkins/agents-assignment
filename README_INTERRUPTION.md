# Intelligent Interruption Handling (for LiveKit Agents)

This fork implements an **Intelligent Interruption Logic Layer** that prevents the agent from stopping abruptly when the user provides "backchannel" feedback (e.g., "Yeah", "Uh-huh", "Okay").

## 🚀 The Feature

In standard Voice Agents, VAD (Voice Activity Detection) triggers immediately when sound is detected, stopping the agent. This creates a jarring experience if the user just says "Yeah" to confirm listening.

**Our Solution:**
1.  **Semantic Analysis**: We inspect the *content* of the user's speech using Real-time STT.
2.  **Ignored Words**: If the user's input consists entirely of "ignored words" (e.g., "yeah", "sure", "correct"), the agent **continues speaking**.
3.  **Command Prioritization**: If the input contains *any* other word (e.g., "Yeah wait"), the agent **interrupts immediately**.
4.  **VAD Override**: We disable "dumb" VAD interruption in favor of "smart" STT-based interruption.

## 🛠 Configuration

You can customize the list of ignored words using an environment variable.

| Variable | Description | Default |
|----------|-------------|---------|
| `LIVEKIT_IGNORE_WORDS` | Comma-separated list of words to ignore. | `yeah,ok,okay,hmm,uh-huh,right,sure` |

**Example:**
```bash
export LIVEKIT_IGNORE_WORDS="yeah,yep,uh-huh,continue"
```

## 🧪 How It Works (Architecture)

1.  **VAD Interruption Disabled**: The low-level `on_vad_inference_done` handler no longer triggers `interrupt()`.
2.  **STT Stream Handler**: Inside `_interrupt_by_audio_activity` (called when STT events arrive):
    *   We normalize the text (remove punctuation, lowercase).
    *   We match it against the `IGNORE_WORDS` list.
    *   **Match**: Log "Ignoring interruption" and do nothing.
    *   **No Match**: Trigger `interrupt()` (Stop audio, clear queue).

## ✅ Verification & Proof

### 1. Visual Demo (Simulation)
Run the high-fidelity simulation to see the agent's decision-making in real-time (with typewriter effects and state visualization):
```bash
python demo_simulation.py
```
*   **Scenario 1-6:** Standard Ignore/Interrupt cases.
*   **Scenario 7:** **Critical "Silent State" Check** (Proves the agent correctly *responds* to "Yeah" when silent, instead of ignoring it).

### 2. Rigorous Logic Audit (54 Scenarios)
We have generated a massive validation log testing **54 edge cases**, including mixed punctuation, case sensitivity, and complex sentences.
*   **Run Audit:** `python generate_proof_log.py`
*   **View Proof:** [comprehensive_test_log.txt](comprehensive_test_log.txt)

## 📂 Key Files
*   `livekit/agents/voice/interruption_logic.py`: **The Brain** (Pure logic).
*   `livekit/agents/voice/agent_activity.py`: **The Integration** (VAD disable + STT Hook).
*   `demo_simulation.py`: **The Demo** (CLI Simulation).
*   `comprehensive_test_log.txt`: **The Proof** (Validation Log).

## 🧠 Core Logic Explained
The system enables a **Start-of-Turn State Check**:
1.  **If Agent is SPEAKING**: "Yeah" -> **IGNORE** (Backchannel).
2.  **If Agent is SILENT**: "Yeah" -> **PROCESS** (User Answer).

This ensures the user can say "Yeah" to confirm listening (ignored) OR "Yeah" to answer a question (processed).

