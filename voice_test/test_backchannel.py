import asyncio
import pytest
import sys
import types

# ------------------------------------------------------------
# STUB OPTIONAL NATIVE EXTENSIONS (to avoid import errors)
# ------------------------------------------------------------
sys.modules["livekit.blingfire"] = types.ModuleType("livekit.blingfire")
sys.modules["lk_blingfire"] = types.ModuleType("lk_blingfire")

from livekit.agents.voice.agent_activity import AgentActivity


# ------------------------------------------------------------
# Minimal dummy classes needed by AgentActivity logic
# ------------------------------------------------------------

def log(msg: str):
    print(msg, flush=True)

class DummyOptions:
    resume_false_interruption = False
    false_interruption_timeout = None
    min_interruption_words = 0
    min_interruption_duration = 0.0
    discard_audio_if_uninterruptible = False


class DummyOutputAudio:
    can_pause = False

    def pause(self):
        raise RuntimeError("pause() should not be called in this unit test")


class DummyOutput:
    audio = DummyOutputAudio()
    audio_enabled = False


class DummySession:
    def __init__(self):
        self.agent_state = "listening"
        self.options = DummyOptions()
        self.output = DummyOutput()

        # IMPORTANT: so AgentActivity.llm property can fall back safely
        self.llm = None

    def _update_agent_state(self, st: str):
        self.agent_state = st

    def emit(self, *args, **kwargs):
        return None

    def _user_input_transcribed(self, *args, **kwargs):
        return None


class DummySpeech:
    def __init__(self):
        self.allow_interruptions = True
        self.interrupted = False

    def done(self):
        return False

    def interrupt(self, *args, **kwargs):
        self.interrupted = True


class DummyAlt:
    def __init__(self, text: str):
        self.text = text
        self.language = "en"
        self.speaker_id = None


class DummySpeechEvent:
    """
    Mimics stt.SpeechEvent shape used by:
    - on_interim_transcript()
    - on_final_transcript()
    """
    def __init__(self, text: str):
        self.alternatives = [DummyAlt(text)]


class DummyGivenValue:
    """
    AgentActivity.llm uses is_given(self._agent.llm)
    so we must provide an object that will evaluate as "not given".
    We'll just make _agent.llm = None so is_given(None) should be False
    in livekit's utils.
    """
    pass


class DummyAgent:
    def __init__(self):
        # make is_given(self._agent.llm) -> False in typical livekit logic
        self.llm = None


# ------------------------------------------------------------
# Helper: initialize required internal fields
# ------------------------------------------------------------

def init_required_fields(act: AgentActivity):
    # Required to avoid AttributeError in llm property access
    if not hasattr(act, "_agent"):
        act._agent = DummyAgent()

    # pending interrupt timer state
    act._pending_interrupt_task = None
    act._pending_interrupt_started_at = None
    act._pending_interrupt_min_delay_s = 0.01
    act._pending_interrupt_max_delay_s = 0.05

    # transcript cache
    act._last_user_transcript_seen_at = None
    act._last_user_transcript_text = ""

    # backchannel sets (your feature)
    act._soft_ignore_words = {"yeah", "ok", "hmm", "aha"}
    act._hard_interrupt_words = {"stop", "wait"}

    # extra safe defaults used in other codepaths
    act._paused_speech = None
    act._false_interruption_timer = None
    act._audio_recognition = None
    act._rt_session = None
    act._turn_detection = "vad"
    act._interrupt_paused_speech_task = None


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_backchannel_does_not_interrupt_when_agent_speaking(monkeypatch):
    sess = DummySession()
    sess.agent_state = "speaking"

    act = AgentActivity.__new__(AgentActivity)
    act._session = sess
    act._current_speech = DummySpeech()
    init_required_fields(act)

    monkeypatch.setattr(AgentActivity, "allow_interruptions", True, raising=False)

    commit_called = False

    def _commit():
        nonlocal commit_called
        commit_called = True

    act._interrupt_by_audio_activity_commit = _commit

    # Simulate VAD indicating user activity during agent speaking
    act._request_interrupt_validation(reason="vad_unit_test")

    # Simulate STT transcript arriving = backchannel
    act._last_user_transcript_text = "yeah"
    act.on_interim_transcript(DummySpeechEvent("yeah"), speaking=True)

    await asyncio.sleep(0.08)

    assert commit_called is False
    assert act._current_speech.interrupted is False


@pytest.mark.asyncio
async def test_hard_interrupt_does_interrupt_when_agent_speaking(monkeypatch):
    sess = DummySession()
    sess.agent_state = "speaking"

    act = AgentActivity.__new__(AgentActivity)
    act._session = sess
    act._current_speech = DummySpeech()
    init_required_fields(act)

    monkeypatch.setattr(AgentActivity, "allow_interruptions", True, raising=False)

    commit_called = False

    def _commit():
        nonlocal commit_called
        commit_called = True
        act._current_speech.interrupt()

    act._interrupt_by_audio_activity_commit = _commit

    act._request_interrupt_validation(reason="vad_unit_test")

    act._last_user_transcript_text = "stop"
    act.on_final_transcript(DummySpeechEvent("stop"), speaking=True)

    await asyncio.sleep(0.08)

    assert commit_called is True
    assert act._current_speech.interrupted is True


@pytest.mark.asyncio
async def test_when_agent_not_speaking_validation_does_not_start(monkeypatch):
    sess = DummySession()
    sess.agent_state = "listening"

    act = AgentActivity.__new__(AgentActivity)
    act._session = sess

    # IMPORTANT: no active speech => not speaking
    act._current_speech = None

    init_required_fields(act)

    monkeypatch.setattr(AgentActivity, "allow_interruptions", True, raising=False)

    act._request_interrupt_validation(reason="vad_unit_test")

    await asyncio.sleep(0.02)

    assert act._pending_interrupt_task is None
