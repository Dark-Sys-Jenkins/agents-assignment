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
from livekit.agents.llm import function_tool
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import config  # Ensure this file exists with IGNORE_WORDS inside

load_dotenv()
logger = logging.getLogger("basic-agent")

class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()
        
    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def lookup_weather(
        self, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """

        logger.info(f"Looking up weather for {location}")

        return "sunny with a temperature of 70 degrees."
        
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
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=openai.LLM(model="gpt-5-nano"),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=deepgram.TTS(),
         # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
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
    
    # parallel listener
    async def _manual_listening_loop():
        """
        This runs in the background and keeps listening even when the Agent is speaking.
        """
        logger.info("Waiting for microphone track...")
        track = None
        
        # --- LOOP UNTIL WE FIND THE USER'S AUDIO ---
        while not track:
            for p in ctx.room.remote_participants.values():
                for pub in p.track_publications.values():
                    if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                        track = pub.track
                        break
            if not track:
                await asyncio.sleep(1)
        
        logger.info(f"Microphone track found! (Sid: {track.sid}) Starting parallel listener.")

        # Create a separate STT stream
        # create a new instance for this parallel stream
        stt_client = deepgram.STT(model="nova-3") 
        stt_stream = stt_client.stream()
        
        # Create Audio Stream from User
        audio_stream = rtc.AudioStream(track)

        # Forward Audio to STT
        async def _forward_audio():
            async for event in audio_stream:
                stt_stream.push_frame(event.frame)
        
        asyncio.create_task(_forward_audio())

        # Process Transcription Results
        async for event in stt_stream:
            if not event.alternatives:
                continue
                
            text = event.alternatives[0].text.strip().lower()
            logger.debug(f"Test that is said: {text}")
            if not text:
                continue
                
            # Only interrupt if agent is speaking
            if session.agent_state != "speaking":
                continue

            # The Logic Matrix
            words = text.split()
            remaining = [w for w in words if w not in config.IGNORE_WORDS]

            if remaining:
                logger.info(f"VALID INTERRUPTION: '{text}' -> Stopping Agent.")
                await session.interrupt(force=True)
            else:
                logger.info(f"IGNORED: '{text}' -> Agent keeps talking.")
    # Start the parallel listener in background
    asyncio.create_task(_manual_listening_loop())


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
