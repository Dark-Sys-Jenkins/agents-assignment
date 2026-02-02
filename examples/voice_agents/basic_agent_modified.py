"""
Real-Time Filler Detection Using AssemblyAI Word-Level Streaming

AssemblyAI sends words as they're spoken with timestamps.
We can detect fillers as they come and prevent agent pausing.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Set, List, Optional
from dotenv import load_dotenv
import time
import os

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
    stt,
)
from livekit.agents.llm import function_tool
from livekit.plugins import assemblyai, silero

load_dotenv(".env.local")

os.makedirs("logs", exist_ok=True)

debug_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

debug_handler = RotatingFileHandler(
    "logs/agent_debug.log", maxBytes=20 * 1024 * 1024, backupCount=5
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(debug_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(debug_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[debug_handler, console_handler])

logger = logging.getLogger("realtime-agent")
logger.setLevel(logging.DEBUG)

class FillerDetector:
    """
    Detects filler words in real-time using AssemblyAI's word-level streaming.
    """

    IGNORE_LIST: Set[str] = {
        "yeah", "ok", "okay", "hmm", "right", "uh-huh", "mhm", "mm-hmm",
        "yep", "yup", "sure", "gotcha", "alright", "i see", "got it",
        "uh", "um", "er", "ah", "cool", "nice", "mhmm", "hm", "all right", 
        "got you", "fair enough", "makes sense", "oh", "yea", "Okay", "Ok", 'OK', "OKAY",
    }

    INTERRUPT_LIST: Set[str] = {
        "wait",
        "stop",
        "no",
        "hold",
        "pause",
        "cancel",
        "never mind",
        "nevermind",
        "hang on",
        "hold on",
        "but",
        "however",
        "actually",
        "although",
        "except",
        "never mind",
        "isn't",
        "not",
        "no",
        "nah",
    }

    def __init__(self):
        self.is_agent_speaking = False
        self.current_words: List[str] = [] 

        self.filtered_count = 0
        self.utterance_start_time = None

    def normalize_word(self, word: str) -> str:
        return word.lower().strip().rstrip(".,!?;:")


    def add_word(self, word: str) -> dict:
        normalized = self.normalize_word(word)
        self.current_words.append(normalized)

        if self.utterance_start_time is None:
            self.utterance_start_time = time.time()

        result = {
            "word": normalized,
            "words_so_far": self.current_words.copy(),
            "agent_speaking": self.is_agent_speaking,
            "action": "CONTINUE",
            "reason": "",
        }

        if not self.is_agent_speaking:
            result["action"] = "CONTINUE"
            result["reason"] = "Agent silent - normal flow"
            return result

        if normalized in self.INTERRUPT_LIST:
            result["action"] = "INTERRUPT"
            result["reason"] = f"Interrupt word: '{normalized}'"
            logger.warning(f"INTERRUPT WORD: '{normalized}'")
            
            return result

        if normalized in self.IGNORE_LIST:
            if all(w in self.IGNORE_LIST for w in self.current_words):
                result["action"] = "IGNORE"
                result["reason"] = "Only filler words so far"
                logger.debug(f"Filler accumulating: {self.current_words}")
                return result
            else:
                result["action"] = "INTERRUPT"
                result["reason"] = "Filler + meaningful content"
                logger.warning(f"Meaningful content detected: {self.current_words}")
                return result

        result["action"] = "INTERRUPT"
        result["reason"] = f"Meaningful word: '{normalized}'"
        logger.warning(f"MEANINGFUL: '{normalized}' in {self.current_words}")
        
        return result


    def finalize_utterance(self, final_text: str) -> dict:
        """Process final transcript."""
        result = {
            "final_text": final_text,
            "words_received": self.current_words.copy(),
            "agent_speaking": self.is_agent_speaking,
            "action": "RESPOND",
            "reason": "",
        }

        if not self.is_agent_speaking:
            result["action"] = "RESPOND"
            result["reason"] = "Agent was silent"
        elif any(
            self.normalize_word(w) in self.INTERRUPT_LIST for w in self.current_words
        ) or any(
            a + " " + b in self.INTERRUPT_LIST
            for a, b in zip(self.current_words, self.current_words[1:])
        ):
            result["action"] = "INTERRUPT"
            result["reason"] = "Contains interrupt word"
        elif all(w in self.IGNORE_LIST for w in self.current_words) or all(
            a + " " + b in self.IGNORE_LIST
            for a, b in zip(self.current_words, self.current_words[1:])
        ):
            result["action"] = "IGNORE"
            result["reason"] = "Only filler words/phrases"
            self.filtered_count += 1
            logger.info(f"FINAL IGNORE: '{final_text}'")
            
        else:
            result["action"] = "INTERRUPT"
            result["reason"] = "Contains meaningful content"

        self.current_words = []
        self.utterance_start_time = None

        return result


class MyAgent(Agent):
    def __init__(self, session: AgentSession) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You interact with users via voice. "
                "Keep your responses concise and to the point. "
                "Do not use emojis, asterisks, markdown, or other special characters. "
                "You are curious and friendly, and have a sense of humor. "
                "You speak English to the user. "
                "\n\n"
                "When users say brief acknowledgments like 'okay', 'yeah', or 'hmm' "
                "while you're speaking, ignore these completely and continue naturally. "
                "These are just listening signals, not requests for you to stop or respond."
            ),
        )
        # self.session = session
        self.should_suppress = False

    async def on_enter(self):
        """Generate initial greeting."""
        await self.session.say("Hi! I'm Kelly. How can I help you today?")

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Weather lookup function."""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    """Prewarm models with tuned VAD."""
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=0.07,
        min_silence_duration=0.8,  
        activation_threshold=0.7,
    )


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entrypoint with word-level filler detection."""
    ctx.log_context_fields = {"room": ctx.room.name}

    # AssemblyAI for word-level streaming
    stt_instance = assemblyai.STT(
        end_of_turn_confidence_threshold=0.7,  
        min_end_of_turn_silence_when_confident=600,
    )

    session = AgentSession(
        stt=stt_instance,
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection="stt",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        min_endpointing_delay=0.5,
        resume_false_interruption=True,
        false_interruption_timeout=0.4,
        allow_interruptions=True,
    )

    agent = MyAgent(session)

    @session.on("agent_started_speaking")
    def on_agent_started_speaking():
        logger.info(" Agent STARTED speaking")
        agent.filler_detector.is_agent_speaking = True


    @session.on("agent_stopped_speaking")
    def on_agent_stopped_speaking():
        logger.info("Agent STOPPED speaking")
        agent.filler_detector.is_agent_speaking = False


    @session.on("user_speech_interim")
    def on_user_speech_interim(event: stt.SpeechEvent):
        """
        Process PARTIAL transcripts with word-level data.
        
        AssemblyAI sends PartialTranscript with:
        - text: cumulative text so far
        - words: list of Word objects with text, start, end, confidence
        """
        if not event.alternatives:
            return

        alternative = event.alternatives[0]
        partial_text = alternative.text

        # AssemblyAI provides words in the alternative
        # Check if words are available in the event
        if hasattr(alternative, 'words') and alternative.words:
            for word_obj in alternative.words:
                word_text = word_obj.text if hasattr(word_obj, 'text') else str(word_obj)

                evaluation = agent.filler_detector.add_word(word_text)

                if evaluation["action"] == "INTERRUPT":
                    logger.warning(
                        f" Word-level INTERRUPT: '{word_text}'\n"
                        f"   Words so far: {evaluation['words_so_far']}\n"
                        f"   Reason: {evaluation['reason']}"
                    )
                    agent.should_suppress = False

                elif evaluation["action"] == "IGNORE":
                    logger.debug(
                        f"Still filler: '{word_text}' "
                        f"(words: {evaluation['words_so_far']})"
                    )
                    session.drain()
                    agent.should_suppress = True
        else:
            words = partial_text.split()
            if words:
                last_word = words[-1]
                evaluation = agent.filler_detector.add_word(last_word)

                if evaluation["action"] == "IGNORE":
                    agent.should_suppress = True
                    logger.debug(f" Filler partial: '{partial_text}'")
                else:
                    agent.should_suppress = False
                    logger.debug(f" Meaningful partial: '{partial_text}'")

    @session.on("user_speech_committed")
    def on_user_speech_committed(event: stt.SpeechEvent):
        """Final transcript - make final decision."""
        if not event.alternatives:
            return

        final_text = event.alternatives[0].text
        logger.info(f" FINAL: '{final_text}'")

        # Get final evaluation
        evaluation = agent.filler_detector.finalize_utterance(final_text)

        logger.info(
            f"📊 FINAL EVALUATION:\n"
            f"   Text: '{final_text}'\n"
            f"   Words: {evaluation['words_received']}\n"
            f"   Action: {evaluation['action']}\n"
            f"   Reason: {evaluation['reason']}"
        )

        if evaluation["action"] == "IGNORE":
            logger.warning(f"DRAINING filler message: '{final_text}'")
            session.drain()

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
        
    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
