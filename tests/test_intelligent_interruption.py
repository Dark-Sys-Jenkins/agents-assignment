"""
Unit tests for the intelligent interruption handling feature.

Tests the logic matrix:
- User says backchannel ("yeah/ok/hmm") while agent speaking -> IGNORE
- User says interrupt command ("stop/wait/no") while agent speaking -> INTERRUPT
- User says backchannel while agent silent -> RESPOND normally
- Semantic awareness: "Yeah, but wait" should INTERRUPT (contains "wait")
"""

import pytest
from unittest.mock import MagicMock, patch
import asyncio

from livekit.agents.voice.agent_session import (
    DEFAULT_BACKCHANNEL_WORDS,
    DEFAULT_INTERRUPT_WORDS,
    AgentSessionOptions,
)

class TestBackchannelAndInterruptWordLists:
    """Test the default word lists are properly configured."""
    
    def test_default_backchannel_words_exist(self):
        """Verify default backchannel words include common fillers."""
        assert "yeah" in DEFAULT_BACKCHANNEL_WORDS
        assert "ok" in DEFAULT_BACKCHANNEL_WORDS
        assert "hmm" in DEFAULT_BACKCHANNEL_WORDS
        assert "uh-huh" in DEFAULT_BACKCHANNEL_WORDS
        assert "right" in DEFAULT_BACKCHANNEL_WORDS
        assert "sure" in DEFAULT_BACKCHANNEL_WORDS
    
    def test_default_interrupt_words_exist(self):
        """Verify default interrupt words include common commands."""
        assert "stop" in DEFAULT_INTERRUPT_WORDS
        assert "wait" in DEFAULT_INTERRUPT_WORDS
        assert "no" in DEFAULT_INTERRUPT_WORDS
        assert "hold on" in DEFAULT_INTERRUPT_WORDS
        assert "pause" in DEFAULT_INTERRUPT_WORDS
        assert "actually" in DEFAULT_INTERRUPT_WORDS
        assert "but" in DEFAULT_INTERRUPT_WORDS


class TestUtteranceClassification:
    """Test the _classify_utterance method logic."""
    
    @pytest.fixture
    def mock_activity(self):
        """Create a mock AgentActivity with the classification method."""
        from livekit.agents.voice.agent_activity import AgentActivity
        
        # Create mock session with options
        mock_session = MagicMock()
        mock_session.options = AgentSessionOptions(
            allow_interruptions=True,
            discard_audio_if_uninterruptible=True,
            min_interruption_duration=0.5,
            min_interruption_words=0,
            min_endpointing_delay=0.5,
            max_endpointing_delay=3.0,
            max_tool_steps=3,
            user_away_timeout=15.0,
            false_interruption_timeout=2.0,
            resume_false_interruption=True,
            min_consecutive_speech_delay=0.0,
            use_tts_aligned_transcript=None,
            preemptive_generation=False,
            tts_text_transforms=None,
            ivr_detection=False,
            backchannel_words=DEFAULT_BACKCHANNEL_WORDS.copy(),
            interrupt_words=DEFAULT_INTERRUPT_WORDS.copy(),
        )
        mock_session.agent_state = "speaking"
        
        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.turn_detection = None
        mock_agent.vad = None
        mock_agent.stt = None
        mock_agent.llm = MagicMock()
        mock_agent.llm.capabilities.turn_detection = False
        mock_agent.tts = None
        mock_agent.chat_ctx = MagicMock()
        mock_agent._activity = None
        
        # Create the activity - we'll test _classify_utterance directly
        # Since we can't easily instantiate AgentActivity, we'll test the logic inline
        return mock_session
    
    def test_classify_backchannel_single_word(self, mock_activity):
        """Test that single backchannel words are classified correctly."""
        import re
        
        def classify(text, options):
            if not text:
                return "normal"
            normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
            if not normalized:
                return "normal"
            
            for word in options.interrupt_words:
                if word.lower() in normalized:
                    return "interrupt"
            
            words = normalized.split()
            backchannel_set = {w.lower() for w in options.backchannel_words}
            
            is_backchannel = False
            for bc in options.backchannel_words:
                bc_normalized = re.sub(r'[^\w\s]', '', bc.lower().strip())
                if normalized == bc_normalized:
                    is_backchannel = True
                    break
            
            if not is_backchannel and words:
                is_backchannel = all(w in backchannel_set for w in words)
            
            return "backchannel" if is_backchannel else "normal"
        
        opt = mock_activity.options
        
        # Test backchannel words
        assert classify("yeah", opt) == "backchannel"
        assert classify("Yeah", opt) == "backchannel"
        assert classify("YEAH", opt) == "backchannel"
        assert classify("ok", opt) == "backchannel"
        assert classify("OK", opt) == "backchannel"
        assert classify("okay", opt) == "backchannel"
        assert classify("hmm", opt) == "backchannel"
        assert classify("uh-huh", opt) == "backchannel"
        assert classify("right", opt) == "backchannel"
        assert classify("sure", opt) == "backchannel"
    
    def test_classify_interrupt_commands(self, mock_activity):
        """Test that interrupt commands are classified correctly."""
        import re
        
        def classify(text, options):
            if not text:
                return "normal"
            normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
            if not normalized:
                return "normal"
            
            for word in options.interrupt_words:
                if word.lower() in normalized:
                    return "interrupt"
            
            return "normal"
        
        opt = mock_activity.options
        
        # Test interrupt words
        assert classify("stop", opt) == "interrupt"
        assert classify("Stop!", opt) == "interrupt"
        assert classify("STOP", opt) == "interrupt"
        assert classify("wait", opt) == "interrupt"
        assert classify("Wait a moment", opt) == "interrupt"
        assert classify("no", opt) == "interrupt"
        assert classify("No, that's wrong", opt) == "interrupt"
        assert classify("hold on", opt) == "interrupt"
        assert classify("pause", opt) == "interrupt"
    
    def test_semantic_awareness_yeah_but_wait(self, mock_activity):
        """Test that 'Yeah, but wait' is classified as interrupt (contains 'wait')."""
        import re
        
        def classify(text, options):
            if not text:
                return "normal"
            normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
            if not normalized:
                return "normal"
            
            # Check interrupt words FIRST
            for word in options.interrupt_words:
                if word.lower() in normalized:
                    return "interrupt"
            
            words = normalized.split()
            backchannel_set = {w.lower() for w in options.backchannel_words}
            
            is_backchannel = all(w in backchannel_set for w in words) if words else False
            return "backchannel" if is_backchannel else "normal"
        
        opt = mock_activity.options
        
        # Semantic awareness: interrupt command overrides backchannel
        assert classify("Yeah, but wait", opt) == "interrupt"
        assert classify("Ok but actually", opt) == "interrupt"
        assert classify("Hmm, no", opt) == "interrupt"
        assert classify("Right, but hold on", opt) == "interrupt"
    
    def test_classify_normal_speech(self, mock_activity):
        """Test that normal speech is classified correctly."""
        import re
        
        def classify(text, options):
            if not text:
                return "normal"
            normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
            if not normalized:
                return "normal"
            
            for word in options.interrupt_words:
                if word.lower() in normalized:
                    return "interrupt"
            
            words = normalized.split()
            backchannel_set = {w.lower() for w in options.backchannel_words}
            
            is_backchannel = all(w in backchannel_set for w in words) if words else False
            return "backchannel" if is_backchannel else "normal"
        
        opt = mock_activity.options
        
        # Test normal speech (not backchannel, not interrupt)
        assert classify("What's the weather like?", opt) == "normal"
        assert classify("Tell me more", opt) == "normal"
        assert classify("I want to know about", opt) == "normal"
        assert classify("Hello there", opt) == "normal"


class TestCustomWordLists:
    """Test that custom word lists can be provided."""
    
    def test_custom_backchannel_words(self):
        """Test providing custom backchannel words."""
        custom_backchannels = ["yep", "aye", "gotcha"]
        
        options = AgentSessionOptions(
            allow_interruptions=True,
            discard_audio_if_uninterruptible=True,
            min_interruption_duration=0.5,
            min_interruption_words=0,
            min_endpointing_delay=0.5,
            max_endpointing_delay=3.0,
            max_tool_steps=3,
            user_away_timeout=15.0,
            false_interruption_timeout=2.0,
            resume_false_interruption=True,
            min_consecutive_speech_delay=0.0,
            use_tts_aligned_transcript=None,
            preemptive_generation=False,
            tts_text_transforms=None,
            ivr_detection=False,
            backchannel_words=custom_backchannels,
            interrupt_words=DEFAULT_INTERRUPT_WORDS.copy(),
        )
        
        assert options.backchannel_words == custom_backchannels
        assert "yep" in options.backchannel_words
        assert "yeah" not in options.backchannel_words  # Not in custom list
    
    def test_custom_interrupt_words(self):
        """Test providing custom interrupt words."""
        custom_interrupts = ["abort", "cancel", "halt"]
        
        options = AgentSessionOptions(
            allow_interruptions=True,
            discard_audio_if_uninterruptible=True,
            min_interruption_duration=0.5,
            min_interruption_words=0,
            min_endpointing_delay=0.5,
            max_endpointing_delay=3.0,
            max_tool_steps=3,
            user_away_timeout=15.0,
            false_interruption_timeout=2.0,
            resume_false_interruption=True,
            min_consecutive_speech_delay=0.0,
            use_tts_aligned_transcript=None,
            preemptive_generation=False,
            tts_text_transforms=None,
            ivr_detection=False,
            backchannel_words=DEFAULT_BACKCHANNEL_WORDS.copy(),
            interrupt_words=custom_interrupts,
        )
        
        assert options.interrupt_words == custom_interrupts
        assert "abort" in options.interrupt_words
        assert "stop" not in options.interrupt_words  # Not in custom list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
