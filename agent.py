import logging
from typing import Set
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,)
from livekit.agents import Agent, AgentSession
from livekit.plugins import deepgram, silero, groq

load_dotenv()
logger = logging.getLogger("sales-agent")

IGNORE_WORDS: Set[str] = {
    "yeah", "ok", "okay", "hmm", "right", "uh-huh", "aha", 
    "cool", "yep", "sure", "got it", "i see", "nice", "hello"
}

def is_backchannel(text: str) -> bool:
    """
    Returns True if the input consists ONLY of ignore words.
    Example: "Yeah okay" -> True.
    Example: "Yeah wait" -> False (Contains 'wait').
    """
    if not text: return False
    clean = text.lower().strip().replace(".", "").replace(",", "").replace("!", "").replace("?", "")
    words = clean.split()

    return all(word in IGNORE_WORDS for word in words)


class SalesAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._is_speaking = False

    async def on_agent_started_speaking(self):
        """Callback: Agent has started playing audio."""
        self._is_speaking = True
    
    async def on_agent_stopped_speaking(self):
        """Callback: Agent has finished playing audio."""
        self._is_speaking = False

    async def on_user_started_speaking(self):
        """
        CRITICAL OVERRIDE:
        Standard behavior is to interrupt audio immediately when VAD fires.
        We override this to 'pass' so the agent KEEPS TALKING until we see the transcript.
        This solves the "Hiccup" problem.
        """
        pass

    async def on_user_transcript(self, msg: llm.ChatMessage):
        """
        Logic Layer: Decide whether to Interrupt or Ignore based on Context.
        """
        user_text = msg.content
        is_ignorable = is_backchannel(user_text)
        
        if self._is_speaking and is_ignorable:
            logger.info(f"🟢 IGNORED (Backchannel): '{user_text}' - Audio continues.")
            return 
      
        if self._is_speaking and not is_ignorable:
            logger.info(f"🔴 INTERRUPT (Semantic): '{user_text}' - Stopping audio.")
           
        if not self._is_speaking and is_ignorable:
            logger.info(f"🔵 RESPOND (Passive Affirmation): '{user_text}'")

      
        await super().on_user_transcript(msg)


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

   
    SALES_PITCH = """
    You are a high-energy sales rep for SalesCode.ai.
    
    YOUR GOAL:
    - Pitch the product enthusiastically.
    - SalesCode is an AI copilot for sales teams that integrates with Salesforce.
    - Speak clearly and continuously.
    - If the user says "Yeah" or "Okay" while you speak, DO NOT STOP.
    - If the user asks a question or says "Stop", answer immediately.
    """

    agent_worker = SalesAgent(instructions=SALES_PITCH)

   
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=groq.LLM(model="llama-3.3-70b-versatile"), 
        tts=deepgram.TTS(),
    )

    await session.start(agent=agent_worker, room=ctx.room)
    await session.generate_reply(instructions="Introduce yourself as calling from SalesCode.ai and start the pitch immediately.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
