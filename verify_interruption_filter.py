"""Simple verification script for interruption filter logic."""

import sys
sys.path.insert(0, 'livekit-agents')

from livekit.agents.voice.interruption_filter import should_ignore_as_soft_acknowledgment

print("=" * 60)
print("INTERRUPTION FILTER VERIFICATION")
print("=" * 60)

tests_passed = 0
tests_total = 0

def test(description, result, expected):
    global tests_passed, tests_total
    tests_total += 1
    status = "✓ PASS" if result == expected else "✗ FAIL"
    print(f"{status}: {description}")
    if result == expected:
        tests_passed += 1
    else:
        print(f"   Expected: {expected}, Got: {result}")

# Test 1: Soft acknowledgment when agent speaking → should ignore
test(
    "Soft word 'yeah' when agent speaking",
    should_ignore_as_soft_acknowledgment("yeah", True),
    True
)

# Test 2: Soft acknowledgment when agent silent → should NOT ignore
test(
    "Soft word 'yeah' when agent silent",
    should_ignore_as_soft_acknowledgment("yeah", False),
    False
)

# Test 3: Hard interrupt when agent speaking → should NOT ignore
test(
    "Interrupt word 'stop' when agent speaking",
    should_ignore_as_soft_acknowledgment("stop", True),
    False
)

# Test 4: Mixed input → should NOT ignore
test(
    "Mixed input 'yeah but stop' when agent speaking",
    should_ignore_as_soft_acknowledgment("yeah but stop", True),
    False
)

# Test 5: Multiple soft words → should ignore
test(
    "Multiple soft words 'yeah ok' when agent speaking",
    should_ignore_as_soft_acknowledgment("yeah ok", True),
    True
)

# Test 6: Soft + other content → should NOT ignore
test(
    "Soft + content 'yeah tell me more' when agent speaking",
    should_ignore_as_soft_acknowledgment("yeah tell me more", True),
    False
)

# Test 7: Empty transcript → should ignore
test(
    "Empty transcript when agent speaking",
    should_ignore_as_soft_acknowledgment("", True),
    True
)

print("=" * 60)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
print("=" * 60)

if tests_passed == tests_total:
    print("✓ All tests PASSED!")
    sys.exit(0)
else:
    print("✗ Some tests FAILED")
    sys.exit(1)
