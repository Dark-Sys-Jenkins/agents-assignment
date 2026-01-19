"""
Example agent demonstrating intelligent interruption handling.

This example shows how to use the smart interruption handler to prevent
the agent from stopping when users provide backchanneling feedback.

Features:
- Agent ignores user backchanneling (yeah, ok, hmm, etc.) while speaking
- Agent responds to actual commands (stop, wait, etc.)
- Configurable word lists for different use cases
"""

from livekit.agents import (
    AgentSession, 
    AgentJobContext, 
    JobContext,
    llm,
    tokenize,
    tts,
    stt,
)
from livekit.agents.voice import VoiceAssistant
from livekit.plugins import silero, openai, deepgram, cartesia
from livekit.agents.voice.interruption_handler import BackchannelingConfig


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the agent.
    """
    # Create a custom backchanneling configuration
    # You can customize which words are treated as backchanneling vs commands
    backchanneling_config = BackchannelingConfig(
        # Words that should be ignored when agent is speaking
        backchanneling_words={
            "yeah", "yep", "yes", "ok", "okay", "hmm", "aha", 
            "right", "uh-huh", "sure", "mm-hmm", "gotcha",
            "uh", "um", "ah", "oh", "mhm",
        },
        # Words that should interrupt the agent
        command_words={
            "stop", "wait", "hold", "pause", "no", "nope",
            "wrong", "cancel", "skip", "repeat", "again",
        },
        enabled=True  # Enable the smart filtering
    )
    
    # Create the agent session with the custom configuration
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=openai.LLM(model="gpt-4o-mini"),
        stt=deepgram.STT(),
        tts=cartesia.TTS(),
        # Pass the custom backchanneling config
        backchanneling_config=backchanneling_config,
        # Standard agent session options
        allow_interruptions=True,
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
    )
    
    # Define the agent's instructions
    system_prompt = """You are a helpful, friendly AI assistant. You engage in natural conversation 
with the user. When the user provides feedback like 'yeah', 'okay', or 'hmm', you should recognize these 
as positive acknowledgments and continue speaking naturally without pausing.

If the user says something like 'stop', 'wait', or 'hold on', you should stop speaking and listen to their command.

Key behaviors:
1. Continue speaking naturally when users provide backchanneling feedback
2. Stop immediately when users issue commands to interrupt
3. Provide comprehensive, helpful responses
4. Speak at a natural pace

Example scenarios:
- User: "Yeah" (while you're speaking) → You: Continue speaking without pausing
- User: "Okay" (while you're speaking) → You: Continue speaking without pausing  
- User: "Stop" (while you're speaking) → You: Stop and listen for the next command
"""
    
    # Create the voice agent
    agent = VoiceAssistant(
        session=session,
        system_prompt=system_prompt,
    )
    
    # Connect to the room and start the agent
    await agent.start(room=ctx.room)


if __name__ == "__main__":
    from livekit.agents.runner import run_job_context
    run_job_context(entrypoint)
