# examples/voice_agents/fakes.py
from __future__ import annotations

import asyncio
import copy
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from livekit.agents.llm import (
    LLM,
    ChatChunk,
    ChatContext,
    ChoiceDelta,
    FunctionTool,
    FunctionToolCall,
    LLMStream,
    RawFunctionTool,
    ToolChoice,
)
from livekit.agents.stt import (
    STT,
    RecognizeStream,
    SpeechData,
    SpeechEvent,
    SpeechEventType,
    STTCapabilities,
)
from livekit.agents.vad import VAD, VADCapabilities, VADEvent, VADEventType, VADStream
from livekit.agents.tts import (
    TTS,
    ChunkedStream,
    SynthesizeStream,
    TTSCapabilities,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.agents.utils.audio import AudioBuffer
from livekit.agents import utils

# Fake LLM 

class FakeLLMResponse(BaseModel):
    type: Literal["llm"] = "llm"
    input: str
    content: str
    ttft: float = 0.1
    duration: float = 0.5
    tool_calls: list[FunctionToolCall] = Field(default_factory=list)

class FakeLLM(LLM):
    def __init__(self, *, fake_responses: list[FakeLLMResponse] | None = None) -> None:
        super().__init__()
        self._fake_response_map = (
            {resp.input: resp for resp in fake_responses} if fake_responses else {}
        )

    @property
    def fake_response_map(self) -> dict[str, FakeLLMResponse]:
        return self._fake_response_map

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> LLMStream:
        return FakeLLMStream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)

class FakeLLMStream(LLMStream):
    def __init__(self, llm: FakeLLM, *, chat_ctx: ChatContext, tools: list[FunctionTool | RawFunctionTool], conn_options: APIConnectOptions) -> None:
        super().__init__(llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._llm = llm

    async def _run(self) -> None:
        index_text = self._get_index_text()
        # Default response if input not found
        resp = self._llm.fake_response_map.get(index_text)
        if not resp:
            # Fallback for ANY input if no specific match
            resp = FakeLLMResponse(input=index_text, content=f"Echo: {index_text}")
        
        await asyncio.sleep(resp.ttft)
        chunk_size = 5
        for i in range(0, len(resp.content), chunk_size):
            delta = resp.content[i : i + chunk_size]
            self._send_chunk(delta=delta)
            await asyncio.sleep(0.05)

        self._send_chunk(tool_calls=resp.tool_calls)

    def _send_chunk(self, *, delta: str | None = None, tool_calls: list[FunctionToolCall] | None = None) -> None:
        self._event_ch.send_nowait(
            ChatChunk(
                id=str(id(self)),
                delta=ChoiceDelta(role="assistant", content=delta, tool_calls=tool_calls or []),
            )
        )

    def _get_index_text(self) -> str:
        items = self.chat_ctx.items
        if items and items[-1].role == "user":
            return items[-1].text_content
        return ""

# Fake STT 

class FakeUserSpeech(BaseModel):
    type: Literal["user_speech"] = "user_speech"
    start_time: float
    end_time: float
    transcript: str
    stt_delay: float = 0.1

class FakeSTT(STT):
    def __init__(self, *, fake_exception: Exception | None = None, fake_transcript: str | None = None, fake_user_speeches: list[FakeUserSpeech] | None = None) -> None:
        super().__init__(capabilities=STTCapabilities(streaming=True, interim_results=False))
        self._fake_exception = fake_exception
        self._fake_transcript = fake_transcript
        self._fake_user_speeches = fake_user_speeches
        self._recognize_ch = utils.aio.Chan()
        self._stream_ch = utils.aio.Chan()

    # FIXED: Method name should be 'recognize' not '_recognize_impl'
    async def _recognize_impl(
        self, 
        buffer: AudioBuffer, 
        *, 
        language: str | None = None, 
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> SpeechEvent:
        if self._fake_exception:
            raise self._fake_exception
        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT, 
            alternatives=[SpeechData(text=self._fake_transcript or "Fake transcript", language=language or "")]
        )

    def stream(self, *, language: str | None = None, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS) -> RecognizeStream:
        stream = FakeRecognizeStream(stt=self, conn_options=conn_options)
        return stream

class FakeRecognizeStream(RecognizeStream):
    def __init__(self, *, stt: FakeSTT, conn_options: APIConnectOptions):
        super().__init__(stt=stt, conn_options=conn_options)
        self._stt = stt

    async def _run(self) -> None:
        # Simple simulation: if we receive audio, we emit a transcript after a delay
        # In a real "fake" scenario for manual testing, this might be tricky without pre-canned audio timing.
        # But for dev/console mode, we might just assume input triggers transcript.
        # For this implementation, we will rely on mapped fake speeches if provided.
        if self._stt._fake_user_speeches:
            start_time = time.time()
            for speech in self._stt._fake_user_speeches:
                # Wait until speech start
                now = time.time()
                wait_start = speech.start_time - (now - start_time)
                if wait_start > 0: 
                    await asyncio.sleep(wait_start)
                
                # Wait until end
                wait_end = (speech.end_time - speech.start_time)
                if wait_end > 0: 
                    await asyncio.sleep(wait_end)
                
                # Emit final
                self._event_ch.send_nowait(
                    SpeechEvent(
                        type=SpeechEventType.FINAL_TRANSCRIPT, 
                        alternatives=[SpeechData(text=speech.transcript, language="")]
                    )
                )
        
        async for _ in self._input_ch: 
            pass

# Fake TTS 

class FakeTTS(TTS):
    def __init__(self) -> None:
        super().__init__(capabilities=TTSCapabilities(streaming=True), sample_rate=24000, num_channels=1)

    def stream(self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS) -> SynthesizeStream:
        return FakeSynthesizeStream(tts=self, conn_options=conn_options)

    # Optional: Only implement if needed by your version of LiveKit
    def synthesize(self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS) -> ChunkedStream:
        stream = FakeChunkedStream(tts=self, input_text=text, conn_options=conn_options)
        return stream

class FakeChunkedStream(ChunkedStream):
    def __init__(self, tts: FakeTTS, input_text: str, conn_options: APIConnectOptions):
        super().__init__(tts=tts, conn_options=conn_options)
        self._input_text = input_text
    
    async def _run(self, output_emitter):
        # Simulate synthesis
        output_emitter.initialize(request_id="fake", sample_rate=24000, num_channels=1, mime_type="audio/pcm")
        
        # Fake audio generation
        duration = len(self._input_text) * 0.05
        num_samples = int(24000 * duration)
        output_emitter.push(b"\x00\x00" * num_samples)
        output_emitter.flush()

class FakeSynthesizeStream(SynthesizeStream):
    async def _run(self, output_emitter):
        output_emitter.initialize(request_id="fake", sample_rate=24000, num_channels=1, mime_type="audio/pcm")
        async for data in self._input_ch:
            if isinstance(data, str):
                # Fake audio generation: emit silence roughly corresponding to text length
                # 1 char ~ 0.05s
                duration = len(data) * 0.05
                # Generate fake PCM (silence)
                num_samples = int(24000 * duration)
                output_emitter.start_segment(segment_id=utils.shortuuid())
                output_emitter.push(b"\x00\x00" * num_samples)
                output_emitter.flush()

# Fake VAD 
class FakeVAD(VAD):
    def __init__(self) -> None:
        super().__init__(capabilities=VADCapabilities(update_interval=0.1))

    def stream(self) -> VADStream:
        return FakeVADStream(self)

class FakeVADStream(VADStream):
    async def _main_task(self) -> None:
        # Passive VAD, doesn't really do anything without input audio analysis
        async for _ in self._input_ch: 
            pass