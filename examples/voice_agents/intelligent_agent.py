import logging
import string
import asyncio
from typing import Optional, List

import librosa
import numpy as np
import pyttsx3

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    stt,
)
from livekit.plugins import silero, deepgram

# CONFIG

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intelligent-agent")

TARGET_SR = 24000
FRAME_SIZE = 480  # 20 ms @ 24 kHz

# these words will be ignored (more words can be added)
FILLER_WORDS = {
    "yeah", "ok", "okay", "uhhuh", "uh-huh",
    "hmm", "right", "aha", "yep", "yes", "alright", "oh", "ohh"
}

# these words will interrupt the agent (more words can be added)
HARD_WORDS = {
    "stop", "wait", "pause", "hold", "no"
}

# these words will resume the agent from the exact position where it was interrupted (more words can be added)
RESUME_WORDS = {
    "continue", "resume", "go"
}

# these words will restart the agent (more words can be added)
RESTART_WORDS = {
    "repeat", "restart", "again", "start again", "from beginning"
}

# these words will start the agent (more words can be added)
START_WORDS = {
    "start", "begin", "explain", "hello", "hi", "tell me", "talk about", "go ahead"
}

# CONTENT

LONG_PARAGRAPH = (
    "Today we are going to talk about the history of computing. "
    "Early computers were mechanical devices designed to perform simple calculations. "
    "Over time, these machines evolved into electronic systems capable of complex reasoning "
    "and automation. This evolution transformed science, engineering, and society, shaping "
    "how humans solve problems and communicate information."
    "Whose world is this?"
    "Today we are going to talk about the history of computing. "
    "Early computers were mechanical devices designed to perform simple calculations. "
    "Over time, these machines evolved into electronic systems capable of complex reasoning "
    "and automation. This evolution transformed science, engineering, and society, shaping "
    "how humans solve problems and communicate information."
)

# TTS (LOCAL, FREE)

def generate_wav(text: str, path="out.wav"):
    engine = pyttsx3.init()
    engine.save_to_file(text, path) # not required
    engine.runAndWait()

#CONVERTING WAV TO PCM FRAMES
def wav_to_pcm_frames(path: str) -> List[bytes]:
    audio, _ = librosa.load(path, sr=TARGET_SR, mono=True)
    audio = (audio * 32767).astype(np.int16)

    frames = []
    for i in range(0, len(audio), FRAME_SIZE):
        chunk = audio[i:i + FRAME_SIZE]
        if len(chunk) < FRAME_SIZE:
            break
        frames.append(chunk.tobytes())
    return frames

# AGENT
class IntelligentAgent:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.stt = deepgram.STT()

        # AUDIO OUTPUT

        self.audio_source = rtc.AudioSource(TARGET_SR, 1)
        self.audio_track = rtc.LocalAudioTrack.create_audio_track(
            "agent-voice", self.audio_source
        )

        # SPEECH STATE

        self.is_speaking = False
        self.is_paused = False
        self.speech_task: Optional[asyncio.Task] = None

        self.speech_frames: List[bytes] = []
        self.frame_idx = 0

        # HYBRID VAD + STT STATE 

        self.pending_interrupt = False
        self.interrupt_timer: Optional[asyncio.Task] = None


    async def start(self):
        logger.info("Agent started")

        await self.ctx.room.local_participant.publish_track(
            self.audio_track,
            rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE),
        )

        participant = await self.ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")

        track_pub = None
        while not track_pub:
            track_pub = next(
                (p for p in participant.track_publications.values()
                 if p.kind == rtc.TrackKind.KIND_AUDIO),
                None
            )
            await asyncio.sleep(0.1)

        track_pub.set_subscribed(True)
        while not track_pub.track:
            await asyncio.sleep(0.1)

        audio_stream = rtc.AudioStream(track_pub.track)
        stt_stream = self.stt.stream()

        async def pipe_audio():
            async for event in audio_stream:
                stt_stream.push_frame(event.frame)

        asyncio.create_task(pipe_audio())

        async for event in stt_stream:
            if not event.alternatives:
                continue

            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                await self.process_input(event.alternatives[0].text.strip())

    # LOGIC LAYER (PDF-COMPLIANT)
    async def process_input(self, text: str):
        cleaned = text.lower().translate(str.maketrans("", "", string.punctuation))
        words = cleaned.split()

        if not words:
            return

        passive_only = all(w in FILLER_WORDS for w in words)
        has_hard = any(w in HARD_WORDS for w in words)
        wants_resume = any(w in RESUME_WORDS for w in words)
        wants_restart = any(phrase in cleaned for phrase in RESTART_WORDS)
        wants_start = any(phrase in cleaned for phrase in START_WORDS)

        logger.info(f"[INPUT] '{text}'")

        # MY SPEAKING AGENT

        if self.is_speaking:
            if passive_only:
                # Pure filler → absolutely ignore
                return

            if wants_restart:
                # STRONG COMMAND: cancel + restart immediately
                logger.info("[RESTART] restarting from beginning")
                self._cancel_speech()
                await self.start_new_speech(LONG_PARAGRAPH)
                return

            if has_hard:
                # True interruption → pause only
                logger.info("[INTERRUPT] confirmed by STT")
                self._cancel_speech()
                self.is_paused = True
                return

            return

        if wants_restart:
            await self.start_new_speech(LONG_PARAGRAPH)
            return

        if self.is_paused and wants_resume:
            await self.resume_with_bridge()
            return

        if wants_start or passive_only:
            await self.start_new_speech(LONG_PARAGRAPH)
            return


    # SPEECH CONTROL
    def _cancel_speech(self):
        if self.speech_task:
            self.speech_task.cancel()

    async def start_new_speech(self, text: str):
        generate_wav(text)
        self.speech_frames = wav_to_pcm_frames("out.wav")
        self.frame_idx = 0
        self.is_paused = False
        self.speech_task = asyncio.create_task(self.play_pcm_frames())

        
        #additional bridge to make the interaction more human-like
    async def resume_with_bridge(self):
        bridge = "Alright. I hope you understood till now. Continuing."
        generate_wav(bridge)
        bridge_frames = wav_to_pcm_frames("out.wav")

        self.speech_frames = bridge_frames + self.speech_frames[self.frame_idx:]
        self.frame_idx = 0
        self.is_paused = False
        self.speech_task = asyncio.create_task(self.play_pcm_frames())

    async def play_pcm_frames(self):
        self.is_speaking = True
        logger.info("Agent STARTED speaking")

        try:
            while self.frame_idx < len(self.speech_frames):
                await self.audio_source.capture_frame(
                    rtc.AudioFrame(
                        data=self.speech_frames[self.frame_idx],
                        sample_rate=TARGET_SR,
                        num_channels=1,
                        samples_per_channel=FRAME_SIZE,
                    )
                )
                self.frame_idx += 1
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Agent PAUSED")
            raise

        finally:
            self.is_speaking = False
            if self.frame_idx >= len(self.speech_frames):
                self.is_paused = False
                self.frame_idx = 0
                self.speech_frames = []
            logger.info("Agent FINISHED speaking")


# THIS IS THE VAD PARTS
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    agent = IntelligentAgent(ctx)
    asyncio.create_task(agent.start())

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
