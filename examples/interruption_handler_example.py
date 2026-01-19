"""
Example: Intelligent Interruption Handler Integration with LiveKit Agents

This example demonstrates how to integrate the InterruptionHandler into a real LiveKit agent.

Usage:
    python examples/interruption_handler_example.py

The agent will:
1. Acknowledge backchhannel words ("yeah", "ok") only when it's NOT speaking
2. Immediately stop for interrupt commands ("wait", "stop")
3. Continue normally when no special input is detected
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import interruption_handler
sys.path.insert(0, str(Path(__file__).parent.parent))

from interruption_handler import InterruptionHandler, InterruptionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("agent_interruption.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


class ConversationalAgent:
    """Example agent with intelligent interruption handling"""
    
    def __init__(self):
        self.handler = InterruptionHandler()
        self.conversation_log = []
        
        # Register callbacks
        self.handler.register_interrupt_callback(self._on_interrupt)
        
        logger.info("Agent initialized with interruption handler")
    
    def _on_interrupt(self, transcript: str):
        """Callback when user interrupts"""
        logger.warning(f"User interrupted: '{transcript}'")
        self.conversation_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "interrupt",
            "content": transcript,
        })
    
    def start_explaining(self, topic: str):
        """Agent starts explaining something"""
        logger.info(f"Agent starting explanation on: {topic}")
        self.handler.set_agent_speaking(True)
        self.conversation_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "agent_speaking",
            "content": f"Started explaining: {topic}",
        })
    
    def stop_explaining(self):
        """Agent finishes explaining"""
        logger.info("Agent stopped speaking")
        self.handler.set_agent_speaking(False)
        self.conversation_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "agent_silent",
            "content": "Stopped speaking",
        })
    
    def process_user_speech(self, transcript: str) -> dict:
        """Process user speech and return action"""
        logger.info(f"Processing user speech: '{transcript}'")
        
        # Use handle_interruption which executes callbacks and returns interrupt status
        will_interrupt = self.handler.handle_interruption(transcript)
        
        interruption_type = self.handler.process_user_input(transcript)
        
        action = {
            "timestamp": datetime.now().isoformat(),
            "user_input": transcript,
            "interruption_type": interruption_type.value,
            "will_interrupt": will_interrupt,
            "agent_was_speaking": self.handler.state.agent_is_speaking,
        }
        
        self.conversation_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "user_speech",
            "content": transcript,
            "action": interruption_type.value,
        })
        
        logger.info(f"Action: {interruption_type.value} (interrupt={will_interrupt})")
        
        return action
    
    def get_conversation_log(self) -> list:
        """Get the conversation log"""
        return self.conversation_log
    
    def reset(self):
        """Reset agent state"""
        self.handler.reset()
        logger.info("Agent reset")


def run_scenario(name: str, scenario_fn):
    """Run a test scenario"""
    print("\n" + "=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)
    
    agent = ConversationalAgent()
    scenario_fn(agent)
    
    # Print conversation log
    print("\nConversation Log:")
    print("-" * 80)
    for entry in agent.get_conversation_log():
        print(f"[{entry['timestamp']}] {entry['type']:20s} | {entry['content']}")
    
    return agent


def scenario_1_long_explanation(agent: ConversationalAgent):
    """
    Scenario 1: The Long Explanation
    Agent is explaining something, user provides backchannel feedback
    """
    print("\nAgent: 'So the history of AI started with Turing...'")
    agent.start_explaining("AI History")
    
    # User provides backchannel
    user_inputs = ["okay", "yeah", "uh-huh", "right"]
    for user_input in user_inputs:
        print(f"User: '{user_input}'")
        action = agent.process_user_speech(user_input)
        print(f"  → {action['interruption_type'].upper()}")
        assert action['interruption_type'] == 'ignore', "Should ignore backchannel while speaking"
    
    agent.stop_explaining()
    print("\nAgent: [finished]")


def scenario_2_passive_affirmation(agent: ConversationalAgent):
    """
    Scenario 2: The Passive Affirmation
    Agent asks question and waits for response
    """
    agent.start_explaining("Question posed")
    print("Agent: 'Are you ready to continue?'")
    agent.stop_explaining()
    
    print("User: 'Yeah.'")
    action = agent.process_user_speech("yeah")
    print(f"  → {action['interruption_type'].upper()}")
    assert action['interruption_type'] == 'respond', "Should respond to backchannel when silent"
    
    print("Agent: 'Great, let's continue...'")


def scenario_3_correction(agent: ConversationalAgent):
    """
    Scenario 3: The Correction
    Agent is counting, user says "stop"
    """
    agent.start_explaining("Counting")
    print("Agent: 'One, two, three, four...'")
    
    print("User: 'No, stop.'")
    action = agent.process_user_speech("no stop")
    print(f"  → {action['interruption_type'].upper()}")
    assert action['interruption_type'] == 'interrupt', "Should interrupt for stop command"
    assert action['will_interrupt'] is True, "Should trigger interrupt callback"
    
    agent.stop_explaining()
    print("Agent: [stopped abruptly]")


def scenario_4_mixed_input(agent: ConversationalAgent):
    """
    Scenario 4: The Mixed Input
    User says something with both backchannel and interrupt command
    """
    agent.start_explaining("Complex topic")
    print("Agent: 'Let me explain the concept...'")
    
    print("User: 'Yeah okay but wait.'")
    action = agent.process_user_speech("yeah okay but wait")
    print(f"  → {action['interruption_type'].upper()}")
    assert action['interruption_type'] == 'interrupt', "Should detect interrupt command in mixed input"
    
    agent.stop_explaining()
    print("Agent: [stopped, listening]")


def main():
    """Run all scenarios"""
    print("\n" + "=" * 80)
    print("INTELLIGENT INTERRUPTION HANDLER - LIVEKIT AGENTS INTEGRATION")
    print("=" * 80)
    
    # Run all scenarios
    scenarios = [
        ("Scenario 1: Long Explanation", scenario_1_long_explanation),
        ("Scenario 2: Passive Affirmation", scenario_2_passive_affirmation),
        ("Scenario 3: Correction", scenario_3_correction),
        ("Scenario 4: Mixed Input", scenario_4_mixed_input),
    ]
    
    for name, scenario_fn in scenarios:
        try:
            run_scenario(name, scenario_fn)
            print(f"✓ {name} PASSED")
        except AssertionError as e:
            print(f"✗ {name} FAILED: {e}")
        except Exception as e:
            print(f"✗ {name} ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("ALL SCENARIOS COMPLETED")
    print("=" * 80)
    print("\nLogs saved to: agent_interruption.log")


if __name__ == "__main__":
    main()
