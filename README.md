# LiveKit Agents Framework

![PyPI - Version](https://img.shields.io/pypi/v/livekit-agents)
[![PyPI Downloads](https://static.pepy.tech/badge/livekit-agents/month)](https://pepy.tech/projects/livekit-agents)
[![Slack community](https://img.shields.io/endpoint?url=https%3A%2F%2Flivekit.io%2Fbadges%2Fslack)](https://livekit.io/join-slack)
[![Twitter Follow](https://img.shields.io/twitter/follow/livekit)](https://twitter.com/livekit)
[![License](https://img.shields.io/github/license/livekit/livekit)](https://github.com/livekit/livekit/blob/master/LICENSE)

## 🎥 Project Demo Video

👉 **Watch the complete project demo here:**  
**https://drive.google.com/file/d/1332n-VWiKf-PM9jlrEVUXmh2oJpCwJw_/view?usp=sharing**

---

Looking for the JS/TS library? Check out [AgentsJS](https://github.com/livekit/agents-js)

## What is Agents?

The Agent Framework is designed for building realtime, programmable participants that run on servers. Use it to create conversational, multi-modal voice agents that can see, hear, and understand.

## Features

- **Flexible integrations**: A comprehensive ecosystem to mix and match the right STT, LLM, TTS, and Realtime API to suit your use case.
- **Integrated job scheduling**: Built-in task scheduling and distribution with dispatch APIs to connect end users to agents.
- **Extensive WebRTC clients**: Build client applications using LiveKit's open-source SDK ecosystem, supporting all major platforms.
- **Telephony integration**: Works seamlessly with LiveKit's telephony stack, allowing your agent to make or receive phone calls.
- **Exchange data with clients**: Use RPCs and Data APIs to seamlessly exchange data with clients.
- **Semantic turn detection**: Uses a transformer model to detect when a user is done speaking, reducing interruptions.
- **MCP support**: Native support for MCP to integrate tools provided by MCP servers.
- **Built-in test framework**: Write tests and use judges to validate agent behavior.
- **Open-source**: Fully open-source and self-hostable, including the LiveKit server.

## Installation

```bash
pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0"
```

## Docs and Guides

Documentation is available at: https://docs.livekit.io/agents/

## Core Concepts

- **Agent**: An LLM-powered application with defined instructions.
- **AgentSession**: Manages agent interaction with end users.
- **Entrypoint**: Starting point for an interactive session.
- **Worker**: Coordinates job scheduling and agent execution.

## Usage

### Simple Voice Agent

```python
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, openai, silero

@function_tool
async def lookup_weather(context: RunContext, location: str):
    return {"weather": "sunny", "temperature": 70}

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="You are a friendly voice assistant built by LiveKit.",
        tools=[lookup_weather],
    )

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply("Greet the user and ask about their day")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

## Running Your Agent

### Terminal Testing
```bash
python myagent.py console
```

### Development Mode
```bash
python myagent.py dev
```

### Production Mode
```bash
python myagent.py start
```

**Environment variables required:**
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

## Contributing

Contributions are welcome! You can submit issues, open PRs, or join the LiveKit Slack community for discussions and support.

---

## LiveKit Ecosystem

| Category | Links |
|----------|-------|
| **Agents Frameworks** | **Python** · [Node.js](https://github.com/livekit/agents-js) · [Playground](https://github.com/livekit/agent-playground) |
| **Resources** | [Docs](https://docs.livekit.io) · [Examples](https://github.com/livekit-examples) · [Cloud](https://livekit.io/cloud) |