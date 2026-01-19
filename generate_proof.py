import asyncio
import logging
import sys
from livekit.agents import Agent
from tests.fake_session import FakeActions, create_session, run_session

# Configure logging to output to file and stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", handlers=[
    logging.FileHandler("proof_log.txt", mode='w'),
    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger("proof")

class MyAgent(Agent):
    def __init__(self, interruption_ignore_list=None):
        super().__init__(
            instructions="You are a helpful assistant.",
            interruption_ignore_list=interruption_ignore_list
        )

async def run_demo():
    logger.info("--- Starting Proof Demo ---")
    
    # Scene 1: Ignore "yeah"
    logger.info("\n[Scene 1] Agent ignores 'yeah' while speaking")
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0)
    # User says "yeah" at 5.0s (during speech)
    actions.add_user_speech(5.0, 5.5, "yeah", stt_delay=0.1)
    
    session = create_session(actions, speed_factor=5.0)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    logger.info("Running session...")
    await run_session(session, agent)
    # Check logs for "interruption" events (or lack thereof)
    
    # Scene 2: Stop for "stop"
    logger.info("\n[Scene 2] Agent stops for 'stop'")
    actions = FakeActions()
    actions.add_user_speech(0.5, 2.0, "Tell me a story.")
    actions.add_llm("Here is a long story for you... the end.")
    actions.add_tts(10.0)
    actions.add_user_speech(5.0, 5.5, "stop", stt_delay=0.1)
    
    session = create_session(actions, speed_factor=5.0)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    await run_session(session, agent)

    # Scene 3: Respond to "yeah" when silent
    logger.info("\n[Scene 3] Agent responds to 'yeah' when silent")
    actions = FakeActions()
    # Agent is silent initially
    actions.add_user_speech(1.0, 1.5, "yeah")
    actions.add_llm("How can I help you?") # Expect response
    actions.add_tts(5.0)
    
    session = create_session(actions, speed_factor=5.0)
    agent = MyAgent(interruption_ignore_list=["yeah", "ok"])
    
    await run_session(session, agent)
    logger.info("--- Proof Demo Completed ---")

if __name__ == "__main__":
    asyncio.run(run_demo())
