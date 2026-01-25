<!--BEGIN_BANNER_IMAGE-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/.github/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/.github/banner_light.png">
  <img style="width:100%;" alt="The LiveKit icon, the name of the repository and some sample code in the background." src="https://raw.githubusercontent.com/livekit/agents/main/.github/banner_light.png">
</picture>

<!--END_BANNER_IMAGE-->
<br />

![PyPI - Version](https://img.shields.io/pypi/v/livekit-agents)
[![PyPI Downloads](https://static.pepy.tech/badge/livekit-agents/month)](https://pepy.tech/projects/livekit-agents)
[![Slack community](https://img.shields.io/endpoint?url=https%3A%2F%2Flivekit.io%2Fbadges%2Fslack)](https://livekit.io/join-slack)
[![Twitter Follow](https://img.shields.io/twitter/follow/livekit)](https://twitter.com/livekit)
[![Ask DeepWiki for understanding the codebase](https://deepwiki.com/badge.svg)](https://deepwiki.com/livekit/agents)
[![License](https://img.shields.io/github/license/livekit/livekit)](https://github.com/livekit/livekit/blob/master/LICENSE)

<br />

Looking for the JS/TS library? Check out [AgentsJS](https://github.com/livekit/agents-js)

## What is Agents?

<!--BEGIN_DESCRIPTION-->

The Agent Framework is designed for building realtime, programmable participants
that run on servers. Use it to create conversational, multi-modal voice
agents that can see, hear, and understand.

<!--END_DESCRIPTION-->

## Features

- **Flexible integrations**: A comprehensive ecosystem to mix and match the right STT, LLM, TTS, and Realtime API to suit your use case.
- **Integrated job scheduling**: Built-in task scheduling and distribution with [dispatch APIs](https://docs.livekit.io/agents/build/dispatch/) to connect end users to agents.
- **Extensive WebRTC clients**: Build client applications using LiveKit's open-source SDK ecosystem, supporting all major platforms.
- **Telephony integration**: Works seamlessly with LiveKit's [telephony stack](https://docs.livekit.io/sip/), allowing your agent to make calls to or receive calls from phones.
- **Exchange data with clients**: Use [RPCs](https://docs.livekit.io/home/client/data/rpc/) and other [Data APIs](https://docs.livekit.io/home/client/data/) to seamlessly exchange data with clients.
- **Semantic turn detection**: Uses a transformer model to detect when a user is done with their turn, helps to reduce interruptions.
- **MCP support**: Native support for MCP. Integrate tools provided by MCP servers with one loc.
- **Builtin test framework**: Write tests and use judges to ensure your agent is performing as expected.
- **Open-source**: Fully open-source, allowing you to run the entire stack on your own servers, including [LiveKit server](https://github.com/livekit/livekit), one of the most widely used WebRTC media servers.

## Installation

To install the core Agents library, along with plugins for popular model providers:

```bash
pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0"
```

## Docs and guides

Documentation on the framework and how to use it can be found [here](https://docs.livekit.io/agents/)

## Core concepts

- Agent: An LLM-based application with defined instructions.
- AgentSession: A container for agents that manages interactions with end users.
- entrypoint: The starting point for an interactive session, similar to a request handler in a web server.
- Worker: The main process that coordinates job scheduling and launches agents for user sessions.

## Usage

### Simple voice agent

---

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
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""

    return {"weather": "sunny", "temperature": 70}


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="You are a friendly voice assistant built by LiveKit.",
        tools=[lookup_weather],
    )
    session = AgentSession(
        vad=silero.VAD.load(),
        # any combination of STT, LLM, TTS, or realtime API can be used
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="greet the user and ask about their day")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

You'll need the following environment variables for this example:

- DEEPGRAM_API_KEY
- OPENAI_API_KEY
- ELEVEN_API_KEY

### Multi-agent handoff

---

This code snippet is abbreviated. For the full example, see [multi_agent.py](examples/voice_agents/multi_agent.py)

```python
...
class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"You are a story teller. Your goal is to gather a few pieces of information from the user to make the story personalized and engaging."
            "Ask the user for their name and where they are from"
        )

    async def on_enter(self):
        self.session.generate_reply(instructions="greet the user and gather information")

    @function_tool
    async def information_gathered(
        self,
        context: RunContext,
        name: str,
        location: str,
    ):
        """Called when the user has provided the information needed to make the story personalized and engaging.

        Args:
            name: The name of the user
            location: The location of the user
        """

        context.userdata.name = name
        context.userdata.location = location

        story_agent = StoryAgent(name, location)
        return story_agent, "Let's start the story!"


class StoryAgent(Agent):
    def __init__(self, name: str, location: str) -> None:
        super().__init__(
            instructions=f"You are a storyteller. Use the user's information in order to make the story personalized."
            f"The user's name is {name}, from {location}"
            # override the default model, switching to Realtime API from standard LLMs
            llm=openai.realtime.RealtimeModel(voice="echo"),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    userdata = StoryData()
    session = AgentSession[StoryData](
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="echo"),
        userdata=userdata,
    )

    await session.start(
        agent=IntroAgent(),
        room=ctx.room,
    )
...
```

### Testing

Automated tests are essential for building reliable agents, especially with the non-deterministic behavior of LLMs. LiveKit Agents include native test integration to help you create dependable agents.

```python
@pytest.mark.asyncio
async def test_no_availability() -> None:
    llm = google.LLM()
    async AgentSession(llm=llm) as sess:
        await sess.start(MyAgent())
        result = await sess.run(
            user_input="Hello, I need to place an order."
        )
        result.expect.skip_next_event_if(type="message", role="assistant")
        result.expect.next_event().is_function_call(name="start_order")
        result.expect.next_event().is_function_call_output()
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(llm, intent="assistant should be asking the user what they would like")
        )

```

## Examples

<table>
<tr>
<td width="50%">
<h3>🎙️ Starter Agent</h3>
<p>A starter agent optimized for voice conversations.</p>
<p>
<a href="examples/voice_agents/basic_agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🔄 Multi-user push to talk</h3>
<p>Responds to multiple users in the room via push-to-talk.</p>
<p>
<a href="examples/voice_agents/push_to_talk.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🎵 Background audio</h3>
<p>Background ambient and thinking audio to improve realism.</p>
<p>
<a href="examples/voice_agents/background_audio.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🛠️ Dynamic tool creation</h3>
<p>Creating function tools dynamically.</p>
<p>
<a href="examples/voice_agents/dynamic_tool_creation.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>☎️ Outbound caller</h3>
<p>Agent that makes outbound phone calls</p>
<p>
<a href="https://github.com/livekit-examples/outbound-caller-python">Code</a>
</p>
</td>
<td width="50%">
<h3>📋 Structured output</h3>
<p>Using structured output from LLM to guide TTS tone.</p>
<p>
<a href="examples/voice_agents/structured_output.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🔌 MCP support</h3>
<p>Use tools from MCP servers</p>
<p>
<a href="examples/voice_agents/mcp">Code</a>
</p>
</td>
<td width="50%">
<h3>💬 Text-only agent</h3>
<p>Skip voice altogether and use the same code for text-only integrations</p>
<p>
<a href="examples/other/text_only.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📝 Multi-user transcriber</h3>
<p>Produce transcriptions from all users in the room</p>
<p>
<a href="examples/other/transcription/multi-user-transcriber.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🎥 Video avatars</h3>
<p>Add an AI avatar with Tavus, Beyond Presence, and Bithuman</p>
<p>
<a href="examples/avatar_agents/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🍽️ Restaurant ordering and reservations</h3>
<p>Full example of an agent that handles calls for a restaurant.</p>
<p>
<a href="examples/voice_agents/restaurant_agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>👁️ Gemini Live vision</h3>
<p>Full example (including iOS app) of Gemini Live agent that can see.</p>
<p>
<a href="https://github.com/livekit-examples/vision-demo">Code</a>
</p>
</td>
</tr>

</table>

## Running your agent

### Testing in terminal

```shell
python myagent.py console
```

Runs your agent in terminal mode, enabling local audio input and output for testing.
This mode doesn't require external servers or dependencies and is useful for quickly validating behavior.

### Developing with LiveKit clients

```shell
python myagent.py dev
```

Starts the agent server and enables hot reloading when files change. This mode allows each process to host multiple concurrent agents efficiently.

The agent connects to LiveKit Cloud or your self-hosted server. Set the following environment variables:
- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET

You can connect using any LiveKit client SDK or telephony integration.
To get started quickly, try the [Agents Playground](https://agents-playground.livekit.io/).

## 🎯 Intelligent Interruption Handling

This agent implements sophisticated interruption handling that distinguishes between **soft acknowledgements** (fillers) and **real interruptions**. This prevents the agent from pausing unnecessarily when users say "yeah," "okay," or "uh-huh" while listening.

### 🧠 How It Works

The interruption system operates in three stages:

#### 1. **VAD (Voice Activity Detection) - First Line**
- Detects audio activity in real-time using the Silero VAD model
- Fires immediately when speech is detected (faster than STT)
- When VAD triggers while the agent is speaking:
  - Sets a `_pending_interruption` flag
  - **Does NOT pause immediately** - waits for STT confirmation

#### 2. **STT (Speech-to-Text) - Validation Layer**
- Transcribes the user's speech with ~0.5-0.7s delay
- Analyzes the transcript using the `InterruptionFilter`
- Three possible outcomes:

   **a) Filler words detected while agent is speaking:**
   ```python
   User: "yeah" (while agent speaking)
   Decision: IGNORE → Continue speaking without pause
   ```
   - Sets `_ignore_current_user_turn = True`
   - Clears `_pending_interruption`
   - **Agent continues speaking seamlessly**

   **b) Interrupt words detected:**
   ```python
   User: "wait" or "stop" (while agent speaking)
   Decision: INTERRUPT → Stop immediately
   ```
   - Calls `interrupt()` to cancel current speech
   - Clears `_pending_interruption`
   - Agent stops and listens

   **c) Filler words when agent is silent:**
   ```python
   User: "yeah" (agent silent)
   Decision: RESPOND → Treat as valid input
   ```
   - Agent generates appropriate response
   - Example: "Great! What would you like to talk about?"

#### 3. **Turn Detection - Final Gate**
- End-of-utterance (EOU) model predicts when user has finished speaking
- Before triggering a response:
  ```python
  if self._ignore_current_user_turn:
      return False  # Drop this turn entirely
  ```
- Prevents the LLM from wasting tokens on "yeah" / "okay"

### 🔧 State Management

The system tracks agent speaking state through multiple sources:

1. **Session state**: `self._session.agent_state == "speaking"`
2. **Active speech tasks**: `self._speech_tasks` not empty
3. **Paused speech**: `self._paused_speech` is not None
4. **Audio playback**: `audio_output.is_playing` (checks pending frames)

```python
def _agent_is_speaking(self) -> bool:
    # Most authoritative: session state
    if self._session.agent_state == "speaking":
        return True
    
    # Fallback checks for edge cases
    if any(not t.done() for t in self._speech_tasks) or self._paused_speech:
        return True
    
    # Check if audio is still queued for playback
    audio_output = self._session.output.audio
    return bool(audio_output and audio_output.is_playing)
```

### 📋 Configuration

#### Environment Variables
Override default word lists for your use case. The system automatically parses comma-separated values and lowercases them.

**How it works:**
1. **Default values** are defined in `interrupt_filter.py`
2. **Environment variables override** defaults in `agent_activity.py`
3. Words are automatically **lowercased and trimmed**
4. Empty environment variable → **falls back to defaults**

### 🧪 Testing Scenarios

#### 🎥 Video Demonstration
Watch the complete testing demonstration:  
**[View Demo Video](https://drive.google.com/file/d/1LBsiFXKJMqZQ3kyvM8HrwBV74nPXppJx/view?usp=drivesdk)**

#### Test Cases

| User Input | Agent State | Expected Behavior | Result |
|------------|-------------|-------------------|--------|
| "yeah" | Speaking | Continue without pause | ✅ IGNORE |
| "okay" | Speaking | Continue without pause | ✅ IGNORE |
| "stop" | Speaking | Stop immediately | ✅ INTERRUPT |
| "wait" | Speaking | Stop immediately | ✅ INTERRUPT |
| "yeah" | Silent | Generate response | ✅ RESPOND |
| "hello" | Silent | Generate response | ✅ RESPOND |

### 🚀 Running the Agent

#### 1. Install Dependencies

**Using requirements.txt (Recommended)**
```bash
pip install -r requirements.txt
```

#### 2. Download Model Files
```bash
python examples/voice_agents/basic_agent.py download-files
```

#### 3. Set Environment Variables
Create a `.env` file:
```bash
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Optional: Customize interruption words
LK_IGNORE_WORDS="yeah,ok,okay,hmm,uh-huh,right,yep,ah"
LK_INTERRUPT_WORDS="wait,stop,no,hold,cancel"
```

#### 4. Run in Console Mode (Testing)
```bash
python examples/voice_agents/basic_agent.py console
```

**Test the interruption logic:**
1. Say "Tell me a long story"
2. While the agent is speaking, say "yeah" or "okay" → Agent continues
3. While the agent is speaking, say "stop" → Agent stops immediately
4. When agent is silent, say "yeah" → Agent responds appropriately

#### 5. Run in Development Mode
```bash
# Set LiveKit server credentials
export LIVEKIT_URL=wss://your-server.livekit.cloud
export LIVEKIT_API_KEY=your_api_key
export LIVEKIT_API_SECRET=your_api_secret

# Start the agent server
python examples/voice_agents/basic_agent.py dev
```

Connect using the [Agents Playground](https://agents-playground.livekit.io/)

### 📊 System Architecture

```
User Speech
    ↓
┌─────────────────────────────────────────────────┐
│ 1. VAD Detection (Silero)                      │
│    - Fast audio activity detection              │
│    - Sets _pending_interruption if speaking    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 2. STT Transcription (Deepgram)                │
│    - Converts speech to text                    │
│    - ~0.5-0.7s latency                         │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 3. Interruption Filter Analysis                │
│    ┌─────────────────────────────────────────┐ │
│    │ Is agent speaking?                      │ │
│    │  YES → Check word lists                 │ │
│    │    - In IGNORE_WORDS? → DROP TURN       │ │
│    │    - In INTERRUPT_WORDS? → INTERRUPT    │ │
│    │    - Neither? → Normal handling         │ │
│    │  NO → Treat as valid input              │ │
│    └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 4. Turn Detection (Multilingual EOU)           │
│    - Checks _ignore_current_user_turn flag     │
│    - If True → Return False (skip LLM call)    │
│    - If False → Trigger agent response         │
└─────────────────────────────────────────────────┘
```

## Contributing

The Agents framework is under active development in a rapidly evolving field. We welcome and appreciate contributions of any kind, be it feedback, bugfixes, features, new plugins and tools, or better documentation. You can file issues under this repo, open a PR, or chat with us in LiveKit's [Slack community](https://livekit.io/join-slack).

<!--BEGIN_REPO_NAV-->
<br/><table>
<thead><tr><th colspan="2">LiveKit Ecosystem</th></tr></thead>
<tbody>
<tr><td>LiveKit SDKs</td><td><a href="https://github.com/livekit/client-sdk-js">Browser</a> · <a href="https://github.com/livekit/client-sdk-swift">iOS/macOS/visionOS</a> · <a href="https://github.com/livekit/client-sdk-android">Android</a> · <a href="https://github.com/livekit/client-sdk-flutter">Flutter</a> · <a href="https://github.com/livekit/client-sdk-react-native">React Native</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/client-sdk-unity">Unity</a> · <a href="https://github.com/livekit/client-sdk-unity-web">Unity (WebGL)</a> · <a href="https://github.com/livekit/client-sdk-esp32">ESP32</a></td></tr><tr></tr>
<tr><td>Server APIs</td><td><a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/server-sdk-go">Golang</a> · <a href="https://github.com/livekit/server-sdk-ruby">Ruby</a> · <a href="https://github.com/livekit/server-sdk-kotlin">Java/Kotlin</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/agence104/livekit-server-sdk-php">PHP (community)</a> · <a href="https://github.com/pabloFuente/livekit-server-sdk-dotnet">.NET (community)</a></td></tr><tr></tr>
<tr><td>UI Components</td><td><a href="https://github.com/livekit/components-js">React</a> · <a href="https://github.com/livekit/components-android">Android Compose</a> · <a href="https://github.com/livekit/components-swift">SwiftUI</a> · <a href="https://github.com/livekit/components-flutter">Flutter</a></td></tr><tr></tr>
<tr><td>Agents Frameworks</td><td><b>Python</b> · <a href="https://github.com/livekit/agents-js">Node.js</a> · <a href="https://github.com/livekit/agent-playground">Playground</a></td></tr><tr></tr>
<tr><td>Services</td><td><a href="https://github.com/livekit/livekit">LiveKit server</a> · <a href="https://github.com/livekit/egress">Egress</a> · <a href="https://github.com/livekit/ingress">Ingress</a> · <a href="https://github.com/livekit/sip">SIP</a></td></tr><tr></tr>
<tr><td>Resources</td><td><a href="https://docs.livekit.io">Docs</a> · <a href="https://github.com/livekit-examples">Example apps</a> · <a href="https://livekit.io/cloud">Cloud</a> · <a href="https://docs.livekit.io/home/self-hosting/deployment">Self-hosting</a> · <a href="https://github.com/livekit/livekit-cli">CLI</a></td></tr>
</tbody>
</table>
<!--END_REPO_NAV-->
