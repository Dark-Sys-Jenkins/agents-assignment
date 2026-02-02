"""
Voice Test - Speak into microphone to test interruption handling

Usage: python voice_test.py console
"""

import logging
from dotenv import load_dotenv
load_dotenv()

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import deepgram, groq, silero

logger = logging.getLogger("voice-test")


class TestAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""You are a friendly and helpful assistant. 
            
            Adjust your response length based on the question:
            - For simple questions or greetings: Give short 1-2 sentence answers
            - For complex questions or when user asks for details/paragraphs: Give thorough, detailed responses
            
            IMPORTANT: Always respond to the user, even if they just say 'yeah', 'ok', 
            'okay', or 'yes'. Ask them what they'd like to know or how you can help.
            
            If the user says 'wait' or 'stop', acknowledge and ask how you can help."""
        )

    async def on_enter(self):
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    print("\n" + "=" * 50)
    print("VOICE INTERRUPTION TEST")
    print("=" * 50)
    print("\nSpeak into your microphone:")
    print("  'yeah', 'ok' while agent talks -> should CONTINUE")
    print("  'wait', 'stop' while agent talks -> should STOP")
    print("\nPress Ctrl+C to exit")
    print("=" * 50 + "\n")
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=deepgram.TTS(model="aura-asteria-en"),
        vad=ctx.proc.userdata["vad"],
    )
    
    await session.start(
        agent=TestAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    cli.run_app(server)
