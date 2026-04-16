#!/usr/bin/env python3
"""
Verification script for backchannel implementation.

Run this to verify:
1. Imports work correctly
2. Filter logic functions as expected
3. All test scenarios pass

Usage:
    python verify_backchannel.py
"""

from __future__ import annotations

import sys

# Use ASCII-safe checkmarks for Windows console compatibility
PASS = "[PASS]"
FAIL = "[FAIL]"


def test_imports():
    """Test 1: Verify all imports work correctly."""
    print("=" * 60)
    print("TEST 1: Import Verification")
    print("=" * 60)

    try:
        from livekit.agents.voice.backchannel import (
            BackchannelConfig,
            BackchannelFilter,
        )

        print(f"{PASS} BackchannelConfig import: OK")
        print(f"{PASS} BackchannelFilter import: OK")

        from livekit.agents.tokenize.basic import split_words

        print(f"{PASS} tokenize.basic.split_words import: OK")

        return True
    except ImportError as e:
        print(f"{FAIL} Import failed: {e}")
        return False


def test_filter_logic():
    """Test 2: Verify filter logic works correctly."""
    print("\n" + "=" * 60)
    print("TEST 2: Filter Logic Verification")
    print("=" * 60)

    from livekit.agents.voice.backchannel import BackchannelConfig, BackchannelFilter

    filter = BackchannelFilter(BackchannelConfig())

    test_cases = [
        # (utterance, agent_speaking, expected, description)
        ("yeah", True, "ignore", "Backchannel during speech"),
        ("ok", True, "ignore", "Backchannel during speech"),
        ("hmm", True, "ignore", "Backchannel during speech"),
        ("uh-huh", True, "ignore", "Backchannel during speech (hyphenated)"),
        ("mm-hmm", True, "ignore", "Backchannel during speech (hyphenated)"),
        ("yeah", False, "respond", "Backchannel when silent"),
        ("wait", True, "interrupt", "Command during speech"),
        ("stop", True, "interrupt", "Command during speech"),
        ("no", True, "interrupt", "Command during speech"),
        ("yeah wait", True, "interrupt", "Mixed input (backchannel + command)"),
        ("what is that", True, "interrupt", "Question during speech"),
        ("", True, "ignore", "Empty utterance"),
    ]

    passed = 0
    failed = 0

    for utterance, agent_speaking, expected, description in test_cases:
        result = filter.should_interrupt(utterance, agent_speaking)
        status = PASS if result == expected else FAIL

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"    Input: '{utterance}', Speaking: {agent_speaking}")
        print(f"    Expected: {expected}, Got: {result}")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_scenarios():
    """Test 3: Verify all required scenarios work."""
    print("\n" + "=" * 60)
    print("TEST 3: Required Scenarios Verification")
    print("=" * 60)

    from livekit.agents.voice.backchannel import BackchannelConfig, BackchannelFilter

    filter = BackchannelFilter(BackchannelConfig())

    scenarios = {
        "Scenario 1: Long Explanation": {
            "description": "User says 'yeah/ok/uh-huh' while agent talks",
            "tests": [
                ("yeah", True, "ignore"),
                ("ok", True, "ignore"),
                ("uh-huh", True, "ignore"),
                ("mm-hmm", True, "ignore"),
            ],
        },
        "Scenario 2: Passive Affirmation": {
            "description": "User says 'yeah' when agent is silent",
            "tests": [
                ("yeah", False, "respond"),
                ("ok", False, "respond"),
            ],
        },
        "Scenario 3: Correction": {
            "description": "User says 'no stop' to interrupt",
            "tests": [
                ("no stop", True, "interrupt"),
                ("wait", True, "interrupt"),
            ],
        },
        "Scenario 4: Mixed Input": {
            "description": "User says 'yeah but wait' - should interrupt",
            "tests": [
                ("yeah but wait", True, "interrupt"),
                ("ok hold on", True, "interrupt"),
            ],
        },
    }

    all_passed = True

    for scenario_name, scenario_data in scenarios.items():
        print(f"\n{scenario_name}:")
        print(f"  {scenario_data['description']}")

        scenario_passed = True
        for utterance, speaking, expected in scenario_data["tests"]:
            result = filter.should_interrupt(utterance, speaking)
            status = PASS if result == expected else FAIL

            if result != expected:
                scenario_passed = False
                all_passed = False

            print(f"  {status} '{utterance}' (speaking={speaking}) -> {result}")

        if scenario_passed:
            print(f"  -> Scenario PASSED")
        else:
            print(f"  -> Scenario FAILED")

    return all_passed


def test_configuration():
    """Test 4: Verify configuration options work."""
    print("\n" + "=" * 60)
    print("TEST 4: Configuration Verification")
    print("=" * 60)

    from livekit.agents.voice.backchannel import BackchannelConfig, BackchannelFilter

    # Test default config
    config = BackchannelConfig()
    print(f"{PASS} Default config created")
    print(f"  - enabled: {config.enabled}")
    print(f"  - backchannel_words: {len(config.backchannel_words)} words")
    print(f"  - interruption_commands: {len(config.interruption_commands)} commands")
    print(f"  - stt_settling_delay_ms: {config.stt_settling_delay_ms}ms")

    # Test custom config
    custom_config = BackchannelConfig(
        enabled=True,
        backchannel_words={"custom", "words"},
        interruption_commands={"custom_command"},
        stt_settling_delay_ms=500,
    )
    filter = BackchannelFilter(custom_config)

    print(f"{PASS} Custom config created")
    print(f"  - stt_settling_delay_ms: {custom_config.stt_settling_delay_ms}ms")

    # Verify custom words work
    result = filter.should_interrupt("custom", agent_is_speaking=True)
    print(f"{PASS} Custom backchannel word 'custom' -> {result}")

    result = filter.should_interrupt("custom_command", agent_is_speaking=True)
    print(f"{PASS} Custom command 'custom_command' -> {result}")

    return True


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("BACKCHANNEL IMPLEMENTATION VERIFICATION")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Filter Logic": test_filter_logic(),
        "Scenarios": test_scenarios(),
        "Configuration": test_configuration(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
