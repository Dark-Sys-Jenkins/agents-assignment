# examples/voice_agents/simulate_interruption_race.py
import asyncio
import logging
import os
import sys
import time
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Setup Logging
PROOF_FILE = "interruption_log_proof.txt"
if os.path.exists(PROOF_FILE):
    os.remove(PROOF_FILE)

# Configure format to match requirements
formatter = logging.Formatter('%(message)s')
file_handler = logging.FileHandler(PROOF_FILE)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Configure the specific logger used in the code
logger = logging.getLogger("smart-agent-activity")
logger.setLevel(logging.INFO)
logger.handlers = [] # Clear existing
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Import classes
try:
    from examples.voice_agents.smart_interruption_session import SmartAgentActivity
    from examples.voice_agents.intelligent_interruption_agent import IntelligentInterruptionHandler
    from livekit.agents.voice.agent_activity import AgentActivity
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Mocks
class MockSpeechEvent:
    def __init__(self, text, is_final=True):
        self.alternatives = [MagicMock()]
        self.alternatives[0].text = text
        self.type = 1 # FINAL_TRANSCRIPT generic

class MockVADEvent:
    def __init__(self):
        self.type = "inference_done"
        self.speech_duration = 0.5
        self.silence_duration = 0.0
        self.frames = []
        self.probability = 1.0
        self.inference_duration = 0.05
        self.event_type = 1 # VADEventType.INFERENCE_DONE

async def run_simulation():
    print(f"Starting simulation... Output will be saved to {PROOF_FILE}")
    
    # 1. Setup
    mock_agent = MagicMock()
    mock_session = MagicMock()
    mock_session.interrupt = AsyncMock()
    mock_session.commit_user_turn = AsyncMock()
    mock_session.clear_user_turn = AsyncMock()
    # Fix option comparison error
    mock_session.options = MagicMock()
    mock_session.options.min_interruption_words = 0
    
    # Real handler
    handler = IntelligentInterruptionHandler(ignore_words=None, interrupt_keywords=None)
    
    # helper to patch parent methods
    with patch.object(AgentActivity, 'on_vad_inference_done') as mock_super_vad, \
         patch.object(AgentActivity, 'on_final_transcript') as mock_super_stt, \
         patch.object(AgentActivity, 'on_interim_transcript') as mock_super_interim, \
         patch.object(AgentActivity, 'on_start_of_speech') as mock_super_start:
        
        # Instantiate Activity
        activity = SmartAgentActivity(mock_agent, mock_session, handler)
        
        # Helper to set speaking state
        def set_agent_speaking(is_speaking):
            activity._agent_state = "speaking" if is_speaking else "listening"
            # Also mock _current_speech to ensure _is_agent_speaking returns True
            if is_speaking:
                activity._current_speech = MagicMock()
            else:
                activity._current_speech = None
            
            # Update internal state tracker if necessary (though SmartAgentActivity checks _is_agent_speaking internal logic)
        
        async def scenario_runner(name, description, setup_fn, steps):
            logger.info(f"\n[{time.time():06.3f}] === SCENARIO {name}: {description} ===")
            
            # Reset
            activity.pending_interruptions.clear()
            mock_session.interrupt.reset_mock()
            mock_session.commit_user_turn.reset_mock()
            
            setup_fn()
            
            for step_type, delay, data in steps:
                await asyncio.sleep(delay)
                
                if step_type == "VAD":
                    # Manually call the method on our instance
                    # Since parent is patched, super() logic won't run/break
                    activity.on_vad_inference_done(MockVADEvent())
                elif step_type == "STT":
                    activity.on_final_transcript(MockSpeechEvent(data))
            
            # Wait a bit for async tasks to complete
            await asyncio.sleep(0.1)

        # Scenario A: Backchannel during speech
        await scenario_runner(
            "A", "Backchannel during speech ('yeah')",
            lambda: set_agent_speaking(True),
            [
                ("VAD", 0.05, None),
                ("STT", 0.2, "yeah")
            ]
        )
        
        # Scenario B: Real interrupt during speech
        await scenario_runner(
            "B", "Real interrupt during speech ('stop')",
            lambda: set_agent_speaking(True),
            [
                ("VAD", 0.05, None),
                ("STT", 0.2, "stop")
            ]
        )

        # Scenario C: Backchannel while silent
        await scenario_runner(
            "C", "Backchannel while silent ('yeah')",
            lambda: set_agent_speaking(False), # Agent Silent
            [
                ("VAD", 0.05, None),
                ("STT", 0.2, "yeah")
            ]
        )

        # Scenario D: Mixed semantic interrupt
        await scenario_runner(
            "D", "Mixed semantic interrupt ('yeah but wait')",
            lambda: set_agent_speaking(True),
            [
                ("VAD", 0.05, None),
                ("STT", 0.2, "yeah but wait")
            ]
        )

    print("Simulation complete.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
