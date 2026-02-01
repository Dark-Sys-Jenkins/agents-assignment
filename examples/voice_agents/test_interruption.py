import unittest
import logging
from unittest.mock import MagicMock
import sys
import os

# Add the current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock necessary livekit modules before importing intelligent_agent
sys.modules["livekit"] = MagicMock()
sys.modules["livekit.agents"] = MagicMock()
sys.modules["livekit.agents.voice"] = MagicMock()
sys.modules["livekit.agents.cli"] = MagicMock()
sys.modules["livekit.agents.tokenize"] = MagicMock()


# Setup AgentActivity mock
agent_activity = MagicMock()
class MockAgentActivity:
    def _interrupt_by_audio_activity(self):
        pass
    def on_end_of_turn(self, info):
        pass

agent_activity.AgentActivity = MockAgentActivity
sys.modules["livekit.agents.voice.agent_activity"] = agent_activity

# Correct import for basic_agent (mocking it)
sys.modules["examples.voice_agents.basic_agent"] = MagicMock()
sys.modules["basic_agent"] = MagicMock()

# Now import the module under test
import intelligent_agent

class TestInterruptionLogic(unittest.TestCase):
    def test_ignore_list_logic(self):
        """Test the _should_ignore_interruption function directly."""
        # Allowed words: "yeah", "ok", "okay", "hmm", "hm", "right", "sure", "uh-huh"
        
        # Should Ignore
        self.assertTrue(intelligent_agent._should_ignore_interruption("yeah"))
        self.assertTrue(intelligent_agent._should_ignore_interruption("Okay"))
        self.assertTrue(intelligent_agent._should_ignore_interruption("hmm sure"))
        self.assertTrue(intelligent_agent._should_ignore_interruption("right yeah"))
        
        # Should NOT Ignore (Interruption)
        self.assertFalse(intelligent_agent._should_ignore_interruption("stop"))
        self.assertFalse(intelligent_agent._should_ignore_interruption("wait"))
        self.assertFalse(intelligent_agent._should_ignore_interruption("yeah check this"))
        self.assertFalse(intelligent_agent._should_ignore_interruption("okay but"))
        self.assertFalse(intelligent_agent._should_ignore_interruption(""))

    def test_patch_application(self):
        """Verify that the AgentActivity methods were patched."""
        # The patching modifies the class in place, so we check if it matches the patched function
        self.assertEqual(
            agent_activity.AgentActivity._interrupt_by_audio_activity,
            intelligent_agent.patched_interrupt_by_audio_activity,
            "AgentActivity._interrupt_by_audio_activity should be the patched function"
        )
        self.assertEqual(
            agent_activity.AgentActivity.on_end_of_turn,
            intelligent_agent.patched_on_end_of_turn,
            "AgentActivity.on_end_of_turn should be the patched function"
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
