import types
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

# import the AgentActivity class from the repo package
from livekit.agents.voice.agent_activity import AgentActivity
from livekit.agents import llm

def make_activity(transcript: str, speaking: bool, ignore_list=None):
    # create AgentActivity instance without running __init__
    activity = object.__new__(AgentActivity)

    # minimal _agent and _session to satisfy property accessors used by _interrupt_by_audio_activity
    # self.stt property will check agent.stt (is_given logic expects NOT_GIVEN sentinel in repo,
    # but any truthy value will count as "given" within the tests).
    activity._agent = SimpleNamespace(stt=True)

    # Mock the llm property - create a mock that is NOT a RealtimeModel
    activity.llm = Mock(spec=llm.LLM)

    # session.options needs several fields used by the function under test
    options = SimpleNamespace(
        min_interruption_words=0,
        false_interruption_timeout=None,
        resume_false_interruption=False,
        ignore_words=ignore_list,
    )

    # audio output with can_pause + pause/resume methods (not exercised in all tests)
    audio_output = SimpleNamespace(can_pause=True, pause=Mock(), resume=Mock())

    session = SimpleNamespace(
        options=options,
        output=SimpleNamespace(audio=audio_output),
        _update_agent_state=Mock(),
        emit=Mock(),
    )
    activity._session = session

    # audio recognition object exposes current_transcript
    activity._audio_recognition = SimpleNamespace(current_transcript=transcript)

    # realtime session start/interrupt hooks
    activity._rt_session = SimpleNamespace(start_user_activity=Mock(), interrupt=Mock())

    # false interruption timer
    activity._false_interruption_timer = None
    
    # paused speech
    activity._paused_speech = None

    # current speech handle (when agent is speaking) or None (when silent)
    if speaking:
        speech_handle = Mock()
        speech_handle.interrupted = False
        speech_handle.allow_interruptions = True
        speech_handle.interrupt = Mock()
        activity._current_speech = speech_handle
    else:
        activity._current_speech = None

    return activity

def test_ignore_ack_while_speaking():
    # "yeah" is in the ignore list -> should NOT call interrupt()
    act = make_activity(transcript="yeah", speaking=True, ignore_list=["yeah", "ok", "hmm"])
    act._interrupt_by_audio_activity()
    assert act._current_speech.interrupt.call_count == 0

def test_interrupt_on_stop_while_speaking():
    # "stop" should cause an interruption
    act = make_activity(transcript="stop", speaking=True, ignore_list=["yeah", "ok", "hmm"])
    act._interrupt_by_audio_activity()
    assert act._current_speech.interrupt.call_count == 1

def test_respond_when_silent_ack():
    # When silent, a short "yeah" should not try to interrupt speech (there's none)
    act = make_activity(transcript="yeah", speaking=False, ignore_list=["yeah", "ok"])
    act._interrupt_by_audio_activity()
    # no speech handle to interrupt; ensure start_user_activity is called to mark user activity
    assert act._rt_session.start_user_activity.call_count == 1

def test_mixed_input_should_interrupt():
    # mixed "yeah wait a second" contains 'wait' -> should interrupt
    act = make_activity(transcript="yeah wait a second", speaking=True, ignore_list=["yeah", "ok"])
    act._interrupt_by_audio_activity()
    assert act._current_speech.interrupt.call_count == 1