# Semantic Interruption Logic Layer

This agent implements a "Semantic Gate" that solves the backchannel interruption problem. 

## 🧠 Logic 
1.  **VAD Decoupling:** The agent does not hard-stop on VAD.
2.  **Semantic Filter:** * If `AgentState == SPEAKING` AND `Input == Backchannel` (e.g. "Yeah") → **IGNORE**.
    * If `Input == Command` (e.g., "Stop") → **INTERRUPT**.

## 🚀 How to Run
```bash
pip install -r requirements.txt
python examples/semantic-interrupt-agent/agent.py dev