"""
this agent demonstrates context-aware interruption handling that:
- IGNORES backchannels (yeah, ok, hmm, uh-huh) while speaking
- INTERRUPTS on explicit commands (stop, wait, no) while speaking
- RESPONDS normally to any input when silent
"""

import logging
import sys
# import time
from pathlib import Path
# from collections import defaultdict

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _add_to_syspath(path: Path) -> None:
    if not path.is_dir():
        return
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_add_to_syspath(ROOT / "livekit-agents")
plugins_root = ROOT / "livekit-plugins"
if plugins_root.is_dir():
    for plugin_dir in plugins_root.iterdir():
        if plugin_dir.is_dir() and (plugin_dir / "livekit").is_dir():
            _add_to_syspath(plugin_dir)

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    # MetricsCollectedEvent,
    # RunContext,
    UserInputTranscribedEvent,
    cli,
    # metrics,
    room_io,
)
# from livekit.agents.voice.events import AgentStateChangedEvent, ConversationItemAddedEvent, SpeechCreatedEvent
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
# from livekit.agents.llm import function_tool
from livekit.plugins import silero, deepgram
from livekit.plugins.google import LLM as GeminiLLM
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from interruption_classifier import (
    InterruptionClassifier,
    InterruptionClassifierConfig,
    InterruptionIntent,
)

logger = logging.getLogger("intelligent-interruption-agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

load_dotenv()

# # Latency tracking (commented out - not needed for core functionality)
# _latency_tracker = defaultdict(lambda: {"start": None, "events": []})
#
#
# def log_latency(stage: str, event: str, details: str = "") -> None:
#     now = time.time()
#     tracker = _latency_tracker[stage]
#     
#     if tracker["start"] is None:
#         tracker["start"] = now
#         elapsed = 0.0
#     else:
#         elapsed = now - tracker["start"]
#     
#     tracker["events"].append((now, event, details))
#     
#     elapsed_ms = elapsed * 1000
#     print(f"⏱️  [{stage:15s}] {event:30s} | +{elapsed_ms:7.2f}ms | {details}")


class IntelligentInterruptionAgent(Agent):
    """
    A voice agent with intelligent interruption handling.

    Backchannels like "yeah", "ok", "uh-huh" are ignored while the agent
    is speaking. Commands like "stop", "wait", "no" will interrupt immediately.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You are a helpful voice assistant. "
                "For stories, give an entertaining story to the user, based on their request. Keep it semi short, but not 4-5 lines, and not too long either. "
                "Keep your tone friendly and conversational. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "IMPORTANT: If a user pauses you mid-story and later asks to continue or resume, "
                "pick up EXACTLY where you left off in the story. You can see what you already said "
                "in the conversation history - continue from that point, don't start over."
            ),
        )

    async def on_enter(self) -> None:
        # Generate an initial greeting when the agent starts
        self.session.generate_reply(
            instructions="Greet the user warmly and ask how you can help them today."
        )
    
    # async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
    #     """Called when user finishes speaking - log LLM request start."""
    #     # Logging removed for barebones version
    #     pass

    # # Function tools commented out - not needed for core interruption functionality
    # @function_tool
    # async def tell_story(self, context: RunContext, topic: str) -> str:
    #     """Called when the user asks for a story.
    #
    #     Args:
    #         topic: The topic or theme of the story
    #     """
    #     logger.info(f"Generating story about: {topic}")
    #     return f"Tell a very brief 3-4 sentence story about {topic}. Keep it short to avoid rate limits."
    #
    # @function_tool
    # async def lookup_weather(
    #     self, context: RunContext, location: str, latitude: str, longitude: str
    # ) -> str:
    #     """Called when the user asks for weather information.
    #
    #     Args:
    #         location: The location they are asking for
    #         latitude: The latitude of the location
    #         longitude: The longitude of the location
    #     """
    #     logger.info(f"Looking up weather for {location}")
    #     return f"The weather in {location} is sunny with a temperature of 72 degrees."


def create_interruption_handler(
    session: AgentSession,
    classifier: InterruptionClassifier,
) -> callable:

    def on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        transcript = ev.transcript
        is_final = ev.is_final
        
        agent_state = session.agent_state
        is_speaking = agent_state == "speaking"
        
        intent = classifier.classify(transcript)

        if not is_speaking:
            if is_final and intent == InterruptionIntent.IGNORE_BACKCHANNEL:
                session.clear_user_turn()
                return
            return

        if intent == InterruptionIntent.IGNORE_BACKCHANNEL:
            if is_final:
                session.clear_user_turn()
            return

        elif intent == InterruptionIntent.INTERRUPT_COMMAND:
            try:
                session.interrupt(force=True)
                if is_final:
                    session.clear_user_turn()
            except RuntimeError:
                pass 

        elif intent == InterruptionIntent.INTERRUPT_OTHER:
            try:
                session.interrupt(force=True)
            except RuntimeError:
                pass  
    return on_user_input_transcribed

from livekit.agents import AgentServer

server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """Prewarm the VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Main entrypoint for the voice agent session."""

    # Set up logging context
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Create classifier with default configuration
    # You can customize the backchannel/command word sets here
    classifier_config = InterruptionClassifierConfig(
        interrupt_on_non_backchannel=True,
    )
    classifier = InterruptionClassifier(classifier_config)

    # Create LLM, STT, and TTS instances
    llm_instance = GeminiLLM(model="gemini-2.0-flash-001")
    stt_instance = deepgram.STT(model="nova-3")
    tts_instance = deepgram.TTS(model="aura-2-andromeda-en")
    session = AgentSession(
        stt=stt_instance,
        llm=llm_instance,
        tts=tts_instance,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
        preemptive_generation=True,
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
    )

    interruption_handler = create_interruption_handler(session, classifier)
    session.on("user_input_transcribed", interruption_handler)

    # # Event handlers for logging (commented out - not needed for core functionality)
    # @session.on("speech_created")
    # def _on_speech_created(ev: SpeechCreatedEvent) -> None:
    #     source = ev.source
    #     log_latency("PIPELINE", f"SPEECH CREATED ({source})", 
    #                f"user_initiated={ev.user_initiated}")
    #
    # @session.on("agent_state_changed")
    # def _on_agent_state_changed(ev: AgentStateChangedEvent) -> None:
    #     old_state = ev.old_state
    #     new_state = ev.new_state
    #     if new_state == "thinking":
    #         log_latency("LLM", "THINKING STARTED", f"{old_state} -> {new_state}")
    #     elif new_state == "speaking":
    #         log_latency("TTS", "SPEECH GENERATION STARTED", f"{old_state} -> {new_state}")
    #     elif old_state == "speaking" and new_state != "speaking":
    #         log_latency("TTS", "SPEECH GENERATION COMPLETE", f"{old_state} -> {new_state}")
    #     elif new_state == "listening":
    #         log_latency("PIPELINE", "READY FOR INPUT", f"{old_state} -> {new_state}")
    #
    # @session.on("conversation_item_added")
    # def _on_conversation_item_added(ev: ConversationItemAddedEvent) -> None:
    #     item = ev.item
    #     if hasattr(item, "role") and item.role == "assistant":
    #         content = ""
    #         if hasattr(item, "content"):
    #             if isinstance(item.content, str):
    #                 content = item.content
    #             elif isinstance(item.content, list):
    #                 for part in item.content:
    #                     if hasattr(part, "text"):
    #                         content += part.text
    #         if content:
    #             log_latency("LLM", "RESPONSE TEXT GENERATED", f'"{content[:50]}..."')
    #
    # # Metrics collection (commented out - not needed for core functionality)
    # usage_collector = metrics.UsageCollector()
    #
    # @session.on("metrics_collected")
    # def _on_metrics_collected(ev: MetricsCollectedEvent) -> None:
    #     m = ev.metrics
    #     if hasattr(m, "llm") and m.llm:
    #         llm_metrics = m.llm
    #         ttft_ms = llm_metrics.ttft * 1000 if hasattr(llm_metrics, "ttft") else 0
    #         tokens_per_sec = llm_metrics.tokens_per_second if hasattr(llm_metrics, "tokens_per_second") else 0
    #         prompt_tokens = llm_metrics.prompt_tokens if hasattr(llm_metrics, "prompt_tokens") else 0
    #         completion_tokens = llm_metrics.completion_tokens if hasattr(llm_metrics, "completion_tokens") else 0
    #         log_latency("LLM", "METRICS", 
    #             f"TTFT={ttft_ms:.1f}ms | {tokens_per_sec:.1f} tok/s | "
    #             f"{prompt_tokens}+{completion_tokens} tokens")
    #     if hasattr(m, "tts") and m.tts:
    #         tts_metrics = m.tts
    #         ttfb_ms = tts_metrics.ttfb * 1000 if hasattr(tts_metrics, "ttfb") else 0
    #         audio_duration = tts_metrics.audio_duration if hasattr(tts_metrics, "audio_duration") else 0
    #         chars_count = tts_metrics.characters_count if hasattr(tts_metrics, "characters_count") else 0
    #         log_latency("TTS", "METRICS",
    #             f"TTFB={ttfb_ms:.1f}ms | Audio={audio_duration:.2f}s | {chars_count} chars")
    #     if hasattr(m, "stt") and m.stt:
    #         stt_metrics = m.stt
    #         audio_duration = stt_metrics.audio_duration if hasattr(stt_metrics, "audio_duration") else 0
    #         log_latency("STT", "METRICS", f"Processed {audio_duration:.2f}s of audio")
    #     metrics.log_metrics(ev.metrics)
    #     usage_collector.collect(ev.metrics)
    #
    # async def log_usage() -> None:
    #     summary = usage_collector.get_summary()
    #     logger.info(f"Usage: {summary}")
    #
    # async def shutdown_session() -> None:
    #     await log_usage()
    #     await session.aclose()
    #
    # ctx.add_shutdown_callback(shutdown_session)

    await session.start(
        agent=IntelligentInterruptionAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

    # logger.info(
    #     "Intelligent Interruption Agent started. "
    #     "Using: Gemini 2.0 Flash (LLM), Deepgram Nova-3 (STT), Deepgram Aura-2 (TTS). "
    #     "Backchannels will be ignored while speaking. "
    #     "Commands like 'stop' or 'wait' will interrupt."
    # )


if __name__ == "__main__":
    cli.run_app(server)
