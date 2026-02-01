"""
Test Suite for Intelligent Interruption Handler

Run with: python -m pytest test_interruption_handler.py -v
"""

import pytest
import asyncio
from intelligent_interrupt_handler import IntelligentInterruptionHandler, InterruptionConfig


class TestInterruptionHandler:
    """Test cases for the Intelligent Interruption Handler"""
    
    @pytest.fixture
    def handler(self):
        """Create a handler instance for testing"""
        config = InterruptionConfig(
            ignore_words={'yeah', 'ok', 'hmm', 'uh-huh', 'right'},
            interrupt_words={'wait', 'stop', 'no', 'hold on'}
        )
        return IntelligentInterruptionHandler(config=config)
    
    # ========== SCENARIO 1: Long Explanation Test ==========
    @pytest.mark.asyncio
    async def test_backchannel_during_agent_speech(self, handler):
        """
        SCENARIO 1: The Long Explanation
        User says backchannels while agent is talking - should be IGNORED
        """
        handler.set_agent_speaking_state(True)
        
        # Test single backchannels
        assert not await handler.should_interrupt("yeah", is_final=True)
        assert not await handler.should_interrupt("okay", is_final=True)
        assert not await handler.should_interrupt("uh-huh", is_final=True)
        assert not await handler.should_interrupt("hmm", is_final=True)
        assert not await handler.should_interrupt("right", is_final=True)
        
        # Test multiple backchannels together
        assert not await handler.should_interrupt("yeah okay", is_final=True)
        assert not await handler.should_interrupt("hmm right", is_final=True)
    
    # ========== SCENARIO 2: Passive Affirmation Test ==========
    @pytest.mark.asyncio
    async def test_backchannel_when_agent_silent(self, handler):
        """
        SCENARIO 2: The Passive Affirmation
        User says "yeah" when agent is silent - should be RESPONDED to
        """
        handler.set_agent_speaking_state(False)
        
        # All backchannels should be processed when agent is silent
        assert await handler.should_interrupt("yeah", is_final=True)
        assert await handler.should_interrupt("okay", is_final=True)
        assert await handler.should_interrupt("hmm", is_final=True)
        assert await handler.should_interrupt("right", is_final=True)
    
    # ========== SCENARIO 3: The Correction Test ==========
    @pytest.mark.asyncio
    async def test_interrupt_during_agent_speech(self, handler):
        """
        SCENARIO 3: The Correction
        User says interrupt words while agent is talking - should INTERRUPT
        """
        handler.set_agent_speaking_state(True)
        
        # Test interrupt words
        assert await handler.should_interrupt("stop", is_final=True)
        assert await handler.should_interrupt("wait", is_final=True)
        assert await handler.should_interrupt("no", is_final=True)
        assert await handler.should_interrupt("hold on", is_final=True)
        
        # Test with punctuation
        assert await handler.should_interrupt("no!", is_final=True)
        assert await handler.should_interrupt("wait.", is_final=True)
    
    # ========== SCENARIO 4: Mixed Input Test ==========
    @pytest.mark.asyncio
    async def test_mixed_backchannel_and_interrupt(self, handler):
        """
        SCENARIO 4: The Mixed Input
        User says "yeah okay but wait" - should INTERRUPT (contains interrupt word)
        """
        handler.set_agent_speaking_state(True)
        
        # Mixed inputs containing interrupt words should interrupt
        assert await handler.should_interrupt("yeah but wait", is_final=True)
        assert await handler.should_interrupt("okay wait", is_final=True)
        assert await handler.should_interrupt("hmm no", is_final=True)
        assert await handler.should_interrupt("yeah okay but stop", is_final=True)
    
    # ========== Additional Edge Cases ==========
    @pytest.mark.asyncio
    async def test_non_final_transcriptions_ignored(self, handler):
        """Non-final transcriptions should not trigger interruptions"""
        handler.set_agent_speaking_state(True)
        
        # Non-final transcriptions should be ignored
        assert not await handler.should_interrupt("stop", is_final=False)
        assert not await handler.should_interrupt("wait", is_final=False)
    
    @pytest.mark.asyncio
    async def test_low_confidence_ignored(self, handler):
        """Low confidence transcriptions should be ignored"""
        handler.set_agent_speaking_state(True)
        
        # Low confidence should be ignored
        assert not await handler.should_interrupt("stop", is_final=True, confidence=0.3)
    
    @pytest.mark.asyncio
    async def test_regular_speech_during_agent_speaking(self, handler):
        """Regular speech during agent speaking should interrupt"""
        handler.set_agent_speaking_state(True)
        
        # Regular speech should interrupt
        assert await handler.should_interrupt("what about the weather", is_final=True)
        assert await handler.should_interrupt("can you help me", is_final=True)
    
    @pytest.mark.asyncio
    async def test_case_insensitive(self, handler):
        """Handler should be case-insensitive"""
        handler.set_agent_speaking_state(True)
        
        # Case variations should work
        assert not await handler.should_interrupt("Yeah", is_final=True)
        assert not await handler.should_interrupt("OKAY", is_final=True)
        assert await handler.should_interrupt("WAIT", is_final=True)
        assert await handler.should_interrupt("Stop", is_final=True)
    
    @pytest.mark.asyncio
    async def test_state_transitions(self, handler):
        """Test state transitions between speaking and silent"""
        # Agent silent -> backchannel should process
        handler.set_agent_speaking_state(False)
        assert await handler.should_interrupt("yeah", is_final=True)
        
        # Agent starts speaking -> same backchannel should be ignored
        handler.set_agent_speaking_state(True)
        assert not await handler.should_interrupt("yeah", is_final=True)
        
        # Agent stops speaking -> backchannel should process again
        handler.set_agent_speaking_state(False)
        assert await handler.should_interrupt("yeah", is_final=True)
    
    @pytest.mark.asyncio
    async def test_configuration_update(self, handler):
        """Test dynamic configuration updates"""
        handler.set_agent_speaking_state(True)
        
        # Initially "cool" is not an ignore word
        assert await handler.should_interrupt("cool", is_final=True)
        
        # Add "cool" to ignore words
        handler.update_config(ignore_words={'yeah', 'ok', 'hmm', 'cool'})
        
        # Now "cool" should be ignored
        assert not await handler.should_interrupt("cool", is_final=True)


# Integration test scenarios
class TestIntegrationScenarios:
    """Test real-world conversation scenarios"""
    
    @pytest.fixture
    def handler(self):
        config = InterruptionConfig()
        return IntelligentInterruptionHandler(config=config)
    
    @pytest.mark.asyncio
    async def test_long_explanation_scenario(self, handler):
        """
        Simulate: Agent explaining history while user gives feedback
        """
        handler.set_agent_speaking_state(True)
        
        # User provides continuous feedback while listening
        backchannels = ["okay", "yeah", "uh-huh", "right", "hmm okay"]
        
        for backchannel in backchannels:
            should_int = await handler.should_interrupt(backchannel, is_final=True)
            assert not should_int, f"Failed on: {backchannel}"
    
    @pytest.mark.asyncio
    async def test_question_answer_scenario(self, handler):
        """
        Simulate: Agent asks question, user responds with "yeah"
        """
        # Agent asks "Are you ready?"
        handler.set_agent_speaking_state(True)
        # ... agent finishes asking
        handler.set_agent_speaking_state(False)
        
        # User responds "Yeah"
        should_interrupt = await handler.should_interrupt("yeah", is_final=True)
        assert should_interrupt  # Should be processed as an answer
    
    @pytest.mark.asyncio
    async def test_correction_scenario(self, handler):
        """
        Simulate: Agent counting, user interrupts to correct
        """
        handler.set_agent_speaking_state(True)
        
        # Agent is counting "One, two, three..."
        # User says "No stop"
        should_interrupt = await handler.should_interrupt("no stop", is_final=True)
        assert should_interrupt  # Should interrupt immediately


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])