#!/usr/bin/env python3
"""
Simple test script to verify the interruption filter logic
"""

from config import InterruptionFilterConfig
from interruption_filter import InterruptionFilter, FilterDecision

def test_all_scenarios():
    """Test all 4 required scenarios"""
    filter = InterruptionFilter()
    
    print("🧪 TESTING INTERRUPTION FILTER")
    print("=" * 50)
    
    # Test 1: Backchannels while agent speaking should be IGNORED
    print("\n📋 TEST 1: Backchannels while speaking")
    backchannels = ["yeah", "ok", "uh-huh", "mm-hmm", "right", "sure"]
    for word in backchannels:
        result = filter.filter(word, agent_speaking=True)
        status = "✅ PASS" if result.decision == FilterDecision.IGNORE else "❌ FAIL"
        print(f"   '{word}' (speaking=True) → {result.decision.name} {status}")
    
    # Test 2: Same words when agent silent should be PROCESSED
    print("\n📋 TEST 2: Backchannels when silent")
    for word in backchannels[:3]:  # Test a few
        result = filter.filter(word, agent_speaking=False)
        status = "✅ PASS" if result.decision == FilterDecision.PROCESS else "❌ FAIL"
        print(f"   '{word}' (speaking=False) → {result.decision.name} {status}")
    
    # Test 3: Real interruptions should always INTERRUPT
    print("\n📋 TEST 3: Real interruptions")
    interruptions = ["stop", "wait", "no", "pause", "hold on"]
    for word in interruptions:
        result = filter.filter(word, agent_speaking=True)
        status = "✅ PASS" if result.decision == FilterDecision.INTERRUPT else "❌ FAIL"
        print(f"   '{word}' (speaking=True) → {result.decision.name} {status}")
    
    # Test 4: Mixed input with interruption words
    print("\n📋 TEST 4: Mixed input scenarios")
    mixed_cases = [
        ("yeah ok", True, FilterDecision.IGNORE, "Only backchannels"),
        ("yeah but wait", True, FilterDecision.INTERRUPT, "Contains 'wait'"),
        ("ok stop", True, FilterDecision.INTERRUPT, "Contains 'stop'"),
        ("hmm actually no", True, FilterDecision.INTERRUPT, "Contains 'no'"),
        ("yeah sure", False, FilterDecision.PROCESS, "Backchannels when silent"),
    ]
    
    for transcript, speaking, expected, desc in mixed_cases:
        result = filter.filter(transcript, agent_speaking=speaking)
        status = "✅ PASS" if result.decision == expected else "❌ FAIL"
        print(f"   '{transcript}' (speaking={speaking}) → {result.decision.name} {status} ({desc})")
    
    print("\n" + "=" * 50)
    print("🎯 ALL TESTS COMPLETE!")
    print("\nℹ️  Filter Logic Summary:")
    print("   • When agent speaking + only backchannels → IGNORE")
    print("   • When agent speaking + has interruption words → INTERRUPT") 
    print("   • When agent silent → PROCESS normally")

if __name__ == "__main__":
    test_all_scenarios()