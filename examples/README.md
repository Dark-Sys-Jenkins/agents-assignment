# 🚀 LiveKit Agents Examples

Welcome! This directory is your gateway to exploring the power of AI-driven voice agents built on the LiveKit Agents framework. Whether you're building conversational customer service, interactive voice applications, or avatar-driven experiences, you'll find comprehensive examples to get you started.

## 📁 Example Categories

### 🎙️ [Voice Agents](./voice_agents/)

Dive into the world of voice-based interactions! This collection showcases everything from simple voice conversations to sophisticated AI agents that can:
- **Respond naturally** to user voice input with intelligent conversation
- **Execute tools and functions** dynamically during conversations
- **Integrate with real-time models** like OpenAI, Google Gemini, and more
- **Handle complex workflows** with multi-agent systems and RAG (Retrieval-Augmented Generation)
- **Manage interruptions gracefully** with intelligent interruption detection
- **Support multimodal inputs** including video and avatar expressions

### 🖼️ [Avatar Agents](./avatar_agents/)

Bring your agents to life with visual avatars! These examples demonstrate how to combine voice agents with animated avatars from various providers including:
- Anam, Bey, BitHuman, Hedra, Simli, Tavus, and more
- Create engaging, face-to-face interactions with your AI
- Perfect for customer service, entertainment, and education applications

### 🔄 [Warm Transfer](./warm-transfer/)

Master the art of seamless handoffs! Learn how to implement professional call center workflows where:
- Supervisors can be intelligently routed calls when needed
- Agents can brief supervisors about the customer context before transfer
- Customers experience smooth, professional escalations

### 🚗 [Drive-Thru](./drive-thru/)

A complete ordering system example showcasing real-world application. This demonstrates:
- Interactive voice ordering flows
- Database integration for menu and order management
- Order confirmation and payment processing through voice

### 🏢 [Front Desk](./frontdesk/)

Build smart reception agents! This example shows how to create agents that:
- Manage appointments and calendars
- Handle customer inquiries with personality
- Integrate with scheduling systems

### 🔧 [Primitives](./primitives/)

Get back to basics! These fundamental examples cover:
- Establishing LiveKit room connections
- Managing participants in real-time
- Handling basic audio and video streams
- Perfect starting point for understanding core concepts

### 🛠️ [Other](./other/)

A treasure trove of specialized implementations including:
- Text-only agent interactions
- Various TTS (Text-to-Speech) provider integrations
- Transcription services
- Translation capabilities

## 🚀 Running Examples

### Prerequisites

Before you begin, make sure you have:

- A **[LiveKit Cloud](https://cloud.livekit.io)** account (easiest option) or a local **[LiveKit server](https://github.com/livekit/livekit)** instance
- **API keys** for the AI models and services you want to use (OpenAI, Groq, Deepgram, etc.)
- **Python 3.9 or higher** installed on your machine
- **[uv](https://docs.astral.sh/uv/)** - a fast Python package manager (optional but recommended)

### Setting Up Your Environment

Create a `.env` file in the `examples` directory with your API credentials:

```bash
# LiveKit Connection
LIVEKIT_URL="wss://your-project.livekit.cloud"
LIVEKIT_API_KEY="your_api_key"
LIVEKIT_API_SECRET="your_api_secret"

# AI Model Providers (choose based on what you want to use)
OPENAI_API_KEY="sk-xxx"              # For OpenAI models
GROQ_API_KEY="gsk-xxx"               # For Groq (fast inference)
DEEPGRAM_API_KEY="xxx"               # For speech recognition and TTS
ELEVENLABS_API_KEY="xxx"             # For natural-sounding speech synthesis

# Add other provider keys as needed for your examples
```

### Installing Dependencies

From the repository root, install all dependencies:

```bash
uv sync --all-extras --dev
```

This command will:
- Install the LiveKit agents framework
- Add all plugin dependencies (STT, TTS, LLM providers)
- Set up development tools

### Running Your First Example

Get started with a simple voice agent:

```bash
uv run examples/voice_agents/basic_agent.py console
```

Your agent is now live in console mode! You can speak to it and watch it respond.

### Using with a Frontend

For a better user experience with a visual interface, use:

- **[Agents Playground](https://agents-playground.livekit.io)** - Official playground to test your agents
- **[Starter Apps](https://docs.livekit.io/agents/start/frontend/#starter-apps)** - Production-ready frontend templates

## 💡 Quick Tips

- **Test locally first** - Use the `console` mode to quickly test your agent logic
- **Check the logs** - Agent logs will show you exactly what's happening under the hood
- **Start simple** - Begin with `basic_agent.py` before moving to complex examples
- **Explore tools** - Function calling and tool integration are powerful features - check out the tool examples!

## 📖 Additional Resources

- **[LiveKit Documentation](https://docs.livekit.io/)** - Complete platform documentation
- **[LiveKit Agents Documentation](https://docs.livekit.io/agents/)** - Detailed agent framework guide
- **[Starter Template](https://github.com/livekit-examples/agent-starter-python)** - Quick-start template for new projects
- **[More Examples](https://github.com/livekit-examples/python-agents-examples)** - Extended examples collection

Happy building! 🎉