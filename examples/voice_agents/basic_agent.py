import logging
import os
import asyncio
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
)
try:
    from livekit.agents import StopResponse
except ImportError:
    from livekit.agents.llm import StopResponse

from livekit.agents.llm import function_tool, ChatContext, ChatMessage
from livekit.plugins import silero, groq, murf
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("kelly-agent")
load_dotenv()


IGNORE_WORDS = [
    "yeah", "ok", "okay", "kay", "k", "hmm", "hm", "aha", 
    "uh-huh", "uh huh", "yep", "yup", "right", "sure", "correct", 
    "i see", "got it", "nice", "cool", "interesting", "wait a sec",
    "yeah okay", "oh okay"
]
STOP_WORDS = ["stop", "wait", "hold on", "cancel", "shut up"]

semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
IGNORE_EMBEDDINGS = semantic_model.encode(IGNORE_WORDS)

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep responses concise. You are curious and friendly."
            ),
        )

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str, latitude: str, longitude: str):
        return "It is currently sunny and 70 degrees."

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server = AgentServer()
server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=groq.STT(),
        llm=groq.LLM(model="llama-3.3-70b-versatile"), 
        tts=murf.TTS(voice="en-US-matthew"),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        
        allow_interruptions=True, 
        

        min_interruption_duration=2.0, 
        
        preemptive_generation=True,
    )



    # --- THE BRAIN ---
    async def my_custom_turn_completed(session: AgentSession, turn_ctx: ChatContext, new_message: ChatMessage):
      
        text = new_message.text_content.lower().strip()
        clean_text = text.replace('.', '').replace(',', '').replace('!', '')
        

        is_direct_match = clean_text in IGNORE_WORDS
        
        user_embedding = semantic_model.encode([clean_text])
        similarities = cosine_similarity(user_embedding, IGNORE_EMBEDDINGS)
        is_semantic_match = np.max(similarities) > 0.60
        
        is_ignore_word = is_direct_match or is_semantic_match
        
        # 3. Decision Logic
        if session.agent_state == "speaking" or session.agent_state == "processing":
            if is_ignore_word:

                logger.info(f"SEAMLESS IGNORE: '{clean_text}'")
                raise StopResponse()
            else:

                logger.info(f"MANUAL INTERRUPT: '{clean_text}'")
                
                # A. Cancel the brain's thinking
                if session.response_task:
                    session.response_task.cancel()
                

                await session.say("Stopping.", allow_interruptions=True)

        else:
            
            logger.info(f"NORMAL RESPONSE: '{clean_text}'")
            pass

    session.on_user_turn_completed = my_custom_turn_completed

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    await session.start(agent=MyAgent(), room=ctx.room)
    # Intro protected from VAD
    await session.say("Hello! I am Kelly. I am ready to be tested.", allow_interruptions=False)

if __name__ == "__main__":
    cli.run_app(server)
