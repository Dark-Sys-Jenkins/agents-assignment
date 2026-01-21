import logging
import asyncio
import string
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    stt,
    WorkerOptions,
)
from livekit.agents.llm import function_tool
# IMPORT NEW PLUGINS
from livekit.plugins import silero, deepgram, groq

logger = logging.getLogger("basic-agent")

load_dotenv()

# 1. Configurable Ignore List
IGNORE_WORDS = {'yeah', 'ok', 'hmm', 'uh-huh', 'right', 'aha', 'okay', 'yep', 'sure', 'alright', 'Alright' 'mm-hmm', 'gotcha', 'i see', 'understood', 'hello', 'Hello'}

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    # --- FREE STACK INITIALIZATION ---
    # 1. VAD: Silero (Local/Free)
    my_vad = silero.VAD.load()
    
    # 2. STT: Deepgram (Free Tier)
    # We use Nova-2 for fast, accurate speech recognition
    my_stt = deepgram.STT(model="nova-2-general")
    
    # 3. LLM: Groq (Free Tier)
    # We use Llama 3 8B which is insanely fast and free
    my_llm = groq.LLM(model="llama-3.3-70b-versatile")
    
    # 4. TTS: Deepgram (Free Tier)
    # Aura TTS is low latency and sounds natural
    my_tts = deepgram.TTS(model="aura-asteria-en")

    # Initialize custom agent
    agent = MyAgent(vad=my_vad, stt_instance=my_stt)
    
    # Create the Session
    session = AgentSession(
        vad=my_vad,
        stt=my_stt,
        llm=my_llm,
        tts=my_tts,
    )
    
    await session.start(room=ctx.room, agent=agent)
    await session.generate_reply()

class MyAgent(Agent):
    def __init__(self, vad, stt_instance) -> None:
        super().__init__(
            instructions="Your name is Kelly. You interact with users via voice. "
            "Keep your responses concise and to the point. "
            "Do not use emojis or special characters. "
            "You are curious, friendly, and have a sense of humor. "
            "Speak English to the user.",
        )
        self.my_vad = vad
        self.my_stt = stt_instance

    # --- Intelligent Interruption Logic Layer ---
    def stt_node(self, audio, model_settings):
        # Create stream using the Deepgram STT instance
        # Note: Deepgram STT stream handling is slightly different than OpenAI's in some versions,
        # but the adapter pattern standardizes it.
        stt_stream = stt.StreamAdapter(stt=self.my_stt, vad=self.my_vad)
        
        stream = stt_stream.stream()

        async def push_audio_loop():
            async for frame in audio:
                stream.push_frame(frame)
            stream.end_input()

        asyncio.create_task(push_audio_loop())
        
        return self._interruption_filter(stream)

    async def _interruption_filter(self, stream):
        buffered_start_event = None
        monitoring_turn = False
        drop_rest_of_turn = False

        async for event in stream:
            is_agent_speaking = self._is_agent_speaking()

            if event.type == stt.SpeechEventType.START_OF_SPEECH:
                if is_agent_speaking:
                    buffered_start_event = event
                    monitoring_turn = True
                    drop_rest_of_turn = False
                else:
                    yield event
            
            elif event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT or event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                if drop_rest_of_turn:
                    continue

                if not monitoring_turn:
                    yield event
                    continue

                text = event.alternatives[0].text if event.alternatives else ""
                if self._should_ignore(text):
                    if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                        logger.info(f"Ignoring passive acknowledgement: '{text}'")
                        buffered_start_event = None
                        monitoring_turn = False
                        drop_rest_of_turn = True 
                else:
                    if buffered_start_event:
                        yield buffered_start_event
                        buffered_start_event = None
                    
                    monitoring_turn = False
                    yield event

            elif event.type == stt.SpeechEventType.END_OF_SPEECH:
                if drop_rest_of_turn:
                    drop_rest_of_turn = False
                    continue
                
                if buffered_start_event:
                    yield buffered_start_event
                    buffered_start_event = None
                
                monitoring_turn = False
                yield event
            
            else:
                yield event

    # def _is_agent_speaking(self):
    #     if hasattr(self, '_activity') and self._activity:
    #         if self._activity._current_speech and not self._activity._current_speech.future.done():
    #             return True
    #         if self._activity._speech_q:
    #             return True
    #     return False


    def _is_agent_speaking(self):
        """
        Helper to check if the agent is actively speaking based on the current SpeechHandle.
        """
        if hasattr(self, '_activity') and self._activity:
            # Check if there is a current speech handle and if it is NOT marked as done
            if self._activity._current_speech and not self._activity._current_speech.done(): #
                return True
            # Also check if there are any speech turns waiting in the queue
            if self._activity._speech_q:
                return True
        return False


    def _should_ignore(self, text):
        clean_text = text.strip().lower().translate(str.maketrans('', '', string.punctuation))
        words = clean_text.split()
        if not words: return True

        for i, word in enumerate(words):
            is_last = (i == len(words) - 1)
            if is_last:
                if not any(ign.startswith(word) for ign in IGNORE_WORDS):
                    return False
            else:
                if word not in IGNORE_WORDS:
                    return False
        return True

    @function_tool
    async def lookup_weather(
        self, location: str, latitude: str, longitude: str
    ):
        return f"The weather in {location} is currently sunny."

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm, 
        )
    )
