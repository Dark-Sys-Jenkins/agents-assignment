# Voice Agents Examples

This directory contains a comprehensive collection of voice-based agent examples demonstrating various capabilities and integrations with the LiveKit Agents framework.

## 📋 Table of Contents

### 🚀 Getting Started

- [`basic_agent.py`](./basic_agent.py) - A fundamental voice agent with metrics collection

### 🛠️ Tool Integration & Function Calling

- [`annotated_tool_args.py`](./annotated_tool_args.py) - Using Python type annotations for tool arguments
- [`dynamic_tool_creation.py`](./dynamic_tool_creation.py) - Creating and registering tools dynamically at runtime
- [`raw_function_description.py`](./raw_function_description.py) - Using raw JSON schema definitions for tool descriptions
- [`silent_function_call.py`](./silent_function_call.py) - Executing function calls without verbal responses to user
- [`long_running_function.py`](./long_running_function.py) - Handling long running function calls with interruption support

### ⚡ Real-time Models

- [`weather_agent.py`](./weather_agent.py) - OpenAI Realtime API with function calls for weather information
- [`realtime_video_agent.py`](./realtime_video_agent.py) - Google Gemini with multimodal video and voice capabilities
- [`realtime_joke_teller.py`](./realtime_joke_teller.py) - Amazon Nova Sonic real-time model with function calls
- [`realtime_load_chat_history.py`](./realtime_load_chat_history.py) - Loading previous chat history into real-time models
- [`realtime_turn_detector.py`](./realtime_turn_detector.py) - Using LiveKit's turn detection with real-time models
- [`realtime_with_tts.py`](./realtime_with_tts.py) - Combining external TTS providers with real-time models

### 🎯 Pipeline Nodes & Hooks

- [`fast-preresponse.py`](./fast-preresponse.py) - Generating quick responses using the `on_user_turn_completed` node
- [`flush_llm_node.py`](./flush_llm_node.py) - Flushing partial LLM output to TTS in `llm_node`
- [`structured_output.py`](./structured_output.py) - Structured data and JSON outputs from agent responses
- [`speedup_output_audio.py`](./speedup_output_audio.py) - Dynamically adjusting agent audio playback speed
- [`timed_agent_transcript.py`](./timed_agent_transcript.py) - Reading timestamped transcripts from `transcription_node`
- [`inactive_user.py`](./inactive_user.py) - Handling inactive users with the `user_state_changed` event hook
- [`resume_interrupted_agent.py`](./resume_interrupted_agent.py) - Resuming agent speech after false interruption detection
- [`toggle_io.py`](./toggle_io.py) - Dynamically toggling audio input/output during conversations

### 🎙️ Voice Interruption Handling

- **Context-Aware Interrupt Handler** - Advanced interruption management with intelligent filtering
  - **3-Layer Defense System**:
    1. **VAD Gate**: Blocks single-word fillers at the audio level
    2. **Semantic Filter**: Distinguishes between backchannels ("yeah") and commands ("stop")
    3. **Grace Period**: Handles race conditions during state transitions
  - **Implementation**: `salescode_interrupt_handler/controllers.py`
  - **Verification**: Run `python examples/verification_check.py` to test the logic

### 🤖 Multi-agent & AgentTask Use Cases

- [`restaurant_agent.py`](./restaurant_agent.py) - Multi-agent system for restaurant ordering and reservation management
- [`multi_agent.py`](./multi_agent.py) - Collaborative storytelling with multiple specialized agents
- [`email_example.py`](./email_example.py) - Using AgentTask to collect and validate email addresses

### 🔗 MCP & External Integrations

- [`web_search.py`](./web_search.py) - Integrating web search capabilities into voice agents
- [`langgraph_agent.py`](./langgraph_agent.py) - LangGraph integration
- [`mcp/`](./mcp/) - Model Context Protocol (MCP) integration examples
  - [`mcp-agent.py`](./mcp/mcp-agent.py) - MCP agent integration
  - [`server.py`](./mcp/server.py) - MCP server example
- [`zapier_mcp_integration.py`](./zapier_mcp_integration.py) - Automating workflows with Zapier through MCP

### 💾 RAG & Knowledge Management

- [`llamaindex-rag/`](./llamaindex-rag/) - Complete RAG implementation with LlamaIndex
  - [`chat_engine.py`](./llamaindex-rag/chat_engine.py) - Chat engine integration
  - [`query_engine.py`](./llamaindex-rag/query_engine.py) - Query engine used in a function tool
  - [`retrieval.py`](./llamaindex-rag/retrieval.py) - Document retrieval

### 🎵 Specialized Use Cases

- [`background_audio.py`](./background_audio.py) - Playing background audio or ambient sounds during conversations
- [`push_to_talk.py`](./push_to_talk.py) - Push-to-talk interaction
- [`tts_text_pacing.py`](./tts_text_pacing.py) - Pacing control for TTS requests
- [`speaker_id_multi_speaker.py`](./speaker_id_multi_speaker.py) - Multi-speaker identification

### 📊 Tracing & Error Handling

- [`langfuse_trace.py`](./langfuse_trace.py) - LangFuse integration for conversation tracing
- [`error_callback.py`](./error_callback.py) - Error handling callback
- [`session_close_callback.py`](./session_close_callback.py) - Session lifecycle management

---

## 🚀 Project Setup Instructions

Welcome to the **Context-Aware Interrupt Handler** project! This guide will help you set up the environment and run the voice agent.

### 📋 Prerequisites

- Python 3.12 or higher
- A LiveKit Cloud account (or self-hosted server)
- API keys for:
  - LiveKit
  - Groq (LLM)
  - Deepgram (STT)
  - Cartesia (TTS)

### 🛠️ Step-by-Step Setup

#### 1. Clone and Navigate

```bash
git clone <repository-url>
cd salescode-assignment
```

#### 2. Create Virtual Environment

It is highly recommended to use a virtual environment to avoid dependency conflicts.

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

We use a specific version of OpenTelemetry to ensure compatibility with the LiveKit framework on Windows.

```bash
pip install -r examples/voice_agents/requirements.txt
pip install "opentelemetry-api==1.35.0" "opentelemetry-sdk==1.35.0" "opentelemetry-exporter-otlp==1.35.0" "opentelemetry-proto==1.35.0"
```

#### 4. Configure Environment Variables

Copy the example environment file and fill in your keys.

```bash
cp env.example .env
# Open .env and add your API keys
```

### 🚀 Running the Project

#### 1. Verification Tests

Run the standalone test suite to ensure the interruption logic is working correctly:

```bash
python examples/verify_interrupt_handler.py
```

#### 2. Start the Voice Agent

Launch the agent in development mode with hot-reloading:

```bash
cd examples/voice_agents
python basic_agent.py dev
```

### 🧪 Interruption Logic

The core logic resides in `salescode_interrupt_handler/controllers.py`. It uses a 3-layer defense system:

1. **VAD Gate**: Blocks single-word fillers at the audio level
2. **Semantic Filter**: Distinguishes between backchannels ("yeah") and commands ("stop")
3. **Grace Period**: Handles race conditions during state transitions

---

## 📖 Additional Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [Agents Starter Example](https://github.com/livekit-examples/agent-starter-python)
- [More Agents Examples](https://github.com/livekit-examples/python-agents-examples)