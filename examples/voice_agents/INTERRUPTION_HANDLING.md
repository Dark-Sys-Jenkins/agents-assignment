# Voice Agent Interruption Handling

A voice agent implementation using LiveKit that intelligently handles user interruptions and backchannel feedback during conversations. The agent can distinguish between backchannel responses (like "uh-huh", "okay") and actual interruption commands (like "stop", "wait"), enabling more natural conversational interactions.

## Test-Preview Video

Link: https://drive.google.com/file/d/1thBrJN3np9m8IiIuxMy7pm4P0yROP05l/view?usp=sharing

## Overview

This project implements a conversational AI agent named **Bellatrix** that:
- Engages in natural voice conversations
- Detects and handles user interruptions intelligently
- Distinguishes between backchannel feedback and actual interruption commands
- Logs all interaction decisions for analysis

## Components

### `basic_agent.py`
The main agent implementation that:
- Sets up a LiveKit agent server with speech-to-text, LLM, and text-to-speech capabilities
- Uses Deepgram Nova-3 for speech recognition
- Uses Google Gemini 2.5 Flash as the language model
- Uses Cartesia Sonic-2 for text-to-speech
- Implements interruption detection and handling logic
- Logs metrics and usage statistics

### `agent_intruppter_checker.py`
A classification module that:
- Categorizes user input into four types:
  - **BACKCHANNEL**: Feedback words like "uh-huh", "okay", "yes" that don't require interruption
  - **INTERRUPT**: Explicit interruption commands like "stop", "wait", "no"
  - **MIXED**: Longer phrases that may contain interrupt intent
  - **UNKNOWN**: Empty or unrecognized input
- Makes decisions on whether to interrupt the agent based on the classification
- Writes classification results to a report file
- Supports customizable word lists via environment variables

### `report.txt`
A log file that contains:
- All user input classifications
- The category assigned to each input
- Whether an interrupt action was triggered

## Features

### Intelligent Interruption Detection
- Detects explicit interrupt commands (e.g., "stop", "wait", "no")
- Recognizes backchannel feedback and ignores it appropriately
- Handles mixed content by analyzing length and context
- Supports interim (partial) transcriptions for faster response

### Customizable Word Lists
Word lists can be customized via environment variables:
- `BACKCHANNEL_WORDS`: Comma-separated list of backchannel words
- `INTERRUPT_COMMANDS`: Comma-separated list of interrupt commands

### Reporting
All interaction decisions are logged to a report file (configurable via `REPORT_PATH` environment variable, defaults to `report.txt`).

## Setup

### Prerequisites
- Python 3.8+
- LiveKit account and credentials
- Environment variables configured (see Configuration section)

### Installation

1. Install required dependencies:
```bash
pip install livekit-agents livekit-plugins python-dotenv
```

2. Set up environment variables (create a `.env` file):
```env
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
REPORT_PATH=report.txt
BACKCHANNEL_WORDS=ah,aha,hm,hmm,mhm,uh-huh,ok,okay,yes,yeah
INTERRUPT_COMMANDS=stop,wait,no,hold,pause,cancel
```

## Usage

### Running the Agent

Start the agent server:
```bash
python basic_agent.py dev
```

For production deployment:
```bash
python basic_agent.py start
```

### How It Works

1. **User speaks** while the agent is speaking
2. **Speech is transcribed** using Deepgram
3. **Text is classified** by `decision_maker()` into one of four categories
4. **Decision is made**:
   - **BACKCHANNEL**: Agent continues speaking, user input is cleared
   - **INTERRUPT**: Agent is immediately interrupted
   - **MIXED**: Interrupts if 3+ words, otherwise clears user input
   - **UNKNOWN**: No action taken
5. **Result is logged** to the report file

### Example Interactions

Based on `report.txt`:
- `"You know"` → MIXED → Interrupt triggered
- `"Stop and check"` → INTERRUPT → Interrupt triggered
- `"Okay"` → BACKCHANNEL → No interrupt, agent continues
- `"Yep"` → BACKCHANNEL → No interrupt, agent continues
- `"Yeah"` → BACKCHANNEL → No interrupt, agent continues
- `"K"` → MIXED → Interrupt triggered

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LIVEKIT_URL` | LiveKit server WebSocket URL | Required |
| `LIVEKIT_API_KEY` | LiveKit API key | Required |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Required |
| `REPORT_PATH` | Path to report log file | `report.txt` |
| `BACKCHANNEL_WORDS` | Comma-separated backchannel words | See code defaults |
| `INTERRUPT_COMMANDS` | Comma-separated interrupt commands | See code defaults |

### Default Word Lists

**Backchannel Words:**
- `ah`, `aha`, `hm`, `hmm`, `mhm`, `mhmm`
- `uh-huh`, `uh`, `um`, `oh`
- `yes`, `yeah`, `yep`, `yup`
- `ok`, `okay`, `alright`
- `right`, `correct`, `exactly`
- `i see`, `got it`, `makes sense`
- `go on`, `keep going`, `continue`

**Interrupt Commands:**
- `stop`, `wait`, `no`, `hold`, `pause`
- `cancel`, `enough`
- `hold on`, `hang on`, `actually`
- `listen`

## Architecture

```
User Speech
    ↓
Deepgram STT (Nova-3)
    ↓
Transcription Event
    ↓
agent_intruppter_checker.decision_maker()
    ↓
Classification (BACKCHANNEL/INTERRUPT/MIXED/UNKNOWN)
    ↓
Decision (interrupt: True/False)
    ↓
Action (continue/interrupt/clear)
    ↓
Log to report.txt
```

## Classification Logic

The `decision_maker()` function in `agent_intruppter_checker.py` implements the following logic:

1. **Empty/Whitespace Input**: Returns `UNKNOWN` category, no interrupt
2. **First Token Check**: If the first word matches an interrupt command, returns `INTERRUPT` category with interrupt flag
3. **Short Backchannel Check**: If input has 3 or fewer words and contains any backchannel word, returns `BACKCHANNEL` category, no interrupt
4. **Default**: Returns `MIXED` category with interrupt flag for all other cases

The agent then handles each category:
- **BACKCHANNEL**: Clears user turn, agent continues speaking
- **INTERRUPT**: Immediately interrupts agent (works for both interim and final transcriptions)
- **MIXED**: Interrupts if 3+ words, otherwise clears turn
- **UNKNOWN**: No action taken

## Development

### Adding New Categories
To add new classification categories, modify the `Category` enum in `agent_intruppter_checker.py` and update the `decision_maker()` function logic.

### Customizing Classification Logic
The `decision_maker()` function in `agent_intruppter_checker.py` can be extended to implement more sophisticated classification algorithms, such as:
- Machine learning models
- Context-aware analysis
- Multi-word phrase matching
- Sentiment analysis

### Extending the Agent
The interruption handling logic in `basic_agent.py` can be customized in the `on_user_speech()` event handler. You can:
- Adjust the word count threshold for MIXED category
- Add additional context-based rules
- Implement different interrupt strategies
- Add custom logging or metrics

## Troubleshooting

### Agent Not Interrupting
- Check that `allow_interruptions=False` is set (this allows manual interruption control)
- Verify interrupt commands are in the `INTERRUPT_COMMANDS` list
- Check logs for classification results

### Too Many False Interruptions
- Add more words to the `BACKCHANNEL_WORDS` list
- Adjust the word count threshold for MIXED category
- Review report.txt to identify patterns

### Report File Not Updating
- Check `REPORT_PATH` environment variable
- Verify file permissions
- Ensure `write_report()` is being called

## Contributing

- College: IIIT SiCity
- Name: Harsh
- Assignment: Salescode.io
- Email: harshsingh794613@gmail.com
