"""
Unit tests for InterruptionController

Run with: pytest test_controller.py -v
"""

import pytest
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from salescode_interrupt_handler.controllers import Decision, InterruptionController

class TestInterruptionController:
    """Test suite for InterruptionController logic."""
    
    def setup_method(self):
        """Create a fresh controller before each test."""
        self.controller = InterruptionController()
    
    # ============================================================
    # SCENARIO 1: Backchanneling while agent is speaking
    # ============================================================
    
    def test_ignore_single_filler_while_speaking(self):
        """Agent speaking + 'yeah' → IGNORE"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("yeah", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_ignore_multiple_fillers_while_speaking(self):
        """Agent speaking + 'yeah ok hmm' → IGNORE"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("yeah ok hmm", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_ignore_variations_while_speaking(self):
        """Test various filler word variations"""
        self.controller.update_agent_state('speaking')
        
        fillers = ["ok", "okay", "mhm", "uh-huh", "right", "got it", "cool"]
        for filler in fillers:
            decision = self.controller.decide(filler, is_final=True)
            assert decision == Decision.IGNORE, f"Failed for: {filler}"
    
    # ============================================================
    # SCENARIO 2: Commands while agent is speaking
    # ============================================================
    
    def test_interrupt_on_stop_command(self):
        """Agent speaking + 'stop' → INTERRUPT"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("stop", is_final=True)
        assert decision == Decision.INTERRUPT
    
    def test_interrupt_on_wait_command(self):
        """Agent speaking + 'wait' → INTERRUPT"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("wait", is_final=True)
        assert decision == Decision.INTERRUPT
    
    def test_interrupt_on_mixed_filler_with_command(self):
        """Agent speaking + 'yeah wait' → INTERRUPT"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("yeah wait", is_final=True)
        assert decision == Decision.INTERRUPT
    
    def test_interrupt_on_all_commands(self):
        """Test all interrupt words trigger interruption"""
        self.controller.update_agent_state('speaking')
        
        commands = ["stop", "wait", "no", "pause", "hold", "but", "actually"]
        for command in commands:
            decision = self.controller.decide(command, is_final=True)
            assert decision == Decision.INTERRUPT, f"Failed for: {command}"
    
    # ============================================================
    # SCENARIO 3: Unknown words while agent is speaking
    # ============================================================
    
    def test_interrupt_on_unknown_words(self):
        """Agent speaking + 'yeah interesting' → INTERRUPT (unknown word)"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("yeah interesting", is_final=True)
        assert decision == Decision.INTERRUPT
    
    def test_interrupt_on_real_input(self):
        """Agent speaking + 'tell me more' → INTERRUPT"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("tell me more", is_final=True)
        assert decision == Decision.INTERRUPT
    
    # ============================================================
    # SCENARIO 4: Agent is silent (normal conversation)
    # ============================================================
    
    def test_no_decision_when_silent_filler(self):
        """Agent silent + 'yeah' → NO_DECISION"""
        self.controller.update_agent_state('listening')
        decision = self.controller.decide("yeah", is_final=True)
        assert decision == Decision.NO_DECISION
    
    def test_no_decision_when_silent_normal_input(self):
        """Agent silent + 'hello' → NO_DECISION"""
        self.controller.update_agent_state('listening')
        decision = self.controller.decide("hello", is_final=True)
        assert decision == Decision.NO_DECISION
    
    def test_interrupt_command_when_silent(self):
        """Agent silent + 'stop' → INTERRUPT (always interrupt on commands)"""
        self.controller.update_agent_state('listening')
        decision = self.controller.decide("stop", is_final=True)
        assert decision == Decision.INTERRUPT
    
    # ============================================================
    # EDGE CASES
    # ============================================================
    
    def test_empty_transcript(self):
        """Empty transcript → IGNORE"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_whitespace_only_transcript(self):
        """Whitespace only → IGNORE"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("   ", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_normalization_handles_hyphens(self):
        """'uh-huh' should normalize to 'uh huh' and be recognized"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("uh-huh", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_normalization_handles_punctuation(self):
        """'yeah!' should normalize to 'yeah'"""
        self.controller.update_agent_state('speaking')
        decision = self.controller.decide("yeah!", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_case_insensitive(self):
        """'YEAH' and 'Yeah' should be treated same as 'yeah'"""
        self.controller.update_agent_state('speaking')
        
        variations = ["YEAH", "Yeah", "YeAh", "yEaH"]
        for variation in variations:
            decision = self.controller.decide(variation, is_final=True)
            assert decision == Decision.IGNORE, f"Failed for: {variation}"
    
    # ============================================================
    # GRACE PERIOD TESTS
    # ============================================================
    
    def test_grace_period_after_speaking(self):
        """Transcript arriving shortly after speaking should be treated as 'speaking'"""
        # Agent speaks
        self.controller.update_agent_state('speaking')
        
        # Agent stops speaking
        self.controller.update_agent_state('listening')
        
        # User says "yeah" 200ms later (within grace period)
        time.sleep(0.2)
        decision = self.controller.decide("yeah", is_final=True)
        
        # Should still be treated as if agent was speaking
        assert decision == Decision.IGNORE
    
    def test_grace_period_expires(self):
        """Transcript after grace period should not be treated as 'speaking'"""
        # Agent speaks
        self.controller.update_agent_state('speaking')
        
        # Agent stops speaking
        self.controller.update_agent_state('listening')
        
        # Wait for grace period to expire (500ms + buffer)
        time.sleep(0.6)
        
        # User says "yeah"
        decision = self.controller.decide("yeah", is_final=True)
        
        # Should be treated as normal input (agent is silent)
        assert decision == Decision.NO_DECISION
    
    # ============================================================
    # WORD LIST MANAGEMENT
    # ============================================================
    
    def test_add_custom_ignore_word(self):
        """Custom ignore words should work"""
        self.controller.add_ignore_word("totally")
        self.controller.update_agent_state('speaking')
        
        decision = self.controller.decide("totally", is_final=True)
        assert decision == Decision.IGNORE
    
    def test_add_custom_interrupt_word(self):
        """Custom interrupt words should work"""
        self.controller.add_interrupt_word("cancel")
        self.controller.update_agent_state('speaking')
        
        decision = self.controller.decide("cancel", is_final=True)
        assert decision == Decision.INTERRUPT
    
    def test_remove_ignore_word(self):
        """Removing an ignore word should make it trigger interruption"""
        self.controller.remove_ignore_word("cool")
        self.controller.update_agent_state('speaking')
        
        # "cool" no longer in ignore list, so should interrupt
        decision = self.controller.decide("cool", is_final=True)
        assert decision == Decision.INTERRUPT
    
    # ============================================================
    # COMPLEX SCENARIOS
    # ============================================================
    
    def test_scenario_1_long_explanation(self):
        """Scenario 1: User says backchannels during long explanation"""
        self.controller.update_agent_state('speaking')
        
        # Simulate user saying multiple backchannels
        assert self.controller.decide("okay", is_final=True) == Decision.IGNORE
        assert self.controller.decide("yeah", is_final=True) == Decision.IGNORE
        assert self.controller.decide("uh huh", is_final=True) == Decision.IGNORE
    
    def test_scenario_2_passive_affirmation(self):
        """Scenario 2: Agent asks question, user says 'yeah'"""
        # Agent asks "Are you ready?"
        self.controller.update_agent_state('speaking')
        # Agent finishes and goes silent
        self.controller.update_agent_state('listening')
        
        # User says "yeah"
        decision = self.controller.decide("yeah", is_final=True)
        
        # Should be processed as normal answer
        assert decision == Decision.NO_DECISION
    
    def test_scenario_3_correction(self):
        """Scenario 3: Agent counting, user says 'no stop'"""
        self.controller.update_agent_state('speaking')
        
        # User interrupts
        decision = self.controller.decide("no stop", is_final=True)
        
        # Agent should stop immediately
        assert decision == Decision.INTERRUPT
    
    def test_scenario_4_mixed_input(self):
        """Scenario 4: User says 'yeah okay but wait'"""
        self.controller.update_agent_state('speaking')
        
        decision = self.controller.decide("yeah okay but wait", is_final=True)
        
        # Should interrupt (contains 'but' and 'wait')
        assert decision == Decision.INTERRUPT
    
    # ============================================================
    # STATISTICS
    # ============================================================
    
    def test_get_stats(self):
        """Stats should return correct information"""
        stats = self.controller.get_stats()
        
        assert 'current_state' in stats
        assert 'ignore_words_count' in stats
        assert 'interrupt_words_count' in stats
        assert stats['ignore_words_count'] > 0
        assert stats['interrupt_words_count'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])