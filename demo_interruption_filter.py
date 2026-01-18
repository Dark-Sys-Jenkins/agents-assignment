"""
Demonstration of the Intelligent Interruption Filter

This script demonstrates the backchannel filtering behavior without requiring
a full LiveKit server or API keys. It shows the filter logic in action.

Run this script to generate log output for your submission proof.
"""

import logging
from livekit.agents.voice.interruption_filter import (
    InterruptionFilter,
    InterruptionFilterConfig,
)

# Set up logging to see filter decisions
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_filter():
    """Demonstrate the interruption filter behavior."""

    # Create filter with default configuration
    filter = InterruptionFilter()

    print("=" * 70)
    print("INTELLIGENT INTERRUPTION FILTER DEMONSTRATION")
    print("=" * 70)

    # Test scenarios
    test_cases = [
        # Scenario 1: Agent SPEAKING, user says backchannel words -> IGNORE
        ("yeah", True, "Agent speaking, user says 'yeah'"),
        ("ok", True, "Agent speaking, user says 'ok'"),
        ("uh-huh", True, "Agent speaking, user says 'uh-huh'"),
        ("hmm", True, "Agent speaking, user says 'hmm'"),
        ("sure", True, "Agent speaking, user says 'sure'"),

        # Scenario 2: Agent SILENT, user says backchannel words -> RESPOND
        ("yeah", False, "Agent silent, user says 'yeah'"),
        ("ok", False, "Agent silent, user says 'ok'"),

        # Scenario 3: Agent SPEAKING, user says interrupt words -> INTERRUPT
        ("stop", True, "Agent speaking, user says 'stop'"),
        ("wait", True, "Agent speaking, user says 'wait'"),
        ("no", True, "Agent speaking, user says 'no'"),
        ("what", True, "Agent speaking, user says 'what'"),
        ("help", True, "Agent speaking, user says 'help'"),

        # Scenario 4: Mixed input -> INTERRUPT (contains meaningful content)
        ("yeah but wait", True, "Agent speaking, user says 'yeah but wait'"),
        ("ok stop", True, "Agent speaking, user says 'ok stop'"),
        ("hmm what was that", True, "Agent speaking, user says 'hmm what was that'"),
    ]

    print("\n" + "-" * 70)
    print("TEST RESULTS")
    print("-" * 70)

    for transcript, agent_speaking, description in test_cases:
        result = filter.should_interrupt(transcript, agent_is_speaking=agent_speaking)

        status = "INTERRUPT" if result.should_interrupt else "IGNORE"
        agent_state = "SPEAKING" if agent_speaking else "SILENT"

        print(f"\n[{agent_state}] Input: \"{transcript}\"")
        print(f"  Description: {description}")
        print(f"  Decision: {status}")
        print(f"  Reason: {result.reason}")
        if result.backchannel_words_found:
            print(f"  Backchannel words found: {result.backchannel_words_found}")
        if result.meaningful_words:
            print(f"  Meaningful words: {result.meaningful_words}")

    print("\n" + "=" * 70)
    print("SUMMARY OF KEY BEHAVIORS")
    print("=" * 70)

    # Key demonstration scenarios
    print("\n1. AGENT IGNORING 'yeah' WHILE TALKING:")
    result = filter.should_interrupt("yeah", agent_is_speaking=True)
    print(f"   Input: 'yeah' | Agent State: SPEAKING")
    print(f"   Result: {'IGNORE - Agent continues' if not result.should_interrupt else 'INTERRUPT'}")
    print(f"   Reason: {result.reason}")

    print("\n2. AGENT RESPONDING TO 'yeah' WHEN SILENT:")
    result = filter.should_interrupt("yeah", agent_is_speaking=False)
    print(f"   Input: 'yeah' | Agent State: SILENT")
    print(f"   Result: {'RESPOND - Process as input' if result.should_interrupt else 'IGNORE'}")
    print(f"   Reason: {result.reason}")

    print("\n3. AGENT STOPPING FOR 'stop':")
    result = filter.should_interrupt("stop", agent_is_speaking=True)
    print(f"   Input: 'stop' | Agent State: SPEAKING")
    print(f"   Result: {'INTERRUPT - Agent stops' if result.should_interrupt else 'IGNORE'}")
    print(f"   Reason: {result.reason}")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    demo_filter()
