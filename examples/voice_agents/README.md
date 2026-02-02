# 🎙️ Voice Agents Examples

Welcome to the Voice Agents showcase! This is your comprehensive guide to building intelligent, conversational AI agents that listen, think, and speak naturally. Each example is crafted to demonstrate specific capabilities, from simple conversations to complex multi-agent systems.

## 📋 Table of Contents

### 🚀 Getting Started

- **[`basic_agent.py`](./basic_agent.py)** - Your first step into voice agents
  - A foundational voice agent with metrics collection
  - Perfect for understanding the core architecture
  - See how simple voice conversations work

### 🛠️ Tool Integration & Function Calling

These examples show how to extend your agent with custom functions and tools:

- **[`annotated_tool_args.py`](./annotated_tool_args.py)** - Clean type-safe tools
  - Use Python type annotations for automatic tool descriptions
  - Let the framework handle argument validation

- **[`dynamic_tool_creation.py`](./dynamic_tool_creation.py)** - On-the-fly tools
  - Register tools dynamically at runtime
  - Perfect for conditional or data-driven tool registration

- **[`raw_function_description.py`](./raw_function_description.py)** - Advanced control
  - Use raw JSON schema definitions for precise tool descriptions
  - Maximum flexibility for complex tool configurations

- **[`silent_function_call.py`](./silent_function_call.py)** - Quiet execution
  - Execute function calls without speaking back to the user
  - Useful for background operations and data fetching

- **[`long_running_function.py`](./long_running_function.py)** - Patient assistants
  - Handle long-running operations gracefully
  - Support interruptions while processing tasks

### ⚡ Real-time Models

Experience the power of streaming AI models for ultra-low latency responses:

- **[`weather_agent.py`](./weather_agent.py)** - OpenAI Realtime API
  - Instant responses with OpenAI's streaming model
  - Integrated function calls for weather data

- **[`realtime_video_agent.py`](./realtime_video_agent.py)** - Multimodal magic
  - Google Gemini with video and voice capabilities
  - Describe what the agent "sees" in real-time

- **[`realtime_joke_teller.py`](./realtime_joke_teller.py)** - Amazon Nova Sonic
  - Real-time model with integrated function calling
  - Entertainment-grade agent responses

- **[`realtime_load_chat_history.py`](./realtime_load_chat_history.py)** - Memory management
  - Load previous conversations into real-time models
  - Maintain context across sessions

- **[`realtime_turn_detector.py`](./realtime_turn_detector.py)** - Intelligent listening
  - LiveKit's sophisticated turn detection in action
  - Know when the user has finished speaking without timeouts

- **[`realtime_with_tts.py`](./realtime_with_tts.py)** - Custom voices
  - Combine real-time models with external TTS providers
  - Use natural-sounding voices from your preferred provider

### 🎯 Pipeline Nodes & Hooks

Master the agent pipeline with these advanced examples:

- **[`fast-preresponse.py`](./fast-preresponse.py)** - Lightning-fast replies
  - Generate quick responses using the `on_user_turn_completed` node
  - Minimize perceived latency

- **[`flush_llm_node.py`](./flush_llm_node.py)** - Streaming responses
  - Flush partial LLM output to TTS immediately
  - Let users hear responses sooner

- **[`structured_output.py`](./structured_output.py)** - Structured data
  - Extract JSON and structured data from agent responses
  - Perfect for workflow integration

- **[`speedup_output_audio.py`](./speedup_output_audio.py)** - Dynamic pacing
  - Adjust agent speech speed on the fly
  - Make responses feel more natural or energetic

- **[`timed_agent_transcript.py`](./timed_agent_transcript.py)** - Timing matters
  - Access timestamped transcripts from the pipeline
  - Synchronize responses with timestamps

- **[`inactive_user.py`](./inactive_user.py)** - User awareness
  - Detect and handle inactive users gracefully
  - Use the `user_state_changed` event hook

- **[`resume_interrupted_agent.py`](./resume_interrupted_agent.py)** - Smart resumption
  - Resume agent speech after false interruption detection
  - Distinguish between real commands and filler words

- **[`toggle_io.py`](./toggle_io.py)** - Dynamic control
  - Turn audio input/output on and off during conversations
  - Implement features like "agent is thinking" silently

### 🤖 Multi-agent & AgentTask Use Cases

Orchestrate multiple agents working together:

- **[`restaurant_agent.py`](./restaurant_agent.py)** - Coordinated systems
  - Multi-agent system for restaurant ordering and reservations
  - See agents specializing in different tasks

- **[`multi_agent.py`](./multi_agent.py)** - Collaborative storytelling
  - Multiple specialized agents telling a story together
  - Perfect example of agent coordination

- **[`email_example.py`](./email_example.py)** - Multi-step workflows
  - Use AgentTask to collect and validate information (emails)
  - Build agents that guide users through processes

### 🔗 MCP & External Integrations

Extend your agents with powerful external services:

- **[`web_search.py`](./web_search.py)** - Real-world knowledge
  - Integrate web search capabilities into your agent
  - Let agents find current information

- **[`langgraph_agent.py`](./langgraph_agent.py)** - LangGraph workflows
  - Complex reasoning chains with LangGraph
  - Build agents with sophisticated decision trees

- **[`mcp/`](./mcp/) - Model Context Protocol
  - **[`mcp-agent.py`](./mcp/mcp-agent.py)** - MCP integration
  - **[`server.py`](./mcp/server.py)** - Build your own MCP server
  - Standardized protocol for agent capabilities

- **[`zapier_mcp_integration.py`](./zapier_mcp_integration.py)** - Workflow automation
  - Connect to thousands of apps via Zapier
  - Automate complex business workflows through voice

### 💾 RAG & Knowledge Management

Build knowledge-aware agents:

- **[`llamaindex-rag/`](./llamaindex-rag/) - Complete RAG system**
  - **[`chat_engine.py`](./llamaindex-rag/chat_engine.py)** - Conversational RAG
  - **[`query_engine.py`](./llamaindex-rag/query_engine.py)** - Function-based retrieval
  - **[`retrieval.py`](./llamaindex-rag/retrieval.py)** - Document indexing and search
  - Build agents that answer questions from your documents

### 🎵 Specialized Use Cases

Unique applications for voice agents:

- **[`background_audio.py`](./background_audio.py)** - Ambient sound
  - Play background music or ambient sounds
  - Create atmospheric voice conversations

- **[`intelligent_interrupt_agent.py`](./intelligent_interrupt_agent.py)** - Smart interruption
  - Distinguish between real commands and acknowledgements
  - Agent continues when user just says "yeah" or "ok"

- **[`push_to_talk.py`](./push_to_talk.py)** - Manual control
  - Traditional push-to-talk interaction model
  - User controls when agent listens

- **[`tts_text_pacing.py`](./tts_text_pacing.py)** - Pacing control
  - Control TTS request timing for natural speech
  - Manage speech rate and pauses

- **[`speaker_id_multi_speaker.py`](./speaker_id_multi_speaker.py)** - Multi-speaker
  - Identify different speakers in conversations
  - Perfect for multi-participant scenarios

### 📊 Tracing & Error Handling

Observability and reliability:

- **[`langfuse_trace.py`](./langfuse_trace.py)** - Full observability
  - LangFuse integration for conversation tracing
  - Debug and analyze agent behavior

- **[`error_callback.py`](./error_callback.py)** - Error resilience
  - Handle errors gracefully during conversations
  - Keep agents running smoothly

- **[`session_close_callback.py`](./session_close_callback.py)** - Lifecycle management
  - React to session start and end events
  - Clean up resources and save session data

## 🎯 Choosing Your Starting Point

**New to LiveKit agents?**
→ Start with [`basic_agent.py`](./basic_agent.py)

**Want to add tools/functions?**
→ Check out [`annotated_tool_args.py`](./annotated_tool_args.py)

**Need super-fast responses?**
→ Explore [`weather_agent.py`](./weather_agent.py) (realtime models)

**Building production systems?**
→ Look at error handling and tracing examples

**Want something unique?**
→ Browse the specialized use cases section

## 💡 Pro Tips

- **Combine examples** - Mix and match concepts from different examples
- **Read the code** - Each example is thoroughly commented
- **Check the logs** - Agent logs tell you exactly what's happening
- **Experiment boldly** - The framework is forgiving and flexible
- **Performance matters** - Use real-time models for responsive agents

## 📖 Additional Resources

- **[LiveKit Agents Documentation](https://docs.livekit.io/agents/)** - Complete reference guide
- **[Agents Starter Example](https://github.com/livekit-examples/agent-starter-python)** - Quick-start template
- **[More Examples](https://github.com/livekit-examples/python-agents-examples)** - Extended examples
- **[API Reference](https://docs.livekit.io/agents/api/)** - Detailed API documentation

Happy building! Create something amazing! 🚀
