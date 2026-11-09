# Voice Interview Coach

A real-time voice practice app that runs short, role-specific mock interviews.
It combines a curated question plan with conversational feedback. It is a practice
tool, not a hiring assessment or an objective scoring system.

This is a standalone application repository. It installs LiveKit Agents and its
OpenAI and Silero integrations as Python dependencies; the framework and plugin
source code are not vendored here. The retained [LICENSE](LICENSE) and
[NOTICE](NOTICE) preserve the upstream licensing and attribution.

## Features

- Backend engineer, data analyst, and product manager question tracks.
- Beginner, intermediate, and advanced question plans.
- Four questions per session, asked one at a time.
- Feedback is grounded in the candidate's answer and avoids invented details or
  hiring predictions.
- Environment-based configuration with validation before starting a session.
- Unit tests for question selection and configuration; no provider credentials
  are needed to run those tests.

## Architecture

```text
src/interview_coach/
  ├─ worker.py         starts the LiveKit agent and voice session
  ├─ settings.py       validates role, level, model, voice, and API-key presence
  ├─ agent.py          turns the selected plan into coaching instructions
  └─ questions.py      provides the curated role/level question sequences
```

The app does not persist interview answers. Audio and model requests are processed
by the configured LiveKit and OpenAI services; review their data-handling terms
before using sensitive personal information.

## Requirements

- Python 3.10 or newer.
- An OpenAI API key for live interviews.
- For `dev` mode, a LiveKit project URL, API key, and API secret.
- A working audio input/output device for local `console` mode.

## Install

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. Optionally set:

| Variable | Default | Description |
|---|---|---|
| `INTERVIEW_ROLE` | `backend engineer` | `backend engineer`, `data analyst`, or `product manager` |
| `INTERVIEW_LEVEL` | `intermediate` | `beginner`, `intermediate`, or `advanced` |
| `OPENAI_LLM_MODEL` | `gpt-4o-mini` | OpenAI model used for responses |
| `OPENAI_TTS_VOICE` | `echo` | OpenAI text-to-speech voice |

`LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` are needed only when
connecting through LiveKit server mode. Keep real credentials out of source control.

## Run

Local audio console:

```powershell
voice-interview-coach console
```

Connect through a LiveKit project:

```powershell
voice-interview-coach dev
```

Console mode does not require a LiveKit server, but it still requires the OpenAI
API key and provider access configured above.

## Test

The unit tests cover only local configuration and question-plan logic and do not
call external services:

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Limitations

- Question plans are curated examples, not a comprehensive or validated interview
  curriculum.
- Feedback quality depends on the configured model and the clarity of the answer.
- There is no transcript storage, analytics dashboard, or objective score.
- The app requires a network connection to the configured OpenAI service.
