# LiveKit Intelligent Interruption Handler

## Overview
This project implements a "Smart Interruption" agent using LiveKit. It solves a common problem in voice AI where the agent stops speaking when the user provides passive feedback (backchanneling) like "yeah" or "uh-huh".

The agent uses a logic layer to distinguish between:
1.  **Passive Acknowledgement (Soft Words):** The agent ignores words like "yeah", "ok", "cool" and continues speaking.
2.  **Active Interruption (Commands):** The agent stops immediately for commands like "stop", "wait", or "no".

## Video Proof
Here is the demo of the agent handling interruptions and backchanneling correctly:
* **YouTube:** [Watch Demo](https://www.youtube.com/watch?v=6OORk3eroAQ)
* **Google Drive:** [Watch Demo](https://drive.google.com/file/d/1BcWSkRe9glIQNG9Vd0uLz2FZ_u8b9nDM/view?usp=sharing)

## Features
* **Configurable Ignore List:** A defined set of "soft words" that do not trigger a full interruption.
* **Semantic Interruptions:** Detects mixed sentences (e.g., "Yeah wait a second") as valid interruptions because they contain a stop command.
* **Auto-Resumption:** Utilizes LiveKit's `resume_false_interruption` to seamlessly continue speech if a false interruption is detected.

## Logic Implementation
The core logic resides in the `on_user_input` event handler:

1.  **Text Normalization:** All user input is converted to lowercase and stripped of punctuation.
2.  **Stop Word Check:** If the input contains a hard command (e.g., "stop", "wait"), the agent forces an interruption.
3.  **Filler Check:** If the input consists *only* of filler words (e.g., "yeah okay"), the agent logs it as a "Soft word" and allows the VAD to resume the audio stream automatically.

## How It Works

1. **Configurable Word Lists**
   - `SOFT_WORDS`: Filler words to ignore while speaking
   - `STOP_WORDS`: Commands that always interrupt

2. **Key Settings**
   - `min_interruption_words=3`: Single words don't auto-interrupt
   - `resume_false_interruption=True`: Resume after false alarms
   - `false_interruption_timeout=2.5`: Wait before deciding

3. **Event Handler**: Listens to `user_input_transcribed` and filters based on word content


## Setup & Run

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory and add your keys:
    ```env
    LIVEKIT_URL=wss://your-project.livekit.cloud
    LIVEKIT_API_KEY=your_api_key
    LIVEKIT_API_SECRET=your_api_secret
    DEEPGRAM_API_KEY=your_deepgram_key
    GROQ_API_KEY=your_groq_key
    ```

4.  **Run the Agent:**
    To run in development mode (connects to a local room):
    ```bash
    python intelligent_interruption.py dev
    ```

## Logic Matrix (Expected Behavior)

| User Input | Context | Agent Action |
| :--- | :--- | :--- |
| "Yeah", "okay", "yes" | Agent Speaking | **IGNORE** (Continues speaking) |
| "Stop", "Wait", "No" | Agent Speaking | **INTERRUPT** (Stops immediately) |
| "Yeah stop " | Agent Speaking | **INTERRUPT** (Mixed input detected) |
| "start" | Agent Silent | **RESPOND** (Treats as conversation) |

## Author
Aditya Singh

