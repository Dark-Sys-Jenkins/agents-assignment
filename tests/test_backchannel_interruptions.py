import asyncio

from livekit.agents.voice.events import ConversationItemAddedEvent, PlaybackFinishedEvent

from .fake_session import FakeActions, create_session, run_session
from .test_agent_session import MyAgent, SESSION_TIMEOUT


async def test_backchannel_ignored_while_speaking() -> None:
    """If the agent is speaking and the user says a backchannel, do not interrupt."""

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.", stt_delay=0.0)
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)  # playout starts at ~3.5s

    # Backchannel while the agent is mid-speech.
    actions.add_user_speech(5.0, 5.2, "yeah", stt_delay=0.0)

    session = create_session(actions, speed_factor=speed)

    conversation_events: list[ConversationItemAddedEvent] = []
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.on("conversation_item_added", conversation_events.append)
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(
        run_session(session, MyAgent(), drain_delay=3.0), timeout=SESSION_TIMEOUT
    )

    # Only the initial user turn and the agent reply should be in the chat context.
    assert len(conversation_events) == 2
    assert conversation_events[0].message.role == "user"
    assert conversation_events[1].message.role == "assistant"

    # Agent TTS should finish normally (no interruption).
    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is False


async def test_backchannel_responds_when_silent() -> None:
    """If the agent is silent, a backchannel is a valid user turn and should get a response."""

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 1.0, "Hi", stt_delay=0.0)
    actions.add_llm("Are you ready?")
    actions.add_tts(1.0)

    # Wait until the agent is done speaking (playout ~3.5-4.5s) and then answer.
    actions.add_user_speech(5.0, 5.2, "yeah", stt_delay=0.0)
    actions.add_llm("Great, starting now.")
    actions.add_tts(1.0)

    session = create_session(actions, speed_factor=speed)
    conversation_events: list[ConversationItemAddedEvent] = []
    session.on("conversation_item_added", conversation_events.append)

    await asyncio.wait_for(
        run_session(session, MyAgent(), drain_delay=3.0), timeout=SESSION_TIMEOUT
    )

    # user("Hi"), assistant("Are you ready?"), user("yeah"), assistant("Great...")
    assert [e.message.role for e in conversation_events] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


async def test_hard_interrupt_overrides_min_interruption_words() -> None:
    """Explicit stop/wait commands should interrupt even when min_interruption_words is high."""

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.", stt_delay=0.0)
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)

    actions.add_user_speech(5.0, 5.2, "stop", stt_delay=0.0)

    session = create_session(actions, speed_factor=speed, extra_kwargs={"min_interruption_words": 10})
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(
        run_session(session, MyAgent(), drain_delay=3.0), timeout=SESSION_TIMEOUT
    )

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True


async def test_mixed_input_interrupts() -> None:
    """Mixed utterances like 'yeah ... wait' should still interrupt due to the hard command."""

    speed = 5.0
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.5, "Tell me a story.", stt_delay=0.0)
    actions.add_llm("Here is a long story for you ... the end.")
    actions.add_tts(10.0)

    actions.add_user_speech(5.0, 5.4, "yeah okay but wait", stt_delay=0.0)

    session = create_session(actions, speed_factor=speed)
    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    await asyncio.wait_for(
        run_session(session, MyAgent(), drain_delay=3.0), timeout=SESSION_TIMEOUT
    )

    assert len(playback_finished_events) == 1
    assert playback_finished_events[0].interrupted is True
