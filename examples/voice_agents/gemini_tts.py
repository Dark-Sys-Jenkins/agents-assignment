"""
Custom Gemini TTS Plugin using gemini-2.5-flash-preview-tts
Location: examples/voice_agents/gemini_tts.py

This uses Gemini's built-in TTS capability instead of Google Cloud TTS.
"""

import asyncio
import base64
import logging
from typing import AsyncIterator
from dataclasses import dataclass

from livekit.agents import tts, utils
from livekit import rtc
import google.generativeai as genai
from google.generativeai import types

logger = logging.getLogger(__name__)


@dataclass
class TTSOptions:
    """Configuration for Gemini TTS"""
    model: str = "gemini-2.5-flash-preview-tts"
    voice: str = "Puck"  # Gemini voice options: Puck, Charon, Kore, Fenrir, Aoede
    api_key: str = None


class GeminiTTS(tts.TTS):
    """
    Custom TTS implementation using Gemini's audio generation.
    No need for separate Google Cloud TTS API!
    """

    def __init__(
            self,
            *,
            model: str = "gemini-2.5-flash-preview-tts",
            voice: str = "Puck",
            api_key: str = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,  # Gemini TTS is not streaming
            )
        )

        self._opts = TTSOptions(
            model=model,
            voice=voice,
            api_key=api_key,
        )

        # Configure Gemini
        if api_key:
            genai.configure(api_key=api_key)

        self._client = genai.GenerativeModel(model_name=model)

        logger.info(f"✅ Initialized Gemini TTS with model: {model}, voice: {voice}")

    def synthesize(self, text: str) -> "ChunkedStream":
        """Synthesize text to speech using Gemini"""
        return ChunkedStream(
            tts=self,
            input_text=text,
            opts=self._opts,
        )


class ChunkedStream(tts.ChunkedStream):
    """Stream for Gemini TTS synthesis"""

    def __init__(
            self,
            *,
            tts: GeminiTTS,
            input_text: str,
            opts: TTSOptions,
    ):
        super().__init__(tts=tts, input_text=input_text)
        self._opts = opts
        self._client = tts._client

    async def _run(self) -> None:
        """Generate audio using Gemini"""
        try:
            logger.debug(f"Generating audio for: {self._input_text[:50]}...")

            # Generate content with audio response
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.generate_content(
                    contents=self._input_text,
                    generation_config=types.GenerationConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self._opts.voice
                                )
                            )
                        )
                    ),
                )
            )

            # Extract audio data
            if not response.candidates:
                logger.error("No candidates in Gemini response")
                return

            candidate = response.candidates[0]
            if not candidate.content.parts:
                logger.error("No parts in candidate content")
                return

            # Get the audio data
            audio_part = candidate.content.parts[0]
            if not hasattr(audio_part, 'inline_data'):
                logger.error("No inline_data in audio part")
                return

            audio_data = audio_part.inline_data
            mime_type = audio_data.mime_type
            audio_bytes = audio_data.data

            logger.debug(f"Generated audio: {len(audio_bytes)} bytes, MIME: {mime_type}")

            # Convert to PCM audio frames for LiveKit
            # Gemini returns audio in various formats, we need to convert to PCM
            from io import BytesIO
            import wave

            # Create audio frame
            # Note: You may need to adjust sample rate and channels based on actual output
            audio_frame = rtc.AudioFrame(
                data=audio_bytes,
                sample_rate=24000,  # Gemini typically uses 24kHz
                num_channels=1,
                samples_per_channel=len(audio_bytes) // 2,  # 16-bit audio
            )

            # Push the audio frame
            self._event_ch.send_nowait(
                tts.SynthesizedAudio(
                    request_id=self.request_id,
                    frame=audio_frame,
                )
            )

            logger.debug(f"Successfully pushed audio frame")

        except Exception as e:
            logger.error(f"Error generating audio with Gemini: {e}", exc_info=True)
            raise