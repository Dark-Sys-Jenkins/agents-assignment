from livekit.agents import Agent
from interrupt_handler import InterruptHandler


class InterruptAwareAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are a helpful AI assistant.
            Speak clearly and politely.
            """
        )
        self.handler = InterruptHandler()

    # ✅ CORRECT LiveKit callbacks
    async def on_agent_started_speaking(self):
        self.handler.on_agent_speaking_start()

    async def on_agent_stopped_speaking(self):
        self.handler.on_agent_speaking_end()

    async def on_user_speech_start(self):
        self.handler.on_user_speech_start()

    async def on_user_transcript(self, text: str):
        self.handler.on_user_transcript(
            text=text,
            stop_audio=self.stop_audio,
            respond=self.respond,
        )


def main():
    agent = InterruptAwareAgent()
    print("InterruptAwareAgent initialized successfully.")


if __name__ == "__main__":
    main()
