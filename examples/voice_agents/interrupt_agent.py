#!/usr/bin/env python3
import logging
import os
import string
import asyncio
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    stt,
)
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.agents.voice.speech_handle import SpeechHandle
import interruption_logic

load_dotenv()

# Silence SDK logs to make the demo "clean"
logging.basicConfig(level=logging.WARNING)
logging.getLogger("livekit").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("interrupt-agent")
logger.setLevel(logging.INFO)

# --- MONKEYPATCH START ---
# The default SDK behavior raises a RuntimeError if something (like an automatic text handler)
# tries to interrupt an uninterruptible speech handle. We want to suppress this error
# and simply IGNORE the interruption attempt so our custom logic can handle it.
_original_interrupt = SpeechHandle.interrupt


def _safe_interrupt(self, force: bool = False):
    if not force and not self.allow_interruptions:
        # print(">>> [SDK] Suppressing automatic interruption (allow_interruptions=False)")
        # Return a completed future so 'await' works naturally but does nothing active
        f = asyncio.Future()
        f.set_result(None)
        return f
    return _original_interrupt(self, force=force)

SpeechHandle.interrupt = _safe_interrupt
# --- MONKEYPATCH END ---


class InterruptAgent(Agent):
    """
    An agent that implements intelligent interruption handling.
    It does NOT generate LLM responses for this demo, focusing purely on 
    the interruption logic test using a predefined script.
    """
    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        user_text = new_message.content
        if isinstance(user_text, list):
             user_text = " ".join([str(c) for c in user_text])
        elif user_text is None:
             user_text = ""
        
        # 1. Backchannel Handling (Speaking State)
        # If the user performed a backchannel while the agent is STILL speaking, 
        # we should ignore it (don't generate a "Yes?" response).
        if interruption_logic.is_backchannel(user_text) and self.session.agent_state == "speaking":
            print(f">>> [LOGIC] 🟢 IGNORING backchannel '{user_text}' (Agent still speaking). No LLM response.")
            return

        # 2. Stop Command Handling (Any State)
        # "Scenario 3: No stop -> Agent STOPS immediately"
        # We must suppress the LLM response so it doesn't say "Okay" after stopping.
        clean_input = user_text.strip().lower().translate(str.maketrans('', '', string.punctuation))
        stop_words = ["stop", "wait", "hold on", "shut up", "pause"]
        if any(w in clean_input.split() for w in stop_words):
             print(f">>> [LOGIC] � Command '{user_text}' detected. Suppressing LLM text response (silence).")
             return

        # 3. Valid Input Handling (Silent State / Non-Stop Input)
        # "Scenario 2: The Passive Affirmation -> Agent processes 'Yeah' as an answer"
        # "Scenario 4: Valid mixed input -> Agent treats as valid."
        # We let the LLM handle this naturally.
        
        print(f"\n>>> [LOGIC] 🧠 Generating LLM response for: '{user_text}'")
        stream = self.session.llm.chat(chat_ctx=turn_ctx)
        
        async def text_stream():
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    yield chunk.delta.content

        await self.session.say(text_stream(), allow_interruptions=False)


async def process_interruption(session: AgentSession, msg):
    # msg is UserInputTranscribedEvent
    if hasattr(msg, 'transcript'):
        text = msg.transcript
    else:
        logger.warning(f"Could not extract text from event: {msg}")
        return

    print(f"\n>>> [TRANSCRIPT] User said: '{text}'")
    
    # Check if agent is currently speaking
    is_speaking = session.agent_state == "speaking" 
    print(f">>> [STATE] Agent Speaking: {is_speaking}")

    if is_speaking:
        if interruption_logic.is_backchannel(text):
            print(f">>> [LOGIC] 🟢 IGNORING backchannel '{text}'. Continuing speech...")
            # Do NOTHING. The agent continues speaking because allow_interruptions=False.
        else:
            print(f">>> [LOGIC] 🔴 VALID INTERRUPTION '{text}'. Stopping agent!")
            # FORCE the interruption via SDK
            await session.interrupt(force=True)
    else:
        # Agent is silent. 
        # For "Yeah" or "Continue", this falls through to `on_user_turn_completed` which triggers the LLM.
        print(f">>> [LOGIC] 🔵 Agent Silent. Received '{text}' as valid input. Passing to LLM.")


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(), # Restored LLM for dynamic responses
        tts=cartesia.TTS(),
    )
    
    # Critical: We must set this to False so that the agent "hears" us (runs STT) 
    # even when it is speaking (which we marked as uninterruptible).
    if session.options:
        session.options.discard_audio_if_uninterruptible = False
        logger.info("Configured session to KEEP audio even when uninterruptible.")
    else:
        logger.warning("Could not access session.options to set discard_audio_if_uninterruptible!")
    
    @session.on("speech_created")
    def on_speech_created(msg):
        if hasattr(msg, 'speech_handle'):
            # allow_interruptions=False is CRITICAL for our custom logic to work
            # (otherwise the system auto-interrupts without checking our ignore list)
            msg.speech_handle.allow_interruptions = False


    @session.on("user_input_transcribed")
    def on_user_input_transcribed(msg):
        # Wrapper to run async logic
        asyncio.create_task(process_interruption(session, msg))


    # Standard Agent Instructions
    agent = InterruptAgent(
        instructions="You are the 'Interrupt Agent', a demo created by Vikas Verma. "
                    "You are witty, concise, and professional. "
                    "Handle queries intelligently. "
                    "If the user says 'Yeah' or 'Go on' while you are silent, acknowledge it and continue the topic. "
                    "If asked to count, count immediately."
    )
    await session.start(agent=agent, room=ctx.room)
    
    script = (
        "Hello! This video is a demo of intelligent interruption handling. "
        "My voice is generated locally to save API credits, but the brain behind me is fully alive. "
        "Here is the cool part. Humans make tiny sounds like 'yeah', 'okay', 'hmm', and 'uh-huh' "
        "just to show they are listening. These are called backchannels. "
        "Most voice systems get confused and stop when they hear them. I do not. "
        "So go ahead, say 'yeah' or 'okay'. I will ignore you and keep talking. "
        "But if you say something meaningful like 'wait', 'stop', or ask a real question, "
        "I will immediately stop and listen. That is intelligent interruption handling. "
        "Now, I am going to keep talking. "
        "Say 'yeah' or 'okay' — I won't stop. "
        "But say 'wait' or 'stop', and I'll instantly respect you. "
        "Go ahead. Try to interrupt me... if you can."
    )
    
    await session.say(script, allow_interruptions=False)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
