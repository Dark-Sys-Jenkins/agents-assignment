# 🎤 Smart Voice AI Chatbot with Interruption Handling

This project implements a real-time voice chatbot with intelligent interruption handling.

The agent ignores soft acknowledgements like:
- "yeah"
- "ok"
- "hmm"
- "right"

while speaking, but immediately interrupts on meaningful commands like:
- "stop"
- "wait"
- "cancel"

---

## 🚀 Features
- Real-time speech recognition
- AI response generation
- Text-to-speech output
- Smart interruption filtering
- Configurable ignore and interrupt word lists

---

## 🧠 Interruption Logic

If agent is speaking:
- Only ignore words → ignored
- Any command word → interrupt
- Mixed sentence → interrupt

If agent is silent:
- All speech is processed normally

---

## 🛠 Installation

```bash
pip install -r requirements.txt

