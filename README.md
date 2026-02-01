# Interrupt Handler for LiveKit Agents

This project extends **LiveKit Agents** with a manual turn-detection pipeline and a
custom interrupt controller. The goal is to reduce false interruptions from backchannel
utterances (e.g., “yeah”, “uh-huh”) while still honoring explicit interrupt words.
## Video Solution

Watch the prepared assignment solution: [Video Link](https://drive.google.com/file/d/1jq7hFIStgqCHk_kn7PFOVdT8bnMb3Gdl/view?usp=sharing)

### Additional Resources

- [Interrupt Handler Flow Documentation](interrupt-handler-flow.md) — Detailed workflow and logic explanation
- [Agent Logs](history_agent.log) — Runtime logs and debugging information

## Features

- Manual turn detection with custom interrupt logic.
- Configurable `ignore_words`, `interrupt_words`, and grace window.
- Shared logging and modular event wiring.
- Multi-agent storytelling example plus a simple single-agent demo.

## Project structure

- [history_agent.py](history_agent.py) — Main voice agent entrypoint (manual turn detection).
- [interrupt_controller.py](interrupt_controller.py) — Interrupt decision logic.
- [session_handlers.py](session_handlers.py) — Event wiring for metrics and interrupt handling.
- [logging_utils.py](logging_utils.py) — Shared logger setup.
- [config.py](config.py) — Provider models and environment configuration.
- [original_agent.py](original_agent.py) — Baseline multi-agent example without interrupt handlers.

## How the pipeline works

1. **Agent state changes** update the interrupt controller (speaking vs idle).
2. **User speech transcription** triggers manual interrupt checks.
3. **`InterruptController.should_interrupt()`** decides whether to interrupt or ignore.
4. If interrupted, `session.interrupt()` runs; otherwise the user turn is committed.

## Setup

### Requirements

- Python 3.9+
- LiveKit Agents and required plugins (see [pyproject.toml](pyproject.toml))

### Environment variables

Set these in a `.env` file (see [config.py](config.py)):

- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `CASTERIA_API_KEY` (Cartesia TTS)
- `GEMINI_API_KEY` (optional)
- `OPEN_ROUTER_API_KEY` (optional)
- `ELEVENLABS_API_KEY` (optional)

## Run examples

### Multi-agent history storyteller

```bash
python history_agent.py dev
```

## Notes

- Logs are written to `history_agent.log` (plus console output).
- Custom interrupt logic lives in [interrupt_controller.py](interrupt_controller.py).
