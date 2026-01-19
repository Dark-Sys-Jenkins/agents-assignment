import asyncio
import logging

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import openai, silero

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interrupt-handler-agent")
load_dotenv()

BACKCHANNEL_WORDS = {
    "yeah", "yea", "yep", "ya", "yes",
    "ok", "okay",
    "uh-huh", "uh huh", "uhuh",
    "hmm", "hm", "mm", "mhm",
    "right", "sure", "got it",
    "i see", "ah", "aha", "oh",
    "alright", "all right"
}

INTERRUPT_WORDS = {
    "stop", "wait", "pause", "cancel",
    "hold on", "actually", "but", "however", "ok,wait"
}

def normalize(text: str) -> str:
    return text.lower().strip()


def is_backchannel_only(text: str) -> bool:
    return normalize(text) in BACKCHANNEL_WORDS


def contains_interrupt(text: str) -> bool:
    t = normalize(text)
    return any(word in t for word in INTERRUPT_WORDS)

class GreetingAgent(Agent):
    async def on_enter(self):
        self.session.say("Hey, how can I help you?")

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    agent_is_speaking = False

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),

        # CRITICAL SETTINGS
        preemptive_generation=False,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
    )


    @session.on("agent_started_speaking")
    def _on_agent_start():
        nonlocal agent_is_speaking
        agent_is_speaking = True

    @session.on("agent_stopped_speaking")
    def _on_agent_stop():
        nonlocal agent_is_speaking
        agent_is_speaking = False
        
    @session.on("user_transcript")
    def _on_user_transcript(text: str):
        text = normalize(text)

        #Ignore backchannel words completely
        if is_backchannel_only(text):
            logger.debug("Ignoring backchannel: %s", text)
            return

        #If agent is speaking
        if agent_is_speaking:
            # Interrupt ONLY on explicit command
            if contains_interrupt(text):
                logger.info("Interrupting on command: %s", text)
                session.interrupt()
            return

        #Agent is silent → normal user input
        session.generate_reply(user_input=text)


    await session.start(
        agent=GreetingAgent(
            instructions=(
                "You are a real-time voice assistant speaking to a human. "
                "Listen carefully and do whatever the user asks you to do. "
                "Speak naturally and clearly in plain English. "
                "Ignore filler or backchannel words such as "
                "'yeah', 'ok', 'okay', 'hmm', or similar sounds. "
                "If the user says a filler word while you are talking, "
                "continue the same sentence naturally without stopping or restarting from where you left speaking(sometimes the text generated and the spoken word is not the same. Always start from the next word which you last spoke)"
                "Respond fully and helpfully to user requests. "
                "Do not use emojis, markdown, or special formatting."
            )
        ),
        room=ctx.room,
    )   
if __name__ == "__main__":
    cli.run_app(server)