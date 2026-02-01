import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.agents.voice.events import (
    UserInputTranscribedEvent,
    AgentStateChangedEvent,
)
from livekit.plugins import noise_cancellation, silero
from word_lists import FILLER_WORDS, COMMAND_WORDS

logger = logging.getLogger("agent")
load_dotenv()

FILLER_WORDS = set(w.lower() for w in FILLER_WORDS)
COMMAND_WORDS = set(w.lower() for w in COMMAND_WORDS)



def classify_transcript(text: str) -> str:
    """
    Classify transcript as 'filler', 'command', or 'speech'.
    """
    if not text or not text.strip():
        return 'filler'
    
    words = set(text.lower().replace(",", "").replace(".", "").replace("?", "").split())
    
    if words & COMMAND_WORDS:
        return 'command'
    
    if words and words.issubset(FILLER_WORDS):
        return 'filler'
    
    return 'speech'


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )


server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm


# MANUAL TURN DETECTION HANDLER
class ManualTurnHandler:
    """
    Handles context-aware interruption with ZERO pause for filler words.
    
    Key insight: 
    - With turn_detection="manual", VAD and STT do NOT trigger pauses
    - We receive transcripts but decide if they should trigger a turn
    - Only commit_user_turn() will cause the agent to respond
    
    This achieves TRUE "deafness" to filler words.
    """
    
    def __init__(self, session: AgentSession):
        self.session = session
        self._current_transcript = ""
        self._agent_is_speaking = False
        
        # Register event handlers
        session.on("agent_state_changed", self._on_agent_state_changed)
        session.on("user_input_transcribed", self._on_user_input_transcribed)
        
        logger.info("ManualTurnHandler initialized - agent is DEAF to filler words")
    
    def _on_agent_state_changed(self, ev: AgentStateChangedEvent):
        """Track when agent is speaking."""
        self._agent_is_speaking = (ev.new_state == "speaking")
        logger.debug(f"Agent state: {ev.old_state} → {ev.new_state}")
    
    def _on_user_input_transcribed(self, ev: UserInputTranscribedEvent):
        """
        Process transcripts and decide whether to trigger a turn.
        
        STATE-AWARE LOGIC:
        - When agent is SPEAKING:
            - Filler words: IGNORE (agent keeps speaking)
            - Command words: INTERRUPT immediately
            - Regular speech: INTERRUPT
        - When agent is LISTENING:
            - ALL input (including fillers): Commit turn to get a response
        """
        transcript = ev.transcript
        classification = classify_transcript(transcript)
        
        if not ev.is_final:
            logger.debug(f"Interim: '{transcript}' | Class: {classification}")
            return
        
        logger.info(
            f"Final transcript: '{transcript}' | "
            f"Classification: {classification} | "
            f"Agent speaking: {self._agent_is_speaking}"
        )
        
        # STATE-AWARE: Only ignore fillers when agent is SPEAKING
        if self._agent_is_speaking:
            if classification == 'filler':
                logger.info(f"IGNORING filler '{transcript}' - agent is speaking")
                return
            
            if classification == 'command':
                logger.info(f"COMMAND '{transcript}' - interrupting agent")
                self._commit_turn()
                return
            
            logger.info(f"Real speech '{transcript}' - interrupting agent")
            self._commit_turn()
        else:
            # Agent is LISTENING - respond to everything including fillers
            logger.info(f"Agent listening - committing '{transcript}'")
            self._commit_turn()
    
    def _commit_turn(self):
        """Commit the user turn, which will interrupt agent and trigger response."""
        try:
            self.session.commit_user_turn(
                transcript_timeout=2.0,
                stt_flush_duration=0.5
            )
            logger.info("User turn committed")
        except Exception as e:
            logger.error(f"Failed to commit turn: {e}")


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,

        turn_detection="manual",
        resume_false_interruption=False,
        min_interruption_words=0,
    )

    #init handler
    handler = ManualTurnHandler(session)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
