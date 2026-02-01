"""
Smart Interruption Handler for LiveKit Voice Agent

Problem: LiveKit's VAD stops the agent when user says "yeah" or "ok".
Solution: Logic layer that ignores filler words but stops on commands.


"""

import re
import asyncio
from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, groq, silero

load_dotenv()

# 1. CONFIGURATION

# Soft words (Backchanneling) -> IGNORE these
SOFT_WORDS = {
   "yeah", "yes", "yea", "ya", "yep", "yup", "yah", "yeh",
    "ok", "okay", "k", "kk", "alright", "right", "sure", "fine",
    "got it", "i see", "i understand", "understood",
    "hmm", "hm", "hmmmm", "aha", "ah", "uh", "um", "umm",
    "uh-huh", "uh huh", "mhm", "mhmm", "mm", "mmm", "mm-hmm",
    "go on", "continue", "and", "so", "then",
}

# Stop words (Commands) -> INTERRUPT immediately
STOP_WORDS = {
    "stop", "wait", "hold on",
    "pause", "no", "cancel", "quiet",
}


# 2. HELPER FUNCTIONS

def clean_text(text):
    """Normalize text: lowercase, remove punctuation & extra spaces."""
    return re.sub(r"\s+", " ", text.lower().strip())


def contains_stop_word(text):
    """Check if text contains any stop command."""
    for word in STOP_WORDS:
        # Use regex boundary \b to ensure "no" doesn't match "know"
        if re.search(rf"\b{re.escape(word)}\b", text):
            return True
    return False


def is_only_filler(text):
    """Check if the ENTIRE text is made of only filler words."""
    words = clean_text(text).split()
    if not words: return False
    # Check if every word in the sentence is in the SOFT_WORDS set
    return all(w.strip(".,!?") in SOFT_WORDS for w in words)


# 3. AGENT CLASS

class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful voice assistant. Keep responses to 2-3 sentences.",
            allow_interruptions=True,
        )


# 4. MAIN LOGIC

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # Configure the session with specific VAD settings
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=deepgram.TTS(model="aura-asteria-en"),
        
        # KEY SETTINGS FOR INTERRUPTION HANDLING
        allow_interruptions=True,
        min_interruption_words=3,        # Prevent auto-interrupt on short words
        min_interruption_duration=0.5,   # Prevent auto-interrupt on short sounds
        false_interruption_timeout=2.5,  # Wait longer to classify input
        resume_false_interruption=True,  # Resume if it was just a filler
    )

    @session.on("user_input_transcribed")
    def on_user_input(event):
        """
        Event handler: Decides whether to interrupt or ignore user speech.
        """
        # We only care about final transcripts
        if not getattr(event, "is_final", True):
            return

        text = clean_text(getattr(event, "transcript", ""))
        if not text:
            return

        print(f"User: '{text}'")

        # CASE 1: Stop Command -> Force Interrupt
        if contains_stop_word(text):
            print("Stop command detected - Interrupting!")
            # interrupt() is async, so we schedule it on the loop
            asyncio.ensure_future(session.interrupt())
            return

        # CASE 2: Only Filler Words -> Ignore (Let LiveKit auto-resume)
        if is_only_filler(text):
            print("Soft words only - Ignoring")
            return
        
        # CASE 3: Normal Conversation -> Handled automatically

    await session.start(room=ctx.room, agent=Assistant())
    await session.generate_reply(
        instructions="Greet the user and ask what topic they'd like to learn about."
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))