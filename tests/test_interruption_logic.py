
import unittest
from livekit.agents.voice.interruption_filter import InterruptionFilter, InterruptionFilterConfig

class TestInterruptionFilter(unittest.TestCase):
    def setUp(self):
        self.default_filter = InterruptionFilter()

    def test_ignore_backchanneling_while_speaking(self):
        """Scenario 1: Agent speaking, user says 'yeah' -> IGNORE"""
        decision = self.default_filter.analyze("yeah", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore")
        
        decision = self.default_filter.analyze("ok", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore")
        
        decision = self.default_filter.analyze("uh-huh", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore")

    def test_respond_to_backchanneling_while_silent(self):
        """Scenario 2: Agent silent, user says 'yeah' -> RESPOND"""
        decision = self.default_filter.analyze("yeah", agent_is_speaking=False)
        self.assertEqual(decision.action, "respond")

    def test_interrupt_on_stop_command(self):
        """Scenario 3: Agent speaking, user says 'stop' -> INTERRUPT"""
        decision = self.default_filter.analyze("stop", agent_is_speaking=True)
        self.assertEqual(decision.action, "interrupt")
        
        decision = self.default_filter.analyze("no wait", agent_is_speaking=True)
        self.assertEqual(decision.action, "interrupt")

    def test_interrupt_on_mixed_input(self):
        """Scenario 4: Agent speaking, user says 'yeah but wait' -> INTERRUPT"""
        decision = self.default_filter.analyze("yeah but wait", agent_is_speaking=True)
        self.assertEqual(decision.action, "interrupt")

    def test_custom_config_normalization(self):
        """Test with custom config that has mixed case words."""
        # This mirrors the failure case I found in the scratch script
        custom_backchannel = frozenset(["YeH", "OK"])
        custom_interrupt = frozenset(["WaIT"])
        
        config = InterruptionFilterConfig(
            backchanneling_words=custom_backchannel,
            interrupt_keywords=custom_interrupt,
            enabled=True
        )
        f = InterruptionFilter(config)

        # Should match case-insensitively
        decision = f.analyze("yeh", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore", "Failed to normalize custom backchannel word 'YeH' -> 'yeh'")
        
        decision = f.analyze("wait", agent_is_speaking=True)
        self.assertEqual(decision.action, "interrupt", "Failed to normalize custom interrupt word 'WaIT' -> 'wait'")

    def test_max_backchanneling_words(self):
        """Test threshold for max words."""
        # Default is 3 words
        
        # 3 words -> Ignore
        decision = self.default_filter.analyze("yeah ok cool", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore")
        
        # 4 words -> Interrupt (treated as real input)
        decision = self.default_filter.analyze("yeah ok cool right", agent_is_speaking=True)
        self.assertEqual(decision.action, "interrupt")

    def test_empty_transcript(self):
        decision = self.default_filter.analyze("", agent_is_speaking=True)
        self.assertEqual(decision.action, "ignore")

if __name__ == '__main__':
    unittest.main()
