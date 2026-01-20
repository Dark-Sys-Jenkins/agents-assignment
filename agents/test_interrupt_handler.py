import asyncio
from interrupt_handler import IntelligentInterruptHandler


class FakeAgent:
    def __init__(self):
        self.speaking = True

    def is_speaking(self):
        return self.speaking

    def stop_audio(self):
        print(">>> AGENT STOPPED")

    def continue_audio(self):
        print(">>> AGENT CONTINUES")


async def run_tests():
    agent = FakeAgent()

    handler = IntelligentInterruptHandler(
        is_agent_speaking=agent.is_speaking,
        stop_audio=agent.stop_audio,
        continue_audio=agent.continue_audio,
    )

    print("\n--- TEST 1: Backchannel while speaking ---")
    await handler.handle_stt_result("yeah ok hmm")

    print("\n--- TEST 2: Mixed input while speaking ---")
    await handler.handle_stt_result("yeah but wait")

    print("\n--- TEST 3: Hard stop while speaking ---")
    await handler.handle_stt_result("stop")

    print("\n--- TEST 4: Backchannel while silent ---")
    agent.speaking = False
    await handler.handle_stt_result("yeah")


if __name__ == "__main__":
    asyncio.run(run_tests())
