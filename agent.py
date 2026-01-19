from interrupt_filter import InterruptFilter

interrupt_filter = InterruptFilter()

class Agent:
    def __init__(self):
        self.speaking = False

    async def speak(self, text):
        interrupt_filter.on_agent_start_speaking()
        self.speaking = True

        print(f"Agent speaking: {text}")

        # simulate speaking
        await self.fake_wait()

        interrupt_filter.on_agent_stop_speaking()
        self.speaking = False

    async def fake_wait(self):
        import asyncio
        await asyncio.sleep(3)

    async def on_vad_detected(self):
        # VAD detected user speech
        if not interrupt_filter.on_vad_trigger():
            return
        await self.stop_audio()

    async def on_stt_final(self, text):
        decision = interrupt_filter.on_stt_result(text)

        if decision == "INTERRUPT":
            await self.stop_audio()
            print("Agent interrupted")

        elif decision == "IGNORE":
            print("Ignoring filler while speaking")

        else:
            await self.handle_user_input(text)

    async def stop_audio(self):
        print("Audio stopped")

    async def handle_user_input(self, text):
        print(f"User said: {text}")
