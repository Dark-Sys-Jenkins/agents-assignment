import logging
import re
import os
import asyncio

from dotenv import load_dotenv

from livekit.agents import JobContext, cli, WorkerOptions, Agent
from livekit.agents.voice import AgentSession
from livekit.plugins import deepgram, openai, silero, cartesia


logger = logging.getLogger("interrupt-handler")
logger.setLevel(logging.INFO)
load_dotenv()


IGNORE_WORDS = {
    "yeah", "ok", "okay", "hmm", "uh", "uh-huh",
    "right", "mhm", "mm", "mm-hmm", "aha", "yep", "yup"
}

INTERRUPT_WORDS = {
    "stop", "wait", "no", "cancel", "hold", "but", "however"
}


# Helper functions


def normalize(text: str) -> list[str]:
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^a-z\s]", "", text)
    return [w for w in text.split() if w]

def contains_interrupt_command(transcript: str) -> bool:
    words = normalize(transcript)
    return any(w in INTERRUPT_WORDS for w in words)

def is_only_filler(transcript: str) -> bool:
    words = normalize(transcript)
    return bool(words) and all(w in IGNORE_WORDS for w in words)

# Main entrypoint


async def entrypoint(ctx: JobContext):


    # State tracking
    # -----------------------------
    agent_state = "listening"
    answer_cancelled = False   

    # Session setup

    session = AgentSession(
        vad=silero.VAD.load(),
        llm=openai.LLM(
            model="mistralai/mistral-7b-instruct",
            api_key=os.environ["OPENAI_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        ),
        stt=deepgram.STT(),
        tts=cartesia.TTS(),

 
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
        min_interruption_duration=0.3,
        min_interruption_words=1,
        allow_interruptions=True,
    )

    # Event handlers (logic layer, NOT VAD)


    def on_agent_state_changed(event):
        nonlocal agent_state
        agent_state = event.new_state
        logger.info(f"🤖 Agent state: {event.old_state} → {event.new_state}")

    def on_user_input_transcribed(event):
        nonlocal agent_state, answer_cancelled

        if not event.is_final:
            return

        transcript = event.transcript
        was_speaking = agent_state == "speaking"

        logger.info(f"📝 Transcript: '{transcript}' | Agent state: {agent_state}")

        has_interrupt = contains_interrupt_command(transcript)
        only_filler = is_only_filler(transcript)


        # Agent WAS speaking
 
        if was_speaking:

            if only_filler:
      
                logger.info("✋ IGNORE filler while speaking")
                session.clear_user_turn()
                return

            if has_interrupt:
                logger.info("🛑 SEMANTIC STOP detected → CANCELING SPEECH")

                answer_cancelled = True


                session.agent.interrupt()


                # Prevent resume
                session.clear_user_turn()

         
                asyncio.create_task(
                    session.generate_reply(
                        instructions=(
                            "Okay, I’ll stop there. "
                            "Is there something else I can help you with?"
                        )
                    )
                )

                return



            # Any other meaningful speech interrupts
            logger.info("💬 REAL INTERRUPTION")
            answer_cancelled = True
            return


        else:
            if answer_cancelled:
                # Prevent continuation of cancelled answer
                logger.info("⛔ Cancelled answer cleared")
                answer_cancelled = False
                return

    
            logger.info("✅ PROCESS input while silent")

    session.on("agent_state_changed", on_agent_state_changed)
    session.on("user_input_transcribed", on_user_input_transcribed)


    agent = Agent(
        instructions=(
            "You are a helpful AI assistant. "
            "When the user says just 'yeah', 'okay', or 'hmm' while you're silent, "
            "acknowledge briefly and continue naturally. "
            "When the user says 'stop' or 'wait', immediately stop the current explanation "
            "and ask how else you can help."
        )
    )

    logger.info("🚀 Starting agent session")
    await session.start(room=ctx.room, agent=agent)

    await asyncio.sleep(0.5)

    await session.generate_reply(
        instructions=(
            "Hello! I'm your AI assistant. "
            "You can ask me questions, or try interrupting me by saying things like "
            "'yeah' or 'stop' while I talk."
        )
    )



if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint)
    )
