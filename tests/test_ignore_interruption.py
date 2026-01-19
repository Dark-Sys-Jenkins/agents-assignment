import asyncio
import pytest
from livekit.agents import Agent, AgentStateChangedEvent
from livekit.agents.voice.io import PlaybackFinishedEvent
from .fake_session import FakeActions, create_session, run_session

class MyAgent(Agent):
    def __init__(self, interruption_ignore_list=None):
        super().__init__(
            instructions="You are a helpful assistant.",
            interruption_ignore_list=interruption_ignore_list
        )

SESSION_TIMEOUT = 60.0

def check_timestamp(
    t_event: float, t_target: float, *, speed_factor: float = 1.0, max_abs_diff: float = 0.5
) -> None:
    t_event = t_event * speed_factor
    print(f"check_timestamp: t_event: {t_event}, t_target: {t_target}, max_abs_diff: {max_abs_diff}")
    assert abs(t_event - t_target) <= max_abs_diff, (
        f"event timestamp {t_event} is not within {max_abs_diff} of target {t_target}"
    )

async def test_ignored_word() -> None:
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0) # Playback starts ~3.0s
    
    # User says "yeah" at 5.0s (during speech)
    # VAD triggers at 5.0s. STT returns "yeah".
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.1) 
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    assert len(playback_finished_events) == 1
    # Should NOT be interrupted
    assert playback_finished_events[0].interrupted is False 
    # Should play full length (10s)
    check_timestamp(playback_finished_events[0].playback_position, 10.0, speed_factor=speed)

async def test_valid_interruption() -> None:
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0)
    
    # User says "stop" at 5.0s
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.1)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    assert len(playback_finished_events) == 1
    # Should BE interrupted
    assert playback_finished_events[0].interrupted is True
    # Should interrupt around 5.0s + delays
    check_timestamp(playback_finished_events[0].playback_position, (5.0 - 2.6), speed_factor=speed, max_abs_diff=1.0) # 5.0 - 2.6 = 2.4s info speech

async def test_mixed_sentence() -> None:
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0)
    
    # User says "yeah wait" at 5.0s
    actions.add_user_speech(5.0, 5.8, "yeah wait", stt_delay=0.1)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    assert len(playback_finished_events) == 1
    # Should BE interrupted because "wait" is not in ignore list
    assert playback_finished_events[0].interrupted is True

async def test_delayed_transcript_ignored() -> None:
    # Test where VAD triggers but transcript comes later showing it's an ignored word
    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0)
    
    # User says "yeah" at 5.0s, but STT is delayed by 1.0s
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=1.0)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
    check_timestamp(playback_finished_events[0].playback_position, 10.0, speed_factor=speed)

async def test_silent_agent_with_ignored_word() -> None:
    # Matrix Row 3: Agent Silent + User "Yeah" -> Respond (Standard turn)
    speed = 5.0
    actions = FakeActions()
    # No initial agent speech
    
    # User says "yeah" at 1.0s
    actions.add_user_speech(1.0, 1.5, "yeah")
    actions.add_llm("How can I help you?")
    actions.add_tts(5.0)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    # Needs to verify that the agent DID respond.
    # If it ignored it, no TTS would happen (or at least no LLM->TTS flow for response).
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False

async def test_silent_agent_with_normal_input() -> None:
    # Matrix Row 4: Agent Silent + User "Hello" -> Respond (Standard turn)
    speed = 5.0
    actions = FakeActions()
    
    # User says "Hello" at 1.0s
    actions.add_user_speech(1.0, 1.5, "Hello")
    actions.add_llm("Hi there!")
    actions.add_tts(5.0)
    
    session = create_session(actions, speed_factor=speed)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)
    
    await asyncio.wait_for(run_session(session, agent), timeout=SESSION_TIMEOUT)
    
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False
