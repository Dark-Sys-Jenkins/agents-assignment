# examples/voice_agents/basic_agent.py

import logging
import time
import asyncio
import inspect
from typing import Optional, Tuple

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.plugins import silero

from interaction_manager import InteractionManager

logger = logging.getLogger("basic-agent")
load_dotenv()


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You interact with users via voice. "
            "Keep responses concise. No markdown. No emojis. "
            "You are friendly and humorous. "
            "\n\nCONTINUOUS CONTEXT PROTOCOL: "
            "If the user interrupts you while you are in the middle of any response or task, "
            "answer their input concisely and then immediately return to your previous "
            "thread of conversation. You must maintain context continuity perfectly, "
            "resuming exactly where you left off without requiring a prompt to continue.",
        )

    async def on_enter(self):
        self.session.generate_reply(allow_interruptions=False)


server = AgentServer()


def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load(
            min_speech_duration=0.15,
            min_silence_duration=0.60,
        )
    except TypeError:
        proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def _build_room_options() -> room_io.RoomOptions:
    audio_input = room_io.AudioInputOptions()
    RoomInputOptions = getattr(room_io, "RoomInputOptions", None)
    room_input_obj = None

    if RoomInputOptions is not None:
        try:
            sig = inspect.signature(RoomInputOptions)
            if "close_on_disconnect" in sig.parameters:
                room_input_obj = RoomInputOptions(close_on_disconnect=False)
            else:
                room_input_obj = RoomInputOptions()
        except:
            room_input_obj = None

    sig = inspect.signature(room_io.RoomOptions)
    kwargs = {}
    if "audio_input" in sig.parameters: kwargs["audio_input"] = audio_input
    if room_input_obj is not None:
        if "room_input" in sig.parameters: kwargs["room_input"] = room_input_obj
        elif "input" in sig.parameters: kwargs["input"] = room_input_obj

    return room_io.RoomOptions(**kwargs)


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection="manual",
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,

        # Storage keys simplified
        userdata={
            "ignore_intent": False,
            "interaction_lock": 0.0,
            "paused_state": False,
            "paused_expiry": 0.0,
            "commit_task": None,
            "event_ts": 0.0,
        },
    )

    # Attach Interaction Controller
    InteractionManager(session=session).attach()

    def _kill_commit():
        t = session.userdata.get("commit_task")
        if t is not None and hasattr(t, "cancel"):
            try: t.cancel()
            except: pass
        session.userdata["commit_task"] = None

    @session.on("user_input_transcribed")
    def _on_transcript(ev: any):
        now = time.monotonic()
        
        # Only treat non-final events as commit-killers if they aren't suspiciously close to a final
        if not ev.is_final:
            session.userdata["event_ts"] = now
            _kill_commit()
            return

        transcript = (ev.transcript or "").strip()
        if not transcript:
            try: session.clear_user_turn()
            except: pass
            return

        logger.debug(f"DEBUG: Final transcript received: {transcript!r}")
        _kill_commit()
        
        # Capture the trigger time for this specific final transcript
        trigger_time = now
        session.userdata["event_ts"] = trigger_time

        async def _run_commit(t: float):
            await asyncio.sleep(0.35)
            
            # Check if a NEWER event arrived during the sleep
            current_ts = float(session.userdata.get("event_ts", 0.0))
            if current_ts > t:
                logger.debug(f"DEBUG: Commit cancelled. New event at {current_ts} > {t}")
                return

            arrival = time.monotonic()
            
            # Interaction Lock check
            lock_expiry = float(session.userdata.get("interaction_lock", 0.0))
            if arrival < lock_expiry:
                logger.debug(f"DEBUG: Commit blocked by interaction lock ({arrival} < {lock_expiry})")
                session.userdata["ignore_intent"] = False
                try: session.clear_user_turn()
                except: pass
                return

            # Intent Filter check
            if session.userdata.get("ignore_intent"):
                logger.debug("DEBUG: Commit blocked by ignore_intent flag")
                session.userdata["ignore_intent"] = False
                try: session.clear_user_turn()
                except: pass
                return

            logger.info(f"DEBUG: Committing user turn for: {transcript!r}")
            session.commit_user_turn()

        session.userdata["commit_task"] = asyncio.create_task(_run_commit(trigger_time))

    collector = metrics.UsageCollector()
    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        collector.collect(ev.metrics)

    async def _cleanup():
        logger.info(f"Summary: {collector.get_summary()}")

    ctx.add_shutdown_callback(_cleanup)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=_build_room_options(),
    )


if __name__ == "__main__":
    cli.run_app(server)
