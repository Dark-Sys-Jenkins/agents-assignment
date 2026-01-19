
import asyncio
import logging
import os
import signal
import ssl
import traceback
import aiohttp
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import (
    Agent,
    AgentSession,
    llm,
)
from livekit.plugins import silero
import sys
from unittest.mock import MagicMock
import logging
logging.basicConfig(level=logging.DEBUG)

# Mock missing dependencies for Google Plugin (STT/TTS not used)
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.speech_v2"] = MagicMock()
sys.modules["google.cloud.speech_v2.types"] = MagicMock()
sys.modules["google.cloud.texttospeech"] = MagicMock()
sys.modules["google.cloud.texttospeech_v1"] = MagicMock()
sys.modules["google.cloud.texttospeech_v1.types"] = MagicMock()

import livekit.plugins.google as google
import livekit.plugins.deepgram as deepgram

# --- SSL BYPASS FOR CORPORATE PROXY ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# ---------------------------------------

load_dotenv()

async def run_direct():
    print("Initializing...")
    # 1. Credentials
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    url = os.getenv("LIVEKIT_URL")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not all([api_key, api_secret, url]):
        print("Error: Missing LIVEKIT credentials in .env")
        return
    if not deepgram_key:
        print("Error: Missing DEEPGRAM_API_KEY in .env")
        return
    if not gemini_key:
        print("Error: Missing GEMINI_API_KEY in .env")
        return

    # 2. Setup Agent Token
    # Agent must be able to subscribe to tracks to hear user
    grant = VideoGrants(
        room_join=True, 
        room="test-room-2", 
        agent=True,          
        can_publish=True, 
        can_subscribe=True
    )
    token = (
        AccessToken(api_key, api_secret)
        .with_identity("agent-kelly-direct")
        .with_name("Kelly (Agent)")
        .with_grants(grant)
        .to_jwt()
    )

    # 3. Connect to Room
    room = rtc.Room()
    print(f"Connecting to {url} room: test-room-2...")
    
    @room.on("disconnected")
    def on_disconnected(reason):
        print(f"DEBUG: Room disconnected! Reason: {reason}")
    
    try:
        await room.connect(url, token)
        print("✅ Agent Connected to Room!")
    except Exception as e:
        print(f"Failed to connect to room: {e}")
        traceback.print_exc()
        return

    # 4. Initialize Components
    # Create SSL context with verification disabled for corporate proxy
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Create aiohttp session with SSL bypass
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    http_session = aiohttp.ClientSession(connector=connector)
    try:
        # VAD
        vad = silero.VAD.load()
        
        # Plugins
        print("Initializing Deepgram STT/TTS and Gemini LLM...")
        stt_plugin = deepgram.STT(http_session=http_session)
        tts_plugin = deepgram.TTS(http_session=http_session)
        llm_plugin = google.LLM(model="gemini-2.0-flash-001", api_key=gemini_key)
        
        # Agent Session
        # Switched to Deepgram for STT/TTS per requirements
        session = AgentSession(
            vad=vad,
            stt=stt_plugin, 
            llm=llm_plugin, 
            tts=tts_plugin,
            preemptive_generation=False,
            resume_false_interruption=False,
        )

        # 5. Define Agent
        agent = Agent(
            instructions="You are a helpful voice assistant named Kelly. You are concise and friendly.",
        )

        # 6. Start Session
        print("Starting Agent Session...")
        await session.start(
            agent=agent,
            room=room,
        )
        print("Agent Session started successfully.")

        # GUARANTEED STARTUP SPEECH
        print("Triggering initial LLM generation...")
        try:
            # Gemini requires non-empty contents. Inject a hidden user prompt to start the conversation.
            session.history.add_message(role="user", content="Please introduce yourself concisely.")
            session.generate_reply()  # Don't await - let it run async
            print("Initial LLM generation request sent.")
        except Exception as e:
            print(f"CRITICAL: Failed to generate startup reply: {e}")
            raise e
        
        print("Agent is running! Speak now.")
        
        # Keep alive - check room connection state
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)
            
        print("Room connection closed, exiting...")

    except Exception as e:
        print(f"Runtime Error: {e}")
        traceback.print_exc()
    finally:
        await http_session.close()
        await room.disconnect()

if __name__ == "__main__":
    # Enabling debug logging for livekit to see more details
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_direct())
    except KeyboardInterrupt:
        print("Stopping agent...")
