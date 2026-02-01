from livekit.plugins import deepgram, google, elevenlabs, silero, openai, groq, cartesia
import os 
from dotenv import load_dotenv # type: ignore
load_dotenv()   

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# llm = openai.LLM(base_url="https://openrouter.ai/api/v1", api_key=OPEN_ROUTER_API_KEY, model="tarcee-ai/trinity-large-preview:free")

# llm = google.LLM(model="gemini-2.5-flash", api_key=GEMINI_API_KEY)
llm = openai.LLM(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
stt=deepgram.STT(model="nova-3", api_key=DEEPGRAM_API_KEY)
# tts=elevenlabs.TTS(api_key=ELEVENLABS_API_KEY)
tts = cartesia.TTS(api_key=os.getenv("CASTERIA_API_KEY"))

ignore_words = {'yeah','ok','hmm','right','uh-huh','okay','correct','uh','aha','correct','k','yes','good','nice','great','excellent','awesome','fantastic','amazing'}
interrupt_words = {'stop','wait','no','cancel','hold'}