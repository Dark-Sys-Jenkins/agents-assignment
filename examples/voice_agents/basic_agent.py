import logging
import asyncio
import json
import os
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import config  # Ensure this file exists with IGNORE_WORDS inside

load_dotenv()
logger = logging.getLogger("basic-agent")

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You are curious, friendly, and have a sense of humor. "
            "Keep responses concise. Do not use emojis or markdown.",
        )

    async def on_enter(self):
        # Initial greeting
        await self.session.say("I am ready. Ask me anything!")

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # 1. Connect to Room & Wait for User
    await ctx.connect()
    participant = await ctx.wait_for_participant()

    # 2. Setup AgentSession (The "Speaker")
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-5-nano"),
        tts=deepgram.TTS(),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        
        # [CRITICAL] Disable built-in interruption.
        # This prevents the agent from stopping automatically on "Yeah".
        # We will handle stopping manually in the Parallel Listener below.
        allow_interruptions=False, 
    )

    usage_collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    
    # [START] PARALLEL LISTENER ("The Second Pair of Ears")
    
    
    async def _manual_listening_loop():
        """
        This runs in the background and keeps listening even when the Agent is speaking.
        """
        logger.info("Waiting for microphone track...")
        track = None
        
        # --- LOOP UNTIL WE FIND THE USER'S AUDIO ---
        while not track:
            # FIX: Use 'remote_participants' instead of 'participants'
            for p in ctx.room.remote_participants.values():
                for pub in p.track_publications.values():
                    if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                        track = pub.track
                        break
            if not track:
                await asyncio.sleep(1)
        # -------------------------------------------
        
        logger.info(f"Microphone track found! (Sid: {track.sid}) Starting parallel listener.")

        # B. Create a separate STT stream (Ears that never close)
        # Note: We must create a new instance for this parallel stream
        stt_client = deepgram.STT(model="nova-3") 
        stt_stream = stt_client.stream()
        
        # C. Create Audio Stream from User
        audio_stream = rtc.AudioStream(track)

        # D. Forward Audio to STT
        async def _forward_audio():
            async for event in audio_stream:
                stt_stream.push_frame(event.frame)
        
        asyncio.create_task(_forward_audio())

        # E. Process Transcription Results
        async for event in stt_stream:
            if not event.alternatives:
                continue
                
            text = event.alternatives[0].text.strip().lower()
            logger.debug(f"######{text}")
            if not text:
                continue
                
            # Only interrupt if agent is speaking
            if session.agent_state != "speaking":
                continue

            # F. The Logic Matrix
            words = text.split()
            remaining = [w for w in words if w not in config.IGNORE_WORDS]

            if remaining:
                logger.info(f"🛑 VALID INTERRUPTION: '{text}' -> Stopping Agent.")
                await session.interrupt(force=True)
            else:
                logger.info(f"🙈 IGNORED: '{text}' -> Agent keeps talking.")
    # Start the parallel listener in background
    asyncio.create_task(_manual_listening_loop())

    
    # [END] PARALLEL LISTENER
    
    ctx.add_shutdown_callback(lambda: logger.info("Agent shutting down"))

    # Start the Agent
    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

if __name__ == "__main__":
    cli.run_app(server)
