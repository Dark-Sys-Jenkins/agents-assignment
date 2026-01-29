# Romania: Smart Interruption Voice Agent

This project implements a custom LiveKit Voice Agent named **Romania**. Unlike standard agents that stop speaking immediately upon any user speech, Romania uses Smart Interruption Logic to distinguish between backchanneling (e.g., "uh-huh", "yeah") and true interruption commands (e.g., "stop", "wait"). This enables more natural, conversational interactions.

## 🧠 Agent Logic & Behavior

### 1. Persona
- **Name:** Romania
- **Personality:** Curious, friendly, lightly humorous
- **Constraint:** Speaks only English, concise responses, no special characters/markdown in speech

### 2. Smart Interruption ("Special Sauce")
- **Soft Interruptions (Backchanneling):**
  - Words like "yeah", "ok", "uh-huh", or "right" are treated as active listening.
  - The agent resumes speaking automatically, ignoring the interruption.
  - Mechanism: On `user_transcript` event, if transcript matches `SOFT_INTERRUPT_WORDS`, calls `session.resume()`.
- **Hard Interruptions (Commands):**
  - Words like "wait", "stop", or "hold on" are respected; the agent stops and listens.
  - Mechanism: Checked against `INTERRUPT_KEYWORDS`.
- **Standard Input:**
  - Any other sentence is treated as a normal turn; the agent stops to answer.

## 🚀 How to Run
Run the agent using the LiveKit CLI or directly with Python:

- **Console Mode:**
  ```bash
  python trial1.py console
  ```
- **Dev Mode:**
  ```bash
  python trial1.py dev
  ```

## 📂 Code Structure Overview
- **MyAgent Class:** Defines system prompt and persona
- **SOFT_INTERRUPT_WORDS:** Words that allow the agent to keep talking
- **INTERRUPT_KEYWORDS:** Words that force an immediate stop
- **entrypoint function:**
  - Initializes STT (Deepgram), LLM (OpenAI), TTS (Cartesia)
  - Sets up noise cancellation (Krisp)
- **_on_user_transcript:**
  - Analyzes user text while agent is speaking to determine if `session.resume()` should be called

---

For more details, see the code and comments in `trial1.py`.
