# Voice AI Agent with Intelligent Interruption Gating

This project implements a production-ready Voice AI Agent using LiveKit Agents. The core innovation in this version is the implementation of an Intelligent Interruption Gater, which allows the agent to distinguish between meaningful user interruptions and simple "filler" speech (backchannels).

## 🎥 Demo

Watch the demo video: [Voice AI Agent Demo](https://drive.google.com/file/d/125JVzWRg88kvYJY8cGptZOHZD8jnbeEZ/view?usp=sharing)

## 🚀 How to Run

### 1. Clone the Repository
```bash
git clone -b feature/interrupt-handler-pranav https://github.com/pranav6905/agents-assignment.git
cd agents-assignment
```

### 2. Install Dependencies

**Option 1: Using pip**

Alternatively, you can install dependencies using pip:
```bash
pip install -r examples/voice_agents/requirements.txt
```

**Option 2: Using uv**

This project uses `uv` for dependency management:
```bash
uv sync
```

If you don't have `uv` installed, install it first:
```bash
pip install uv
```

### 3. Configure Environment

Create a `.env` file and add your credentials and the custom ignore list:
```plaintext
LIVEKIT_URL=<your-url>
LIVEKIT_API_KEY=<your-key>
LIVEKIT_API_SECRET=<your-secret>
IGNORE_WORDS="yeah,yes,yep,ok,okay,hmm,mhm,uh-huh,right,sure,cool,gotcha"
```

### 4. Start the Agent

- **Development Mode (Playground):** `python basic_agent.py dev`
- **Console Mode:** `python basic_agent.py console`

## 🧠 Core Logic & Changes

The primary challenge addressed in this assignment is the "Hiccup Problem": standard AI agents stop speaking as soon as they detect any user sound, even if the user is just nodding along saying "Okay" or "Yeah."

### 1. Intelligent Interruption Gating (`is_filler_speech`)

I implemented a robust NLP check that analyzes the user's transcript in real-time.

- **Logic:** It cleans the incoming text (removing punctuation and casing) and checks it against a dynamic `IGNORE_WORDS` set loaded from the environment.
- **Result:** If the user says a filler word while the agent is speaking, the interruption is blocked, and the agent continues its story/task without a stutter.

### 2. Double-Hook Protection

To ensure the agent doesn't "re-trigger" after a filler word, I added the logic to two critical points in the `AgentActivity` pipeline:

- `_interrupt_by_audio_activity`: Prevents the agent from pausing or stopping the current audio playback for backchannels.
- `on_end_of_turn`: Prevents the LLM from generating a brand-new response (e.g., "You're welcome!") if the user only said "OK."

### 3. Production-Grade Configuration

Following system architecture best practices, I moved all "listening" parameters to the Environment Level. This allows the system to be scaled or localized (adding new filler words for different languages) without changing the core logic.


## 🔧 Key Features

- **Intelligent Interruption Detection**: Distinguishes between meaningful interruptions and conversational backchannels
- **Configurable Filler Words**: Easy to customize via environment variables
- **Production-Ready**: Built with scalability and maintainability in mind
- **LiveKit Integration**: Leverages LiveKit's robust voice infrastructure
