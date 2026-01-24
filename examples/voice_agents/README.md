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

### Intelligent Interruption Handling

Context-aware backchannel filtering that distinguishes between passive acknowledgements
("yeah", "ok", "hmm") and active interruptions ("stop", "wait", "no").

**Implementation:**

The solution is implemented in two files:

1. **Core Filter Module:** `livekit-agents/livekit/agents/voice/backchannel_filter.py`
   - `classify(text)` - O(1) classification as "ignore" or "interrupt"
   - `should_ignore(text, agent_speaking)` - Main API for filtering
   - `BackchannelConfig` - Configurable word lists via code or environment variables

2. **Agent Integration:** `livekit-agents/livekit/agents/voice/agent_activity.py`
   - `on_vad_inference_done()` - Skips interrupt when agent is speaking
   - `on_interim_transcript()` - Only interrupts for real content
   - `on_final_transcript()` - Filters backchannels and returns early

**Demo Agent:**
- [`backchannel_agent.py`](./backchannel_agent.py) - Full demonstration agent

**Testing:**
- [`test_backchannel.py`](./test_backchannel.py) - Unit tests for detection logic

#### Decision Logic

| User Input | Agent State | Behavior |
|------------|-------------|----------|
| "Yeah / Ok / Hmm" | Speaking | IGNORE - Continue speaking |
| "Stop / Wait / No" | Speaking | INTERRUPT - Stop and listen |
| "Yeah / Ok / Hmm" | Silent | RESPOND - Process as valid input |
| Mixed (e.g. "Yeah but wait") | Speaking | INTERRUPT - Contains interrupt word |

#### Architecture

```
VAD triggers while speaking -> SKIP (don't interrupt)
                                  |
                    Wait for STT transcript
                                  |
            +---------------------+---------------------+
            |                                           |
    "yeah/ok/hmm"                         "stop/wait/real content"
            |                                           |
    Return early                            Emit + interrupt
    (agent continues)                       (agent stops)
```

#### Quick Start

```bash
# Run unit tests
python test_backchannel.py

# Run demo agent (terminal mode)
python backchannel_agent.py console

# Run demo agent (connect to LiveKit)
python backchannel_agent.py dev
```

#### Configuration

Environment variables for customization:
- `BACKCHANNEL_IGNORE_WORDS` - Comma-separated ignore words
- `BACKCHANNEL_INTERRUPT_WORDS` - Comma-separated interrupt words
- `BACKCHANNEL_DEBUG` - Enable debug logging (true/false)

## Additional Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [Agents Starter Example](https://github.com/livekit-examples/agent-starter-python)
- [More Agents Examples](https://github.com/livekit-examples/python-agents-examples)
