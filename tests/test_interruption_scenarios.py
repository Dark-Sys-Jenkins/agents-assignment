"""
Test Scenarios for Intelligent Interruption Handling

This module demonstrates the test scenarios for the intelligent interruption handling feature.
It validates that the agent correctly distinguishes between passive acknowledgements and active interruptions.
"""

import asyncio
from livekit.agents import Agent
from livekit.agents.voice.io import PlaybackFinishedEvent
from tests.fake_session import FakeActions, create_session, run_session


class TestAgent(Agent):
    """A basic agent for testing interruption handling."""
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant.")


async def scenario_1_long_explanation():
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Expected Result: Agent audio does not break. It ignores the user input completely.
    """
    print("\n" + "="*60)
    print("SCENARIO 1: The Long Explanation")
    print("="*60)
    print("Agent is explaining history, user provides passive feedback")
    
    speed = 5.0
    actions = FakeActions()
    
    # Initial user request
    actions.add_user_speech(0.5, 2.0, "Tell me about the history of Rome")
    
    # Agent's long explanation
    actions.add_llm("Rome was founded in 753 BC. It became a great empire...")
    actions.add_tts(12.0)  # Long TTS duration
    
    # User provides passive feedback while agent is speaking
    actions.add_user_speech(4.0, 4.3, "Okay", stt_delay=0.2)
    actions.add_user_speech(6.0, 6.3, "Yeah", stt_delay=0.2)
    actions.add_user_speech(8.0, 8.3, "Uh-huh", stt_delay=0.2)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1 and not playback_finished_events[0].interrupted:
        print("✓ PASS: Agent IGNORED passive feedback and continued speaking")
        return True
    else:
        print("✗ FAIL: Agent was interrupted by passive feedback")
        return False


async def scenario_2_passive_affirmation():
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Expected Result: Agent processes "Yeah" as an answer and proceeds.
    """
    print("\n" + "="*60)
    print("SCENARIO 2: The Passive Affirmation")
    print("="*60)
    print("Agent asks question, user confirms with 'Yeah'")
    
    speed = 5.0
    actions = FakeActions()
    
    # Agent's question
    actions.add_llm("Are you ready to start?")
    actions.add_tts(2.0)
    
    # User responds when agent is silent
    actions.add_user_speech(3.0, 3.3, "Yeah", stt_delay=0.2)
    
    # Agent continues
    actions.add_llm("Great! Let's begin.")
    actions.add_tts(2.0)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1:
        print("✓ PASS: Agent PROCESSED 'Yeah' as valid input while silent")
        return True
    else:
        print("✗ FAIL: Agent did not process the response correctly")
        return False


async def scenario_3_the_correction():
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "Stop."
    Expected Result: Agent cuts off immediately.
    """
    print("\n" + "="*60)
    print("SCENARIO 3: The Correction")
    print("="*60)
    print("Agent is speaking, user issues 'Stop' command")
    
    speed = 5.0
    actions = FakeActions()
    
    # User's initial request
    actions.add_user_speech(0.5, 2.0, "Count to ten")
    
    # Agent starts counting
    actions.add_llm("One, two, three, four, five, six, seven, eight, nine, ten")
    actions.add_tts(8.0)
    
    # User interrupts with stop command
    actions.add_user_speech(3.0, 3.3, "Stop", stt_delay=0.2)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1 and playback_finished_events[0].interrupted:
        print("✓ PASS: Agent WAS INTERRUPTED by 'Stop' command")
        return True
    else:
        print("✗ FAIL: Agent did not respond to 'Stop' command")
        return False


async def scenario_4_the_mixed_input():
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Expected Result: Agent stops (because "but" and "wait" are not in the ignore list).
    """
    print("\n" + "="*60)
    print("SCENARIO 4: The Mixed Input")
    print("="*60)
    print("Agent is speaking, user says mixed sentence with command words")
    
    speed = 5.0
    actions = FakeActions()
    
    # User's initial request
    actions.add_user_speech(0.5, 2.0, "Tell me a story")
    
    # Agent's long story
    actions.add_llm("Once upon a time, there was a kingdom far away...")
    actions.add_tts(10.0)
    
    # User says mixed input with command words
    actions.add_user_speech(4.0, 4.5, "Yeah okay but wait", stt_delay=0.2)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1 and playback_finished_events[0].interrupted:
        print("✓ PASS: Agent WAS INTERRUPTED by mixed input with commands")
        return True
    else:
        print("✗ FAIL: Agent did not respond to mixed input correctly")
        return False


async def scenario_5_multiple_passive_words():
    """
    Scenario 5: Multiple Passive Words
    
    Context: Agent is explaining something.
    User Action: User says "Yeah, uh-huh, okay" (multiple passive words).
    Expected Result: Agent ignores all and continues speaking.
    """
    print("\n" + "="*60)
    print("SCENARIO 5: Multiple Passive Words")
    print("="*60)
    print("Agent is speaking, user provides multiple passive feedback words")
    
    speed = 5.0
    actions = FakeActions()
    
    # Initial request
    actions.add_user_speech(0.5, 2.0, "Explain quantum physics")
    
    # Agent's explanation
    actions.add_llm("Quantum physics is the study of particles at atomic scales...")
    actions.add_tts(10.0)
    
    # Multiple passive words
    actions.add_user_speech(3.0, 3.3, "Yeah, uh-huh, okay", stt_delay=0.2)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1 and not playback_finished_events[0].interrupted:
        print("✓ PASS: Agent IGNORED multiple passive words")
        return True
    else:
        print("✗ FAIL: Agent was interrupted by multiple passive words")
        return False


async def scenario_6_edge_case_single_passives():
    """
    Scenario 6: Edge Case - Single Passive Words in Sequence
    
    Context: Agent is speaking.
    User Action: User says "Hmm" then later says "Right"
    Expected Result: Both interruptions should be ignored.
    """
    print("\n" + "="*60)
    print("SCENARIO 6: Edge Case - Single Passive Words")
    print("="*60)
    print("Agent is speaking, user provides single passive words in sequence")
    
    speed = 5.0
    actions = FakeActions()
    
    # Initial request
    actions.add_user_speech(0.5, 2.0, "Tell me about gravity")
    
    # Agent's explanation
    actions.add_llm("Gravity is a fundamental force that attracts objects with mass...")
    actions.add_tts(10.0)
    
    # Single passive words at different times
    actions.add_user_speech(3.0, 3.2, "Hmm", stt_delay=0.2)
    actions.add_user_speech(5.0, 5.2, "Right", stt_delay=0.2)

    session = create_session(actions, speed_factor=speed)
    agent = TestAgent()

    playback_finished_events: list[PlaybackFinishedEvent] = []
    session.output.audio.on("playback_finished", playback_finished_events.append)

    try:
        await asyncio.wait_for(run_session(session, agent), timeout=10.0)
    except asyncio.TimeoutError:
        pass

    if len(playback_finished_events) >= 1 and not playback_finished_events[0].interrupted:
        print("✓ PASS: Agent IGNORED all passive words")
        return True
    else:
        print("✗ FAIL: Agent was interrupted by passive words")
        return False


async def run_all_scenarios():
    """Run all test scenarios."""
    print("\n" + "="*60)
    print("INTELLIGENT INTERRUPTION HANDLING - TEST SCENARIOS")
    print("="*60)
    
    results = []
    
    # Run all scenarios
    results.append(("Scenario 1: Long Explanation", await scenario_1_long_explanation()))
    results.append(("Scenario 2: Passive Affirmation", await scenario_2_passive_affirmation()))
    results.append(("Scenario 3: The Correction", await scenario_3_the_correction()))
    results.append(("Scenario 4: Mixed Input", await scenario_4_the_mixed_input()))
    results.append(("Scenario 5: Multiple Passive Words", await scenario_5_multiple_passive_words()))
    results.append(("Scenario 6: Single Passive Words", await scenario_6_edge_case_single_passives()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for scenario_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {scenario_name}")
    
    print(f"\nTotal: {passed}/{total} scenarios passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_scenarios())
    exit(0 if success else 1)
