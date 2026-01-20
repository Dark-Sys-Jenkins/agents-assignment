from typing import Literal

# listing production models from https://console.groq.com/docs/models

STTModels = Literal[
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "distil-whisper-large-v3-en",
]

LLMModels = Literal[
    "llama3-8b-8192",
    "llama3-70b-8192",
    "llama-guard-3-8b",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "deepseek-r1-distill-llama-70b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "moonshotai/kimi-k2-instruct",
    "qwen/qwen3-32b",
]

TTSModels = Literal[
    "canopylabs/orpheus-v1-english",
    "canopylabs/orpheus-arabic-saudi",
]

TTSVoices = Literal[
    # English voices (for canopylabs/orpheus-v1-english)
    "autumn",  # female
    "diana",   # female
    "hannah",  # female
    "austin",  # male
    "daniel",  # male
    "troy",    # male
    # Arabic-Saudi voices (for canopylabs/orpheus-arabic-saudi)
    "fahad",   # male
    "sultan",  # male
    "lulwa",   # female
    "noura",   # female
]
