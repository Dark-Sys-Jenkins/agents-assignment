import logging
import asyncio
import re
import os
import typing

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    metrics,
    room_io,
    llm,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.voice.agent_activity import AgentActivity

load_dotenv()

logger = logging.getLogger("context-aware-agent")

env_ignore = os.environ.get("IGNORE_WORDS")
if env_ignore:
    IGNORE_WORDS = set(word.strip().lower() for word in env_ignore.split(","))
else:
    IGNORE_WORDS = {
        "yeah", "ok", "hmm", "right", "uh-huh", "yep", "sure", "mhm", "aha",
        "okay", "ok yeah", "yeah ok", "yes", "uhhuh"
    }

_original_interrupt_by_audio_activity = AgentActivity._interrupt_by_audio_activity

def _should_ignore(text: str) -> bool:
    if not text:
        return True
    
    normalized = text.lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    if normalized in IGNORE_WORDS:
        return True
        
    words = normalized.split()
    all_ignored = all(word in IGNORE_WORDS for word in words)
    
    return all_ignored

def _patched_interrupt_by_audio_activity(self: AgentActivity) -> None:
    transcript = ""
    if self._audio_recognition:
        transcript = self._audio_recognition.current_transcript
    
    should_block_interruption = False
    
    if self._current_speech and not self._current_speech.done():
         if not transcript:
             should_block_interruption = True
             logger.info("Blocking interruption: No transcript available (Waiting for context)")
         elif _should_ignore(transcript):
             should_block_interruption = True
             logger.info(f"Blocking interruption: '{transcript}' is in ignore list")
         else:
             logger.info(f"Allowing interruption: '{transcript}' is NOT ignored")
             
    if should_block_interruption:
        return

    logger.info(f"Processing interruption (Original Logic). Transcript: '{transcript}'")
    return _original_interrupt_by_audio_activity(self)

AgentActivity._interrupt_by_audio_activity = _patched_interrupt_by_audio_activity

_original_on_end_of_turn = AgentActivity.on_end_of_turn

def _patched_on_end_of_turn(self: AgentActivity, info: typing.Any) -> bool:
    transcript = info.new_transcript
    
    if self._current_speech and not self._current_speech.done():
        if transcript and _should_ignore(transcript):
             logger.info(f"Ignoring end of turn (Reply suppressed): '{transcript}'")
             return False
             
    return _original_on_end_of_turn(self, info)

AgentActivity.on_end_of_turn = _patched_on_end_of_turn

class ContextAwareAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful assistant. You are currently participating in a test for interruption recovery. "
                         "You should read long explanations or count to 20 to demonstrate that you are not interrupted by passive words. "
                         "If the user says 'stop' or asks a question, you should stop immediately.",
        )

    async def on_enter(self):
        self.session.generate_reply()

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

class DummyOptions:
    max_retry = 0
    timeout = 5.0

class CountingLLM(llm.LLM):
    def __init__(self):
        super().__init__()

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool | llm.RawFunctionTool] | None = None,
        conn_options: typing.Optional[typing.Any] = None,
        parallel_tool_calls: typing.Optional[bool] = None,
        tool_choice: typing.Any = None,
        extra_kwargs: dict[str, typing.Any] | None = None,
    ) -> "llm.LLMStream":
        return CountingStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options or DummyOptions()
        )

server.setup_fnc = prewarm

class CountingStream(llm.LLMStream):
    def __init__(self, llm: llm.LLM, chat_ctx: llm.ChatContext, tools: list, conn_options: typing.Any):
        super().__init__(
            llm=llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options
        )
        
    async def _run(self) -> None:
        sentences = [
            "My name is Ujjwal Thapa.",
            "I am twenty one years old.",
            "I an currently pursuing my graduation from Thapar University",
            "I am doing major in conversational ai"
        ]
        
        for sentence in sentences:
            chunk = llm.ChatChunk(
                id="dummy-id",
                delta=llm.ChoiceDelta(content=sentence + " ")
            )
            await self._event_ch.send(chunk)
            await asyncio.sleep(2.0)

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
    session = AgentSession(
        stt=deepgram.STT(), 
        llm=CountingLLM(),
        tts=deepgram.TTS(),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        min_interruption_duration=1000.0, 
        allow_interruptions=True,
    )

    async def log_usage():
        pass

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=ContextAwareAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
