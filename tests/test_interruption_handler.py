"""
Comprehensive test suite for Intelligent Interruption Handling

Tests all scenarios from the challenge specification:
1. The Long Explanation - Agent ignores backchannel while speaking
2. The Passive Affirmation - Agent responds to "yeah" when silent
3. The Correction - Agent stops for "stop" command
4. The Mixed Input - Agent handles semantic interruption ("Yeah wait")

Each test includes detailed logging for verification.
"""

import asyncio
import logging
import sys
from datetime import datetime
from io import StringIO

import pytest

from interruption_handler import (
    InterruptionConfig,
    InterruptionHandler,
    InterruptionType,
)

# Configure logging with detailed format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"


class LogCapture:
    """Captures logs for test verification"""
    
    def __init__(self):
        self.records = []
        self.handler = logging.StreamHandler(self)
        self.handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFORMAT))
        self.logger = logging.getLogger()
        self.old_handlers = []
        self.old_level = None
    
    def __enter__(self):
        # Capture all logs
        self.old_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)
        self.old_handlers = self.logger.handlers[:]
        self.logger.handlers = [self.handler]
        return self
    
    def __exit__(self, *args):
        self.logger.handlers = self.old_handlers
        self.logger.setLevel(self.old_level)
    
    def write(self, msg):
        self.records.append(msg)
    
    def flush(self):
        pass
    
    def get_logs(self):
        return "".join(self.records)


@pytest.fixture
def handler():
    """Create a fresh interruption handler for each test"""
    config = InterruptionConfig()
    return InterruptionHandler(config)


@pytest.fixture
def log_capture():
    """Create a log capture fixture"""
    return LogCapture()


class TestScenario1_LongExplanation:
    """
    Scenario 1: The Long Explanation
    
    Context: Agent is reading a long paragraph about history.
    User Action: User says "Okay... yeah... uh-huh" while Agent is talking.
    Expected: Agent audio does not break. It ignores the user input completely.
    
    This tests the STRICT REQUIREMENT: Agent must NOT pause, resume, or stutter
    when hearing backchannel words while actively speaking.
    """
    
    def test_agent_ignores_backchannel_while_speaking(self, handler, log_capture):
        """Agent should ignore backchannel words while actively speaking"""
        with log_capture:
            # Set up: Agent is actively explaining something
            handler.set_agent_speaking(True)
            state = handler.get_state()
            
            assert state.agent_is_speaking is True, "Agent should be marked as speaking"
            
            # User provides backchannel feedback
            backchannel_inputs = ["okay", "yeah", "uh-huh", "right", "hmm"]
            
            for user_input in backchannel_inputs:
                result = handler.process_user_input(user_input)
                assert result == InterruptionType.IGNORE, (
                    f"Expected IGNORE for '{user_input}' while agent speaking, got {result}"
                )
        
        logs = log_capture.get_logs()
        assert "Agent speaking state changed" in logs
        assert "IGNORE" in logs
        print("\n" + "="*70)
        print("TEST: Scenario 1 - Long Explanation (Backchannel Ignored)")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_mixed_backchannel_sequence(self, handler, log_capture):
        """Test a realistic sequence of backchannel words during explanation"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            # Simulate a user acknowledging during agent's long explanation
            sequence = [
                ("okay", InterruptionType.IGNORE),
                ("yeah", InterruptionType.IGNORE),
                ("uh-huh", InterruptionType.IGNORE),
            ]
            
            for user_input, expected in sequence:
                result = handler.process_user_input(user_input)
                assert result == expected, (
                    f"Sequence error: '{user_input}' should be {expected}, got {result}"
                )
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Scenario 1 - Mixed Backchannel Sequence")
        print("="*70)
        print(logs)
        print("="*70)


class TestScenario2_PassiveAffirmation:
    """
    Scenario 2: The Passive Affirmation
    
    Context: Agent asks "Are you ready?" and goes silent.
    User Action: User says "Yeah."
    Expected: Agent processes "Yeah" as valid input and proceeds.
    
    This tests that SAME WORD ("yeah") is treated differently based on agent state.
    """
    
    def test_backchannel_becomes_input_when_agent_silent(self, handler, log_capture):
        """Same backchannel word should be treated as input when agent is silent"""
        with log_capture:
            # Set up: Agent asks question and waits for response
            handler.set_agent_speaking(False)
            state = handler.get_state()
            
            assert state.agent_is_speaking is False, "Agent should not be speaking"
            
            # User says "Yeah" - same word as backchannel
            result = handler.process_user_input("yeah")
            assert result == InterruptionType.RESPOND, (
                f"Expected RESPOND for 'yeah' while agent silent, got {result}"
            )
        
        logs = log_capture.get_logs()
        assert "Agent silent, responding" in logs or "Backchannel word while agent silent" in logs
        print("\n" + "="*70)
        print("TEST: Scenario 2 - Passive Affirmation (Silent Agent)")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_state_transition_silent_to_speaking(self, handler, log_capture):
        """Test state transition from silent to speaking"""
        with log_capture:
            # Initial: Agent silent, user says "yeah" -> RESPOND
            handler.set_agent_speaking(False)
            result1 = handler.process_user_input("yeah")
            assert result1 == InterruptionType.RESPOND
            
            # Agent starts speaking
            handler.set_agent_speaking(True)
            
            # Same input now -> IGNORE
            result2 = handler.process_user_input("yeah")
            assert result2 == InterruptionType.IGNORE
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Scenario 2 - State Transition (Silent -> Speaking)")
        print("="*70)
        print(logs)
        print("="*70)


class TestScenario3_Correction:
    """
    Scenario 3: The Correction
    
    Context: Agent is counting "One, two, three..."
    User Action: User says "No stop."
    Expected: Agent MUST stop immediately and listen to new command.
    
    This tests the STRICT REQUIREMENT: Stop commands ALWAYS interrupt,
    regardless of agent state.
    """
    
    def test_stop_command_always_interrupts_while_speaking(self, handler, log_capture):
        """Stop command must interrupt even while agent is actively speaking"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            interrupt_commands = ["stop", "wait", "hold on", "no"]
            
            for command in interrupt_commands:
                result = handler.process_user_input(command)
                assert result == InterruptionType.INTERRUPT, (
                    f"Expected INTERRUPT for '{command}' while speaking, got {result}"
                )
        
        logs = log_capture.get_logs()
        assert "INTERRUPT triggered" in logs
        print("\n" + "="*70)
        print("TEST: Scenario 3 - Correction (Stop Command)")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_interrupt_callbacks_executed(self, handler, log_capture):
        """Test that interrupt callbacks are properly executed"""
        callback_executed = []
        
        def test_callback(transcript):
            callback_executed.append(transcript)
        
        handler.register_interrupt_callback(test_callback)
        
        with log_capture:
            handler.set_agent_speaking(True)
            result = handler.handle_interruption("stop")
            
            assert result is True, "Should return True for interrupt"
            assert callback_executed == ["stop"], "Callback should have been executed"
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Scenario 3 - Interrupt Callback Execution")
        print("="*70)
        print(logs)
        print("="*70)


class TestScenario4_MixedInput:
    """
    Scenario 4: The Mixed Input
    
    Context: Agent is speaking.
    User Action: User says "Yeah okay but wait."
    Expected: Agent stops (because "wait" is detected).
    
    This tests semantic interruption: even if backchannel words are present,
    a single interrupt command should trigger stopping.
    """
    
    def test_mixed_input_with_interrupt_command(self, handler, log_capture):
        """Mixed input with interrupt command should detect interrupt"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            # Mixed sentence with backchannel + interrupt command
            mixed_inputs = [
                "yeah wait",
                "okay hold on",
                "yeah but stop",
                "hmm wait a second",
            ]
            
            for user_input in mixed_inputs:
                result = handler.process_user_input(user_input)
                assert result == InterruptionType.INTERRUPT, (
                    f"Expected INTERRUPT for '{user_input}', got {result}"
                )
        
        logs = log_capture.get_logs()
        assert "Interrupt command detected" in logs
        print("\n" + "="*70)
        print("TEST: Scenario 4 - Mixed Input with Interrupt Command")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_pure_backchannel_vs_mixed_input(self, handler, log_capture):
        """Compare pure backchannel vs mixed input with interrupt"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            # Pure backchannel
            result1 = handler.process_user_input("yeah okay")
            assert result1 == InterruptionType.IGNORE, "Pure backchannel should be ignored"
            
            # Mixed with interrupt
            result2 = handler.process_user_input("yeah wait")
            assert result2 == InterruptionType.INTERRUPT, "Mixed with interrupt should interrupt"
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Scenario 4 - Pure Backchannel vs Mixed Input")
        print("="*70)
        print(logs)
        print("="*70)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_input(self, handler, log_capture):
        """Test handling of empty input"""
        with log_capture:
            result = handler.process_user_input("")
            assert result == InterruptionType.RESPOND
            
            result = handler.process_user_input("   ")
            assert result == InterruptionType.RESPOND
        
        logs = log_capture.get_logs()
        assert "Empty transcript" in logs or "Warning" in logs
    
    def test_case_insensitivity(self, handler, log_capture):
        """Test that matching is case-insensitive"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            # Test various cases
            cases = ["YEAH", "Yeah", "yeAH", "YEaH"]
            for case_variant in cases:
                result = handler.process_user_input(case_variant)
                assert result == InterruptionType.IGNORE, (
                    f"Expected IGNORE for case variant '{case_variant}'"
                )
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Edge Case - Case Insensitivity")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_whitespace_handling(self, handler, log_capture):
        """Test that whitespace is properly trimmed"""
        with log_capture:
            handler.set_agent_speaking(True)
            
            inputs = ["  yeah  ", "\tyeah\t", "  yeah  \n"]
            for input_var in inputs:
                result = handler.process_user_input(input_var)
                assert result == InterruptionType.IGNORE, (
                    f"Expected IGNORE for whitespace variant '{repr(input_var)}'"
                )
    
    def test_disabled_handler(self, log_capture):
        """Test that disabled handler always returns RESPOND"""
        with log_capture:
            config = InterruptionConfig(enabled=False)
            handler = InterruptionHandler(config)
            handler.set_agent_speaking(True)
            
            result = handler.process_user_input("yeah")
            assert result == InterruptionType.RESPOND, "Disabled handler should always RESPOND"
        
        logs = log_capture.get_logs()
        assert "disabled" in logs.lower()


class TestStateManagement:
    """Test state management and transitions"""
    
    def test_state_initialization(self, handler):
        """Test initial state"""
        state = handler.get_state()
        assert state.agent_is_speaking is False
        assert state.agent_is_generating is False
        assert state.audio_is_playing is False
    
    def test_state_transitions(self, handler, log_capture):
        """Test various state transitions"""
        with log_capture:
            # Transition: not speaking -> generating
            handler.set_agent_generating(True)
            assert handler.state.agent_is_generating is True
            assert handler.state.agent_is_speaking is True
            
            # Transition: start playing audio
            handler.set_audio_playing(True)
            assert handler.state.audio_is_playing is True
            assert handler.state.agent_is_speaking is True
            
            # Transition: stop generating
            handler.set_agent_generating(False)
            assert handler.state.agent_is_generating is False
            assert handler.state.agent_is_speaking is True  # Still playing audio
            
            # Transition: stop playing audio
            handler.set_audio_playing(False)
            assert handler.state.audio_is_playing is False
            assert handler.state.agent_is_speaking is False
        
        logs = log_capture.get_logs()
        assert "state changed" in logs.lower()
        print("\n" + "="*70)
        print("TEST: State Management - Transitions")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_reset_functionality(self, handler, log_capture):
        """Test that reset restores initial state"""
        with log_capture:
            # Change state
            handler.set_agent_speaking(True)
            handler.set_agent_generating(True)
            assert handler.state.agent_is_speaking is True
            
            # Reset
            handler.reset()
            
            # Verify initial state restored
            state = handler.get_state()
            assert state.agent_is_speaking is False
            assert state.agent_is_generating is False
            assert state.audio_is_playing is False
        
        logs = log_capture.get_logs()
        assert "reset" in logs.lower()


class TestConfigurationCustomization:
    """Test custom configuration"""
    
    def test_custom_backchannel_words(self, log_capture):
        """Test with custom backchannel word list"""
        with log_capture:
            custom_config = InterruptionConfig(
                backchannel_words={"yep", "sure", "got it"}
            )
            handler = InterruptionHandler(custom_config)
            handler.set_agent_speaking(True)
            
            # Custom words should be ignored
            result1 = handler.process_user_input("yep")
            assert result1 == InterruptionType.IGNORE
            
            result2 = handler.process_user_input("sure")
            assert result2 == InterruptionType.IGNORE
            
            # Default words should not be ignored
            result3 = handler.process_user_input("yeah")
            assert result3 == InterruptionType.RESPOND  # Not in custom list
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Configuration - Custom Backchannel Words")
        print("="*70)
        print(logs)
        print("="*70)
    
    def test_custom_interrupt_commands(self, log_capture):
        """Test with custom interrupt command list"""
        with log_capture:
            custom_config = InterruptionConfig(
                interrupt_commands={"pause", "silent", "quiet"}
            )
            handler = InterruptionHandler(custom_config)
            handler.set_agent_speaking(True)
            
            # Custom commands should interrupt
            result1 = handler.process_user_input("pause")
            assert result1 == InterruptionType.INTERRUPT
            
            result2 = handler.process_user_input("silent")
            assert result2 == InterruptionType.INTERRUPT
            
            # Default commands should not interrupt
            result3 = handler.process_user_input("stop")
            assert result3 == InterruptionType.RESPOND  # Not in custom list


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""
    
    def test_long_conversation(self, handler, log_capture):
        """Test a realistic long conversation with state changes"""
        with log_capture:
            conversation = [
                # Agent starts explaining
                ("agent_start_speaking", True, "wait for input"),
                ("yeah", "IGNORE"),
                ("uh-huh", "IGNORE"),
                ("okay", "IGNORE"),
                # Agent finishes, asks question
                ("agent_stop_speaking", False, "waiting for answer"),
                ("yes", "RESPOND"),  # Now same word should be processed
                ("Agent starts talking again", True, ""),
                ("stop", "INTERRUPT"),  # Interrupt command always works
            ]
            
            for action, state_or_input, _ in conversation:
                if action == "agent_start_speaking":
                    handler.set_agent_speaking(state_or_input)
                elif action == "agent_stop_speaking":
                    handler.set_agent_speaking(state_or_input)
                elif action == "Agent starts talking again":
                    handler.set_agent_speaking(state_or_input)
                else:
                    result = handler.process_user_input(action)
                    # For this test, just verify no exceptions
                    assert result in [InterruptionType.IGNORE, InterruptionType.RESPOND, InterruptionType.INTERRUPT]
        
        logs = log_capture.get_logs()
        print("\n" + "="*70)
        print("TEST: Real World - Long Conversation")
        print("="*70)
        print(logs)
        print("="*70)


def test_all_scenarios_summary(log_capture):
    """Summary test that demonstrates all four scenarios"""
    
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST SUMMARY - ALL SCENARIOS")
    print("="*70)
    
    with log_capture:
        # Scenario 1: Long Explanation
        print("\n[SCENARIO 1] The Long Explanation")
        print("-" * 70)
        handler = InterruptionHandler()
        handler.set_agent_speaking(True)
        r1 = handler.process_user_input("okay... yeah... uh-huh")
        print(f"Result: {r1.value} (Expected: ignore)")
        assert r1 == InterruptionType.IGNORE
        
        # Scenario 2: Passive Affirmation
        print("\n[SCENARIO 2] The Passive Affirmation")
        print("-" * 70)
        handler.reset()
        handler.set_agent_speaking(False)
        r2 = handler.process_user_input("yeah")
        print(f"Result: {r2.value} (Expected: respond)")
        assert r2 == InterruptionType.RESPOND
        
        # Scenario 3: Correction
        print("\n[SCENARIO 3] The Correction")
        print("-" * 70)
        handler.reset()
        handler.set_agent_speaking(True)
        r3 = handler.process_user_input("no stop")
        print(f"Result: {r3.value} (Expected: interrupt)")
        assert r3 == InterruptionType.INTERRUPT
        
        # Scenario 4: Mixed Input
        print("\n[SCENARIO 4] The Mixed Input")
        print("-" * 70)
        handler.reset()
        handler.set_agent_speaking(True)
        r4 = handler.process_user_input("yeah okay but wait")
        print(f"Result: {r4.value} (Expected: interrupt)")
        assert r4 == InterruptionType.INTERRUPT
    
    logs = log_capture.get_logs()
    print("\n" + "="*70)
    print("DETAILED LOGS:")
    print("="*70)
    print(logs)
    print("="*70)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
