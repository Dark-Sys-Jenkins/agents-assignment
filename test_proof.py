#!/usr/bin/env python3
"""Test Interruption Filter"""
import sys
sys.path.insert(0, 'livekit-agents')

from livekit.agents.voice.interruption_filter_Satya_Sheel_Shekhar import InterruptionFilter

# Create filter
f = InterruptionFilter()

# Test 1: Agent speaking, user says "yeah"
test1 = f.should_interrupt_agent('yeah', agent_is_speaking=True)
print(f"Test 1 - Agent SPEAKING, User 'yeah': {test1} (expect False) - {'PASS' if test1 == False else 'FAIL'}")

# Test 2: Agent silent, user says "yeah"
test2 = f.should_interrupt_agent('yeah', agent_is_speaking=False)
print(f"Test 2 - Agent SILENT, User 'yeah': {test2} (expect True) - {'PASS' if test2 == True else 'FAIL'}")

# Test 3: Agent speaking, user says "stop"
test3 = f.should_interrupt_agent('stop', agent_is_speaking=True)
print(f"Test 3 - Agent SPEAKING, User 'stop': {test3} (expect True) - {'PASS' if test3 == True else 'FAIL'}")

# Test 4: Agent speaking, user says "yeah wait"
test4 = f.should_interrupt_agent('yeah wait', agent_is_speaking=True)
print(f"Test 4 - Agent SPEAKING, User 'yeah wait': {test4} (expect True) - {'PASS' if test4 == True else 'FAIL'}")

# Summary
all_pass = (test1 == False and test2 == True and test3 == True and test4 == True)
print(f"\nResult: {'ALL TESTS PASS ✓' if all_pass else 'SOME TESTS FAIL ✗'}")
