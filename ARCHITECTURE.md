# LiveKit Agents Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Project Structure](#project-structure)
5. [Workflow](#workflow)
6. [Module Descriptions](#module-descriptions)
7. [Plugin System](#plugin-system)
8. [Data Flow](#data-flow)

---

## Overview

**LiveKit Agents** is a powerful Python framework for building real-time, programmable AI agents that run on servers. It enables the creation of conversational, multi-modal voice agents capable of seeing, hearing, and understanding users through the WebRTC protocol.

### Key Features:
- **Flexible Integrations**: Mix and match STT (Speech-to-Text), LLM (Large Language Models), TTS (Text-to-Speech), and Realtime APIs
- **Job Scheduling**: Built-in task scheduling and distribution via dispatch APIs
- **WebRTC Support**: Extensive WebRTC client support across platforms
- **Telephony Integration**: SIP stack integration for phone calls
- **Data Exchange**: RPC (Remote Procedure Call) and Data APIs for client communication
- **Turn Detection**: ML-based turn detection to reduce interruptions
- **MCP Support**: Model Context Protocol integration for tools
- **Testing Framework**: Built-in testing and judgment system

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     LiveKit Agents Framework                    │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        User Applications                          │
│  (Voice Agents, Avatar Agents, IVR Systems, Drive-Thru, etc.)   │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Core Agent Framework                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Job Management (Worker, JobContext, JobRequest)         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Agent System (Agent, AgentSession, AgentTask)           │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Voice Pipeline (STT, LLM, TTS, VAD, Audio I/O)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Tool & Function System (FunctionTool, ToolContext)      │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Chat & LLM Context (ChatContext, ChatMessage)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
    ┌─────────────────────────┐  ┌──────────────────────┐
    │   Plugin Ecosystem      │  │  Inference Runners   │
    │  (40+ Integrations)     │  │  & Executors         │
    │                         │  │                      │
    │ • OpenAI               │  │ • STT Executor       │
    │ • Anthropic            │  │ • LLM Executor       │
    │ • Google Cloud         │  │ • TTS Executor       │
    │ • Azure                │  │ • VAD Executor       │
    │ • Deepgram             │  └──────────────────────┘
    │ • ElevenLabs           │
    │ • And 30+ more...      │
    └─────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │  LiveKit Media Server (WebRTC) │
    │  + LiveKit API + SIP Stack     │
    └────────────────────────────────┘
```

---

## Core Components

### 1. **Worker & Job Management**

#### `worker.py`
The heart of the framework that manages agent instances and handles incoming jobs.

**Key Classes:**
- `AgentServer`: Main server class that listens for job requests and manages agent lifecycle
- `WorkerOptions`: Configuration for worker startup and behavior

**Responsibilities:**
- Accepts job requests from LiveKit servers
- Spawns/manages agent processes or threads
- Handles job scheduling and distribution
- Manages worker health and load reporting
- Implements heartbeat mechanism for server synchronization

#### `job.py`
Handles individual job execution contexts and lifecycle.

**Key Classes:**
- `JobContext`: Container for a single agent session with full room and participant access
- `JobRequest`: Incoming job request from the server
- `JobProcess`: Process/thread wrapper for job execution
- `JobExecutorType`: ENUM for PROCESS or THREAD execution mode

**Key Methods:**
- `connect()`: Connect to LiveKit room
- `accept()`: Accept a job request
- `reject()`: Reject a job request
- `shutdown()`: Clean shutdown of job context

---

### 2. **Agent System**

#### `voice/agent.py`
Defines individual agent behavior and configuration.

**Key Class: `Agent`**

```python
class Agent:
    """A conversational AI agent with defined instructions and tools"""
    
    __init__(
        instructions: str,          # Agent's system prompt
        id: str | None,            # Agent identifier
        tools: list[FunctionTool], # Available tools/functions
        stt: STT,                  # Speech-to-Text model
        llm: LLM,                  # Language model
        tts: TTS,                  # Text-to-Speech model
        vad: VAD,                  # Voice Activity Detection
        ...
    )
```

**Properties:**
- `id`: Unique agent identifier
- `instructions`: System prompt/instructions for the agent
- `tools`: List of callable functions available to the agent
- `stt`, `llm`, `tts`, `vad`: Models and processors

**Workflow Methods:**
- `on_enter()`: Called when agent session starts
- `on_exit()`: Called when agent session ends
- `on_message()`: Process incoming messages
- `on_tool_call()`: Handle tool invocations

#### `voice/agent_session.py`
Manages a session between an agent and users in a room.

**Key Class: `AgentSession`**

```python
class AgentSession(EventEmitter, Generic[Userdata_T]):
    """
    Manages real-time interaction between an agent and room participants
    """
    
    async def start(
        agent: Agent,
        room: rtc.Room
    ) -> None:
        """Start the agent session in a room"""
```

**Key Methods:**
- `start()`: Start agent interaction in a room
- `generate_reply()`: Generate and send agent response
- `accept_input()`: Accept user input
- `close()`: End the session
- `on_event()`: Register event handlers

**Events Emitted:**
- `agent_state_changed`: When agent state changes
- `user_input_transcribed`: When user speech is transcribed
- `conversation_item_added`: New conversation item
- `close`: Session ending

---

### 3. **Voice Pipeline Components**

These are the core building blocks for voice processing:

#### `stt.py` - Speech-to-Text
Converts audio streams to text.

**Interface:**
```python
class STT(ABC):
    """Base class for STT providers"""
    
    async def recognize(
        audio_stream: AsyncIterable[rtc.AudioFrame]
    ) -> str:
        """Recognize speech from audio stream"""
```

#### `llm/` - Language Model Interface
Interfaces with large language models.

**Key Classes:**
- `LLM`: Interface for text-based LLM
- `RealtimeModel`: Interface for real-time APIs (like OpenAI Realtime)
- `ChatContext`: Maintains conversation history
- `ChatMessage`: Individual message in conversation

**Usage Example:**
```python
llm = openai.LLM(model="gpt-4o")
response = await llm.chat(messages=chat_context.messages)
```

#### `tts.py` - Text-to-Speech
Converts text to audio.

**Interface:**
```python
class TTS(ABC):
    """Base class for TTS providers"""
    
    async def synthesize(
        text: str,
        voice: Voice | None = None
    ) -> AudioFrame:
        """Synthesize speech from text"""
```

#### `vad.py` - Voice Activity Detection
Detects when users are speaking.

**Interface:**
```python
class VAD(ABC):
    """Base class for VAD providers"""
    
    async def detect(
        audio_frame: rtc.AudioFrame
    ) -> bool:
        """Return True if speech detected"""
```

---

### 4. **Tool & Function System**

#### `llm/tool_context.py`
Manages callable tools available to agents.

**Key Decorator:**
```python
@function_tool
async def lookup_weather(
    context: RunContext,
    location: str
):
    """Used to look up weather information"""
    return {"weather": "sunny", "temperature": 70}
```

**Key Classes:**
- `FunctionTool`: Wrapper for a callable function
- `RawFunctionTool`: Low-level tool interface
- `ToolContext`: Manages available tools
- `ToolError`: Exception for tool execution errors

---

### 5. **Chat & LLM Context**

#### `llm/chat_context.py`
Maintains conversation history and structure.

**Key Classes:**

```python
class ChatContext:
    """Maintains conversation state"""
    
    messages: list[ChatMessage]
    user: ChatRole  # USER, ASSISTANT, SYSTEM
    tools: list[FunctionTool]
    
    async def add_message(role: ChatRole, content: str)
    async def add_function_call(name: str, arguments: dict)
    async def add_function_output(output: str)
```

**Data Classes:**
- `ChatMessage`: Individual message with role and content
- `ChatRole`: ENUM (USER, ASSISTANT, SYSTEM)
- `ChatItem`: Base conversation item
- `FunctionCall`: Tool invocation record
- `FunctionCallOutput`: Tool execution result

---

### 6. **I/O & Audio Management**

#### `voice/io.py`
Handles input/output streams for agents.

**Key Classes:**
- `AgentInput`: Receives audio and user input
- `AgentOutput`: Sends audio and responses
- `AudioFrame`: Audio data container

#### `voice/room_io.py`
Integrates with LiveKit room for audio routing.

**Responsibilities:**
- Audio capture from room participants
- Audio output to room
- Participant management
- Stream handling

---

## Project Structure

```
agents-assignment/
│
├── livekit-agents/                    # Core framework
│   └── livekit/agents/
│       ├── __init__.py                # Public API exports
│       ├── worker.py                  # Job/worker management
│       ├── job.py                     # Job context and execution
│       ├── plugin.py                  # Plugin system base
│       ├── cli/                       # Command-line interface
│       │   └── cli.py                 # CLI command handlers
│       │
│       ├── voice/                     # Voice interaction subsystem
│       │   ├── agent.py               # Agent class definition
│       │   ├── agent_session.py       # Session management
│       │   ├── agent_activity.py      # Activity tracking
│       │   ├── io.py                  # Input/Output handling
│       │   ├── room_io.py             # Room audio integration
│       │   ├── events.py              # Event types
│       │   ├── run_result.py          # Execution results
│       │   └── audio_recognition.py   # Audio processing
│       │
│       ├── llm/                       # Language model interfaces
│       │   ├── chat_context.py        # Conversation context
│       │   ├── tool_context.py        # Tool management
│       │   ├── llm.py                 # LLM base classes
│       │   └── mcp/                   # Model Context Protocol
│       │
│       ├── stt.py                     # Speech-to-Text interface
│       ├── tts.py                     # Text-to-Speech interface
│       ├── vad.py                     # Voice Activity Detection
│       │
│       ├── inference/                 # Model inference execution
│       │   ├── __init__.py            # Model loaders
│       │   └── inference_runner.py    # Inference executor
│       │
│       ├── tokenize/                  # Text tokenization
│       ├── ipc/                       # Inter-process communication
│       ├── metrics/                   # Performance metrics
│       ├── telemetry/                 # Observability & tracing
│       ├── utils/                     # Utility functions
│       │   ├── http_server.py
│       │   ├── event_emitter.py
│       │   └── ...
│       │
│       └── log.py                     # Logging configuration
│
├── livekit-plugins/                   # Plugin implementations (40+)
│   ├── livekit-plugins-openai/        # OpenAI integration
│   │   └── livekit/plugins/openai/
│   │       ├── __init__.py            # Public API
│       │       ├── llm.py             # LLM implementation
│       │       ├── stt.py             # STT implementation
│       │       ├── tts.py             # TTS implementation
│       │       └── realtime.py        # Realtime API
│   │
│   ├── livekit-plugins-deepgram/      # Deepgram STT
│   ├── livekit-plugins-elevenlabs/    # ElevenLabs TTS
│   ├── livekit-plugins-anthropic/     # Claude LLM
│   ├── livekit-plugins-google/        # Google Cloud APIs
│   ├── livekit-plugins-azure/         # Azure APIs
│   ├── livekit-plugins-silero/        # Silero VAD
│   ├── livekit-plugins-turn-detector/ # ML-based turn detection
│   ├── livekit-plugins-langchain/     # LangChain integration
│   └── ... (30+ more plugins)
│
├── examples/                          # Example implementations
│   ├── minimal_worker.py              # Simplest working example
│   │
│   ├── voice_agents/                  # Voice agent examples
│   │   ├── basic_agent.py             # Simple conversational agent
│   │   ├── weather_agent.py           # Agent with tools
│   │   ├── multi_agent.py             # Multi-agent handoff
│   │   ├── realtime_video_agent.py    # Video + voice
│   │   ├── push_to_talk.py            # PTT agent
│   │   └── ... (20+ more examples)
│   │
│   ├── avatar_agents/                 # Avatar integration examples
│   ├── bank-ivr/                      # IVR system example
│   ├── drive-thru/                    # Drive-through ordering
│   ├── frontdesk/                     # Front desk agent
│   └── ...
│
├── tests/                             # Test suite
│   ├── conftest.py                    # pytest configuration
│   ├── test_agent_session.py          # Agent session tests
│   ├── test_aio.py                    # Async tests
│   └── ... (various test files)
│
├── pyproject.toml                     # Root workspace configuration
├── README.md                          # Project documentation
└── CODE_OF_CONDUCT.md                 # Community guidelines
```

---

## Workflow

### 1. **Initialization & Startup**

```
┌─────────────────────────────────────────────────┐
│ 1. Define Agent (with instructions, tools)      │
│    agent = Agent(                               │
│        instructions="You are a helpful...",    │
│        tools=[lookup_weather],                  │
│        stt=Deepgram STT(),                     │
│        llm=OpenAI LLM(),                       │
│        tts=ElevenLabs TTS()                    │
│    )                                           │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│ 2. Create AgentServer & Register Entrypoint     │
│    server = AgentServer()                       │
│    @server.rtc_session()                        │
│    async def entrypoint(ctx: JobContext):       │
│        await ctx.connect()                      │
│        session = AgentSession(...)              │
│        await session.start(agent, ctx.room)    │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│ 3. Start Worker                                 │
│    cli.run_app(WorkerOptions(...))              │
│                                                 │
│    Worker listens on port for job requests     │
└─────────────────────────────────────────────────┘
```

### 2. **Job Request & Session Establishment**

```
┌──────────────────────────────┐
│ LiveKit Server               │
│ (Room with participants)     │
└──────────────────────────────┘
            │
            │ (dispatch job request)
            ▼
┌──────────────────────────────┐
│ Worker Process               │
│ Receives JobRequest          │
└──────────────────────────────┘
            │
            │ (create JobContext)
            ▼
┌──────────────────────────────┐
│ Entrypoint Function          │
│ async def entrypoint(ctx)    │
│   - ctx.connect()            │
│   - session.start(agent)     │
└──────────────────────────────┘
            │
            │ (connect to room)
            ▼
┌──────────────────────────────┐
│ Room Connection Established  │
│ Agent ready to interact      │
└──────────────────────────────┘
```

### 3. **User Interaction Loop**

```
┌─────────────────────────────────────────────┐
│ User speaks in room                         │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ VAD: Detect speech activity                 │
│ (Voice Activity Detector)                   │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ STT: Convert audio to text                  │
│ (Speech-to-Text)                            │
│ Input: audio_frame                          │
│ Output: "What's the weather?"               │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ Agent receives transcript                   │
│ - Add to ChatContext                        │
│ - Check for tool calls needed               │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ LLM: Generate response                      │
│ Input: ChatContext + user message           │
│ Output: Response + optional tool calls      │
│ "I'll look up the weather for you"         │
│ Tool: lookup_weather(location="NYC")        │
└─────────────────────────────────────────────┘
            │
            ├─ Tool Call? ──────────────┐
            │                           │
            No                          Yes
            │                           │
            │                           ▼
            │                   ┌──────────────────────┐
            │                   │ Execute Tool         │
            │                   │ lookup_weather(...)  │
            │                   │ Result: {weather...} │
            │                   └──────────────────────┘
            │                           │
            │                           ▼
            │                   ┌──────────────────────┐
            │                   │ Add result to context│
            │                   │ Re-call LLM          │
            │                   └──────────────────────┘
            │                           │
            └───────────────┬───────────┘
                            │
                            ▼
┌─────────────────────────────────────────────┐
│ TTS: Convert response to audio              │
│ (Text-to-Speech)                            │
│ Input: "The weather in NYC is sunny"       │
│ Output: audio_frame                         │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ Send audio to room                          │
│ User hears agent response                   │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│ User continues conversation                 │
│ Or session ends                             │
└─────────────────────────────────────────────┘
```

### 4. **Tool Execution Flow**

```
┌──────────────────────────────────┐
│ LLM decides to call a tool:      │
│ lookup_weather(location="NYC")   │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ ToolContext validates:           │
│ - Tool exists                    │
│ - Arguments match signature      │
│ - Type checking                  │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Execute Function                 │
│ @function_tool decorated func    │
│ @function_tool                   │
│ async def lookup_weather(...):   │
│     # custom implementation      │
│     return {"weather": "sunny"} │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Capture Result                   │
│ {"weather": "sunny",             │
│  "temperature": 70}              │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Add to ChatContext as:           │
│ FunctionCallOutput(result=...)   │
│                                  │
│ Now LLM has tool result          │
└──────────────────────────────────┘
```

### 5. **Multi-Agent Handoff**

```
┌──────────────────────────────────┐
│ User: "Connect me to support"    │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Current Agent (e.g., Intro Agent)│
│ Recognizes handoff need          │
│ Calls @function_tool:            │
│ async def transfer_to_support()  │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ AgentHandoff triggered           │
│ - Save chat context              │
│ - Notify of incoming specialist  │
│ - Close current agent            │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ New Agent (Support Agent) starts │
│ - Receives context               │
│ - Greets user                    │
│ - Continues conversation         │
└──────────────────────────────────┘
```

---

## Module Descriptions

### **worker.py** (1273 lines)
**Purpose**: Core worker process that manages agent lifecycle

**Key Classes**:
- `AgentServer`: Main server accepting WebRTC jobs
- `WorkerOptions`: Configuration dataclass
- `_DefaultLoadCalc`: CPU load monitoring

**Key Methods**:
- `connect()`: Register worker with LiveKit dispatcher
- `on_shutdown()`: Graceful shutdown handling
- `_process_job()`: Job request handler

**Key Responsibilities**:
- Accept and distribute job requests
- Manage process/thread pools
- Monitor health and performance
- Emit status updates to server
- Handle graceful shutdown

---

### **job.py** (815 lines)
**Purpose**: Manages individual job execution context

**Key Classes**:
- `JobContext`: Container for job environment
- `JobRequest`: Incoming job specification
- `JobProcess`: Process/thread wrapper
- `AutoSubscribe`: Subscription mode ENUM
- `JobExecutorType`: PROCESS vs THREAD mode

**Key Methods**:
- `connect()`: Connect to room
- `accept()`: Accept job request
- `reject()`: Reject job request
- `on_shutdown()`: Register shutdown handler
- `request_participant_entrypoint()`: Handle participant events

**Key Responsibilities**:
- Provide isolated execution context
- Handle WebRTC room connection
- Manage participant lifecycle
- Provide API for job configuration
- Track job state and metrics

---

### **voice/agent.py** (836 lines)
**Purpose**: Defines agent behavior and capabilities

**Key Classes**:
- `Agent`: Base agent class
- `AgentTask`: Task-specific agent (generic over result type)
- `ModelSettings`: Configuration for model behavior

**Key Properties**:
- `instructions`: System prompt
- `tools`: Available tools/functions
- `stt/llm/tts/vad`: Model instances
- `id`: Unique identifier

**Key Methods**:
- `on_enter()`: Session start hook
- `on_exit()`: Session end hook
- `on_message()`: Custom message handler
- `on_tool_call()`: Tool invocation handler

**Key Responsibilities**:
- Define agent personality and skills
- Manage tool availability
- Provide session lifecycle hooks
- Integrate with models

---

### **voice/agent_session.py** (1299 lines)
**Purpose**: Manages real-time agent-user interaction

**Key Classes**:
- `AgentSession`: Main session manager
- `AgentSessionOptions`: Configuration
- `SessionConnectOptions`: Connection settings

**Key Methods**:
- `start()`: Begin agent session
- `generate_reply()`: Create and send response
- `accept_input()`: Handle user input
- `on()`: Register event handler
- `close()`: End session

**Key Events**:
- `agent_state_changed`: Agent state changed
- `user_state_changed`: User state changed
- `user_input_transcribed`: User speech transcribed
- `conversation_item_added`: New conversation item
- `close`: Session ended

**Key Responsibilities**:
- Orchestrate voice pipeline
- Manage conversation flow
- Handle interruptions and turn-taking
- Track agent and user state
- Emit session events

---

### **llm/chat_context.py**
**Purpose**: Maintain and manage conversation history

**Key Classes**:
- `ChatContext`: Conversation state container
- `ChatMessage`: Individual message
- `ChatItem`: Base conversation element
- `FunctionCall`: Tool invocation record
- `FunctionCallOutput`: Tool result

**Key Data**:
- `messages`: List of messages
- `tools`: Available tools
- `user_metadata`: Custom user data

**Key Methods**:
- `add_message()`: Add message to history
- `add_function_call()`: Record tool invocation
- `add_function_output()`: Record tool result
- `copy()`: Create context copy

**Key Responsibilities**:
- Maintain conversation state
- Track tool calls and results
- Provide context to LLM
- Enable context serialization

---

### **llm/tool_context.py**
**Purpose**: Manage callable tools and functions

**Key Decorator**:
```python
@function_tool
async def my_function(context: RunContext, arg1: str):
    """Function description"""
    return result
```

**Key Classes**:
- `FunctionTool`: Callable function wrapper
- `RawFunctionTool`: Low-level tool
- `ToolContext`: Tool registry
- `ToolError`: Tool execution error

**Key Methods**:
- `find_function_tools()`: Extract tools from class
- `is_function_tool()`: Check if tool
- `call_tool()`: Execute tool

**Key Responsibilities**:
- Wrap Python functions as LLM tools
- Validate tool arguments
- Execute tools with error handling
- Provide tool introspection

---

### **plugin.py**
**Purpose**: Plugin system foundation

**Key Class**:
- `Plugin`: Base plugin class

**Key Features**:
- Plugin registration
- Version tracking
- Lazy file downloads
- Event emission

**Key Methods**:
- `register_plugin()`: Register plugin
- `download_files()`: Download resources

**Key Responsibilities**:
- Define plugin interface
- Manage plugin lifecycle
- Track plugin metadata

---

### **cli/cli.py**
**Purpose**: Command-line interface for workers

**Key Classes**:
- `AgentsConsole`: Console UI
- `CLIInterface`: CLI handler

**Key Features**:
- `console` mode: Interactive debugging
- `distributed` mode: Server deployment
- `live` mode: Real-time monitoring

**Key Methods**:
- `run_app()`: Start worker
- `parse_args()`: Parse CLI arguments

**Key Responsibilities**:
- Parse command-line arguments
- Manage execution modes
- Provide debugging interface
- Handle worker startup

---

## Plugin System

The plugin system allows extending the framework with new STT, LLM, TTS providers and other integrations.

### Plugin Architecture:

```
┌────────────────────────────┐
│ Plugin Base Class          │
│ (plugin.py)                │
├────────────────────────────┤
│ - Plugin registration      │
│ - Version tracking         │
│ - Metadata                 │
└────────────────────────────┘
            ▲
            │ (inherits)
            │
┌─────────────────────────────────────────┐
│ Provider Plugins (40+)                  │
├─────────────────────────────────────────┤
│                                         │
│ LLM Providers:                          │
│ • OpenAI (including Realtime API)       │
│ • Anthropic                             │
│ • Google Gemini                         │
│ • Azure OpenAI                          │
│ • Groq                                  │
│ • Mistral                               │
│ • ... and more                          │
│                                         │
│ STT Providers:                          │
│ • Deepgram                              │
│ • Assembly AI                           │
│ • Azure Speech                          │
│ • Google Cloud Speech                   │
│ • ... and more                          │
│                                         │
│ TTS Providers:                          │
│ • ElevenLabs                            │
│ • Azure Text-to-Speech                  │
│ • Google Cloud Text-to-Speech           │
│ • Cartesia                              │
│ • ... and more                          │
│                                         │
│ Specialized:                            │
│ • Turn Detector (ML-based)              │
│ • Voice Detection (Silero VAD)          │
│ • LangChain Integration                 │
│ • Avatar Services (Anam, Simli, etc.)  │
│                                         │
└─────────────────────────────────────────┘
```

### Using a Plugin:

```python
from livekit.plugins import openai, deepgram, elevenlabs

# Plugins auto-register when imported
agent = Agent(
    instructions="You are a helpful assistant",
    stt=deepgram.STT(model="nova-3"),
    llm=openai.LLM(model="gpt-4o"),
    tts=elevenlabs.TTS(voice="Aria")
)
```

---

## Data Flow

### Audio Processing Flow:

```
┌─────────────────────────┐
│ Participant Audio       │
│ (WebRTC Stream)         │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ room_io.py              │
│ Capture from room       │
│ Buffer audio frames     │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ VAD (Voice Activity Det)│
│ Filter silence          │
│ Detect speech start/end │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ STT (Speech-to-Text)    │
│ Convert audio → text    │
│ Stream recognition      │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ ChatContext             │
│ Add to message history  │
│ Track tokens            │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ LLM (Language Model)    │
│ Generate response       │
│ Stream tokens           │
└─────────────────────────┘
            │
            ├─ Regular Text ─────┐
            │                    │
            └─ Tool Call?        │
                       │
                       No        Yes
                       │         │
                       │         ▼
                       │      ┌─────────────┐
                       │      │Execute Tool │
                       │      │Get result   │
                       │      │Loop to LLM  │
                       │      └─────────────┘
                       │         │
                       └────┬────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ TTS (Text-to-Speech)│
                 │ Convert text→audio  │
                 │ Stream audio frames │
                 └─────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ room_io.py          │
                 │ Send to room        │
                 │ Play for participant│
                 └─────────────────────┘
```

### Control Flow:

```
User Input Flow:
┌──────────────────────┐
│ User speaks          │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Agent receives input │
│ (VAD/STT triggered)  │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Emit events:         │
│ • InputStarted       │
│ • Transcribed        │
│ • InputEnded         │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Agent.on_message()   │
│ (optional hook)      │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Generate reply:      │
│ - Call LLM           │
│ - Execute tools      │
│ - Synthesize speech  │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Output to room       │
│ Update state         │
│ Emit events          │
└──────────────────────┘
```

---

## Example: Complete Agent Lifecycle

```python
# 1. DEFINE AGENT
from livekit.agents import (
    Agent, AgentSession, JobContext, 
    function_tool, cli
)
from livekit.plugins import openai, deepgram, elevenlabs

@function_tool
async def lookup_weather(context, location: str):
    """Get weather for a location"""
    return {"weather": "sunny", "temperature": 70}

agent = Agent(
    instructions="You are a helpful weather assistant",
    tools=[lookup_weather],
    stt=deepgram.STT(model="nova-3"),
    llm=openai.LLM(model="gpt-4o"),
    tts=elevenlabs.TTS()
)

# 2. CREATE ENTRYPOINT
async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=elevenlabs.TTS()
    )
    
    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(
        instructions="Greet the user"
    )

# 3. RUN WORKER
if __name__ == "__main__":
    from livekit.agents import WorkerOptions
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

# 4. EXECUTION:
# - Worker starts and listens for jobs
# - LiveKit dispatches job when user joins
# - entrypoint() called with JobContext
# - Agent connects to room
# - Agent processes voice interactions
# - Session emits events
# - Agent responds with speech
# - When done, session closes
```

---

## Summary

The LiveKit Agents framework is a comprehensive system for building real-time AI agents:

1. **Worker** coordinates agent instances and job distribution
2. **Agent** defines behavior, instructions, and available tools
3. **AgentSession** manages real-time interaction with users
4. **Voice Pipeline** (VAD → STT → LLM → TTS) processes voice
5. **Plugins** extend capabilities with 40+ provider integrations
6. **Tools** enable agents to call functions and interact with external systems
7. **ChatContext** maintains conversation state and history
8. **Events** enable reactive programming and session monitoring

The system is designed for:
- Real-time, low-latency voice interactions
- Flexible model composition
- Scalable deployment
- Easy extension via plugins
- Production-ready reliability

