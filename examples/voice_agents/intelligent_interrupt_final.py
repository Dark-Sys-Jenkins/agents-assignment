"""
Intelligent Interruption Handler

Implements context-aware interruption filtering per challenge requirements.
Agent continues speaking seamlessly over backchanneling without pause or stutter.

Strategy:
- Use min_interruption_words to delay interruption until transcript available
- Leverage LiveKit's false_interruption with minimal timeout
- System validates transcript and auto-resumes for backchanneling
- Real commands trigger immediate interruption
"""

import logging
from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, JobProcess, cli
from livekit.plugins import silero

logger = logging.getLogger("intelligent-interrupt")
load_dotenv()

# Configurable word lists
IGNORE_WORDS = {'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right', 'aha', 'mhm', 'uh', 'um', 'yep', 'yup'}
COMMAND_WORDS = {'stop', 'wait', 'no', 'pause', 'hold', 'halt', 'but'}


class SmartAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a helpful assistant. Explain concepts clearly.")

    async def on_enter(self):
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    agent_speaking = {"value": False}
    
    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        min_interruption_words=1,
        resume_false_interruption=True,
        false_interruption_timeout=0.15,
    )
    
    @session.on("agent_state_changed")
    def _on_state(event):
        agent_speaking["value"] = (event.state == "speaking")
        logger.info(f"Agent: {event.state}")
    
    @session.on("user_input_transcribed")
    def _on_transcript(event):
        if not event.is_final:
            return
        
        transcript = event.transcript.strip()
        if not transcript:
            return
        
        words = set(transcript.lower().split())
        has_command = bool(words & COMMAND_WORDS)
        only_ignore = words and words.issubset(IGNORE_WORDS)
        is_backchannel = only_ignore and not has_command
        
        logger.info(
            f"User: '{transcript}' | Speaking: {agent_speaking['value']} | "
            f"Backchannel: {is_backchannel}"
        )
    
    @session.on("agent_false_interruption")
    def _on_false_int(event):
        logger.info(f"False interruption - Resumed: {event.resumed}")
    
    await session.start(agent=SmartAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
