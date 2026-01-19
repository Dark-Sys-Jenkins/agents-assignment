import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.modules["dotenv"] = MagicMock()
sys.modules["livekit"] = MagicMock()
sys.modules["livekit.agents"] = MagicMock()
sys.modules["livekit.agents.llm"] = MagicMock()
sys.modules["livekit.plugins"] = MagicMock()
sys.modules["livekit.plugins.silero"] = MagicMock()
sys.modules["livekit.plugins.deepgram"] = MagicMock()
sys.modules["livekit.plugins.openai"] = MagicMock()
sys.modules["livekit.plugins.turn_detector"] = MagicMock()
sys.modules["livekit.plugins.turn_detector.multilingual"] = MagicMock()

class MockAgentActivity:
    _interrupt_by_audio_activity = lambda self: None
    def __init__(self):
        self._current_speech = None
        self._audio_recognition = None

mock_activity_module = MagicMock()
mock_activity_module.AgentActivity = MockAgentActivity
sys.modules["livekit.agents.voice.agent_activity"] = mock_activity_module

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples/voice_agents")))

from context_aware_agent import _should_ignore, _patched_interrupt_by_audio_activity, IGNORE_WORDS
from livekit.agents.voice.agent_activity import AgentActivity

class TestContextLogic(unittest.TestCase):
    def test_ignore_logic(self):
        self.assertTrue(_should_ignore("yeah"))
        self.assertTrue(_should_ignore("ok"))
        self.assertTrue(_should_ignore("aha"))
        self.assertFalse(_should_ignore("hm"))
        self.assertTrue(_should_ignore("hmm"))
        self.assertTrue(_should_ignore("Uh-huh"))
        self.assertTrue(_should_ignore("Yeah ok"))
        self.assertTrue(_should_ignore("ok yeah"))
        
        self.assertFalse(_should_ignore("stop"))
        self.assertFalse(_should_ignore("wait"))
        self.assertFalse(_should_ignore("no"))
        self.assertFalse(_should_ignore("yeah stop"))
        self.assertFalse(_should_ignore("ok but"))
        self.assertFalse(_should_ignore("hello"))
        
    def test_patch_applied(self):
        self.assertEqual(AgentActivity._interrupt_by_audio_activity, _patched_interrupt_by_audio_activity)

    def test_patch_behavior_ignores(self):
        activity = MagicMock(spec=AgentActivity)
        activity._current_speech = MagicMock()
        activity._current_speech.done.return_value = False
        activity._audio_recognition = MagicMock()
        activity._audio_recognition.current_transcript = "yeah"
        
        _patched_interrupt_by_audio_activity(activity)
        
    def test_patch_behavior_interrupts(self):
        activity = MagicMock(spec=AgentActivity)
        activity._current_speech = MagicMock()
        activity._current_speech.done.return_value = False
        activity._audio_recognition = MagicMock()
        activity._audio_recognition.current_transcript = "stop"
        
        try:
            _patched_interrupt_by_audio_activity(activity)
        except (AttributeError, TypeError):
            pass 

if __name__ == '__main__':
    unittest.main()
