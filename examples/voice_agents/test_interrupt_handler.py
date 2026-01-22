"""
Test agent specifically designed for testing intelligent interruption handling.

This agent tells a long story to make it easy to test interruptions.
"""

import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("test-interrupt-handler")

load_dotenv()


class TestAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You are a storyteller. "
                "When the user asks you to tell a story, tell a long, detailed story "
                "about a brave explorer discovering a hidden treasure. "
                "Make the story at least 2-3 minutes long with many details. "
                "Speak slowly and clearly so the user can test interruptions. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "Keep your responses natural and conversational."
            )
        )

    async def on_enter(self):
        # Greet and ask if user wants to hear a story
        self.session.generate_reply(
            instructions="Greet the user and ask if they would like to hear a story. "
            "Wait for their response."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    session = AgentSession(
        stt="deepgram/nova-3",  # Or use your preferred STT
        llm="openai/gpt-4o-mini",  # Or use your preferred LLM
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",  # Or use your preferred TTS
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )

    await session.start(
        agent=TestAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
