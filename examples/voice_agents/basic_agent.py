# examples/voice_agents/basic_agent.py

import logging
import time
import asyncio
import inspect
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    UserInputTranscribedEvent,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero

from backchannel_handler import BackchannelInterruptionHandler

logger = logging.getLogger("basic-agent")
load_dotenv()


def _weather_code_to_text(code: Optional[int]) -> str:
    # Open-Meteo weather codes (simplified)
    if code is None:
        return "unknown conditions"
    if code == 0:
        return "clear sky"
    if code in (1, 2, 3):
        return "partly cloudy"
    if code in (45, 48):
        return "foggy"
    if code in (51, 53, 55):
        return "light drizzle"
    if code in (61, 63, 65):
        return "rain"
    if code in (71, 73, 75):
        return "snow"
    if code in (80, 81, 82):
        return "rain showers"
    if code in (95, 96, 99):
        return "thunderstorms"
    return "mixed conditions"


async def _http_get_json(url: str, params: dict) -> dict:
    def _do():
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    return await asyncio.to_thread(_do)


async def _geocode_location(name: str) -> Tuple[float, float]:
    # Open-Meteo geocoding (no API key)
    data = await _http_get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": name, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not geocode location: {name}")
    res = results[0]
    return float(res["latitude"]), float(res["longitude"])


async def _get_current_weather(lat: float, lon: float) -> Tuple[Optional[float], Optional[int]]:
    data = await _http_get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code",
            "timezone": "auto",
        },
    )
    current = data.get("current") or {}
    temp = current.get("temperature_2m")
    code = current.get("weather_code")

    try:
        temp_f = float(temp) if temp is not None else None
    except Exception:
        temp_f = None

    try:
        code_i = int(code) if code is not None else None
    except Exception:
        code_i = None

    return temp_f, code_i


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Your name is Kelly. You talk to users via voice. "
                "Answer clearly and correctly. If a question is simple, answer directly in one short reply. "
                "If you need a detail to answer, ask one short follow-up question. "
                "Do not use emojis, markdown, or special characters. "
                "Do not respond with filler like 'Okay.' or 'Sure.' by itself. "

                "If you asked a yes/no question and the user answers with yes/yeah/no, treat it as a valid answer and respond. "
                "If the user says stop while you are talking, stop immediately. "
                "If the user then says yeah/okay/uh-huh/hmm soon after that, continue your previous response from where you stopped. "

                "If the user says short acknowledgements like ok/yeah/hmm when you did not ask a question, "
                "do not add extra commentary."
            ),
        )

    async def on_enter(self):
        # Do NOT auto-generate a reply on enter.
        return

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str):
        """Called when the user asks for weather related information."""
        try:
            loc = (location or "").strip()
            if not loc:
                return "Which city should I check the weather for?"

            logger.info(f"Geocoding location={loc!r}")
            lat, lon = await _geocode_location(loc)

            logger.info(f"Looking up weather for {loc} at lat={lat}, lon={lon}")
            temp_c, code = await _get_current_weather(lat, lon)
            desc = _weather_code_to_text(code)

            if temp_c is None:
                return f"I found the weather for {loc}, but could not read the temperature. It looks like {desc}."

            temp_rounded = round(float(temp_c))
            return f"In {loc}, it is {desc} with a temperature around {temp_rounded} degrees Celsius."

        except Exception:
            logger.exception("lookup_weather failed")
            return "Sorry, I could not fetch the weather right now."


server = AgentServer()


def prewarm(proc: JobProcess):
    # Make VAD less eager so it doesn't mark your pause as "end of sentence" too quickly.
    # If it still cuts you off, raise min_silence_duration to 0.75 or 0.90.
    try:
        proc.userdata["vad"] = silero.VAD.load(
            min_speech_duration=0.15,
            min_silence_duration=0.60,
        )
    except TypeError:
        proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def _build_room_options() -> room_io.RoomOptions:
    """
    Compatibility helper.

    Your installed version threw:
    TypeError: AudioInputOptions.__init__() got an unexpected keyword argument 'close_on_disconnect'

    So we must NOT pass close_on_disconnect into AudioInputOptions.

    This helper:
    - Creates AudioInputOptions() with no kwargs.
    - If your version provides RoomInputOptions with close_on_disconnect, set it there.
    - Otherwise omit it.
    """
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
        except Exception:
            room_input_obj = None

    sig = inspect.signature(room_io.RoomOptions)
    kwargs = {}

    if "audio_input" in sig.parameters:
        kwargs["audio_input"] = audio_input

    if room_input_obj is not None:
        if "room_input" in sig.parameters:
            kwargs["room_input"] = room_input_obj
        elif "input" in sig.parameters:
            kwargs["input"] = room_input_obj

    return room_io.RoomOptions(**kwargs)


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    session = AgentSession(
        stt="deepgram/nova-3",
        llm="google/gemini-2.0-flash",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection="manual",
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,

        # We control interruption ourselves in BackchannelInterruptionHandler.
        allow_interruptions=False,
        discard_audio_if_uninterruptible=False,

        userdata={
            "swallow_next_commit": False,
            "swallow_until": 0.0,              # time-bounded swallow
            "suppress_commits_until": 0.0,
            "paused_by_stop": False,
            "paused_resume_deadline": 0.0,

            # Debounce commit fields (prevents replying too early)
            "pending_commit_task": None,
            "last_transcript_time": 0.0,
        },
    )

    BackchannelInterruptionHandler(session=session).attach()

    # Debounced commit: prevents committing a "final" too early while user is still talking
    def _cancel_pending_commit():
        t = session.userdata.get("pending_commit_task")
        if t is not None and hasattr(t, "cancel"):
            try:
                t.cancel()
            except Exception:
                pass
        session.userdata["pending_commit_task"] = None

    @session.on("user_input_transcribed")
    def _commit_on_final(ev: UserInputTranscribedEvent):
        now = time.monotonic()
        session.userdata["last_transcript_time"] = now

        # Any partial means user is still talking -> cancel any pending commit
        if not ev.is_final:
            _cancel_pending_commit()
            return

        transcript = (ev.transcript or "").strip()
        if not transcript:
            try:
                session.clear_user_turn()
            except Exception:
                pass
            return

        # Cancel any pending commit and schedule a debounced commit
        _cancel_pending_commit()

        async def _delayed_commit(start_time: float):
            # Small debounce window: if more speech arrives, we won't commit yet
            await asyncio.sleep(0.35)

            # If any newer transcript arrived after we scheduled, do nothing
            try:
                if float(session.userdata.get("last_transcript_time", 0.0)) > start_time:
                    return
            except Exception:
                return

            now2 = time.monotonic()

            # If we recently interrupted, ignore late final commits
            try:
                if now2 < float(session.userdata.get("suppress_commits_until", 0.0)):
                    try:
                        session.clear_user_turn()
                    except Exception:
                        pass
                    # clear one-shot flags
                    session.userdata["swallow_next_commit"] = False
                    session.userdata["swallow_until"] = 0.0
                    return
            except Exception:
                pass

            # Time-bounded swallow: swallow ONLY if still inside the swallow window.
            try:
                swallow_until = float(session.userdata.get("swallow_until", 0.0))
                if now2 < swallow_until:
                    session.userdata["swallow_next_commit"] = False
                    try:
                        session.clear_user_turn()
                    except Exception:
                        pass
                    return
                else:
                    # If window is over, ensure we don't accidentally swallow the next real prompt
                    session.userdata["swallow_next_commit"] = False
                    session.userdata["swallow_until"] = 0.0
            except Exception:
                pass

            session.commit_user_turn()

        session.userdata["pending_commit_task"] = asyncio.create_task(_delayed_commit(now))

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=_build_room_options(),
    )


if __name__ == "__main__":
    cli.run_app(server)
