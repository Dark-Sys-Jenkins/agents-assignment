import logging
import re

from dotenv import load_dotenv

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import cartesia, deepgram, openai, silero

logger = logging.getLogger("resume-agent")

load_dotenv()

# This example shows how to resume an agent from a false interruption.
# If `resume_false_interruption` is True, the agent will first pause the audio output
# while not interrupting the speech before the `false_interruption_timeout` expires.
# If there is not new user input after the pause, the agent will resume the output for the same speech.
# If there is new user input, the agent will interrupt the speech immediately.

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=openai.LLM(model="gpt-4o-mini"),
        stt=deepgram.STT(),
        tts=cartesia.TTS(),
        false_interruption_timeout=1.0,
        resume_false_interruption=True,
    )

    #This boolean tracks whether the agent is currently speaking based on AgentSession state events. We only use this for deciding whether to consider interrupting the agent. It is updated solely via the "agent_state_changed" hook, not via VAD or any audio primitives
    agent_speaking=False
    #We store the current SpeechHandle from the `speech_created` event so the agent can be interrupted when needed, without modifying VAD or internal audio behavior
    current_speech_handle=None
    #We normalize the transcript into lowercase word tokens so punctuation and casing do not affect keyword based interruption logic
    def normalize(text: str)->list[str]:
        return re.findall(r"[a-z']+", text.lower())

    #Now we update the speaking flag on agent state changes so interruption logic runs only while the agent is speaking
    def on_agent_state_changed(ev):
        nonlocal agent_speaking
        if ev.new_state=="speaking":
            agent_speaking=True
            logger.info("Agent has started speaking")
        elif ev.old_state=="speaking":
            agent_speaking=False
            logger.info("Agent has stopped speaking")

    #We store the current SpeechHandle so interruptions target the active playback and clears it once the speech finishes
    def on_speech_created(ev):
        nonlocal current_speech_handle
        current_speech_handle=ev.speech_handle

        def on_done(handle):
            nonlocal current_speech_handle
            if current_speech_handle==handle:
                current_speech_handle=None

        ev.speech_handle.add_done_callback(on_done)

    #Now we process only final transcripts while the agent is speaking to decide whether to ignore filler input or interrupt on meaningful commands.
    def on_user_input_transcribed(ev):
        if not ev.is_final:
            return
        if not agent_speaking:
            return
        tokens=normalize(ev.transcript)
        if not tokens:
            return
        filler={"yeah", "ok", "okay", "hmm", "uh", "um"}
        interrupt={"stop", "wait", "no"}
        if any(token in interrupt for token in tokens):
            if current_speech_handle and not current_speech_handle.interrupted:
                logger.info("User interruption detected, stopping speech")
                current_speech_handle.interrupt()
            return
        if all(token in filler for token in tokens):
            logger.info("User said a filler word, continuing speech")
            return
        if current_speech_handle and not current_speech_handle.interrupted:
            logger.info("Overlapping user input detected, stopping speech")
            current_speech_handle.interrupt()

    session.on("agent_state_changed", on_agent_state_changed)
    session.on("speech_created", on_speech_created)
    session.on("user_input_transcribed", on_user_input_transcribed)
    await session.start(agent=Agent(instructions="You are a helpful assistant."), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
