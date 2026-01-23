import os

# Interruption Handling Configuration
# These are the words that the agent will IGNORE if said while it is speaking.
# If these words are said when the agent is silent, they will be processed normally.
INTERRUPTION_IGNORE_LIST = os.getenv(
    "INTERRUPTION_IGNORE_LIST", 
    "yeah,ok,hmm,right,uh-huh,got it"
).split(",")

# OpenRouter Configuration (OpenAI-Compatible)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

# Identity and Instructions
AGENT_INSTRUCTIONS = (
    "You are a helpful testing assistant designed to demonstrate intelligent interruption handling. "
    "1. When the user says 'Read history', call the 'read_history' tool. "
    "2. If the user gives passive feedback like 'yeah' or 'ok' while you are speaking, ignore it and continue. "
    "3. If the user says 'Stop' or 'Wait', stop speaking immediately using the 'stop_speech' tool. "
    "4. If the user says 'Yeah' when you are NOT speaking, treat it as a valid answer or confirmation."
)
