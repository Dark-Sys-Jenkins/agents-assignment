from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, elevenlabs, openai, silero
from typing import Optional
import asyncio
from interrupt_handler import InterruptHandler, AgentState, InterruptType


class EnhancedAgentSession(AgentSession):
    """Extended AgentSession with interrupt handling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interrupt_handler = InterruptHandler()
        self.is_speaking = False
        self.pending_task = None
        
    async def start(self, *args, **kwargs):
        """Override start to hook into speaking events"""
        await super().start(*args, **kwargs)
        
        # Hook into TTS events to track speaking state
        original_speak = self.tts.speak
        
        async def tracked_speak(text, **speak_kwargs):
            self.is_speaking = True
            self.interrupt_handler.set_agent_state(AgentState.SPEAKING)
            try:
                result = await original_speak(text, **speak_kwargs)
                return result
            finally:
                self.is_speaking = False
                self.interrupt_handler.set_agent_state(AgentState.SILENT)
                
        self.tts.speak = tracked_speak
        
    async def handle_user_input(self, text: str):
        """
        Process user input with interrupt handling logic.
        Called when STT produces transcription.
        """
        interrupt_type = await self.interrupt_handler.process_transcription(text)
        
        if interrupt_type == InterruptType.IGNORE:
            # Ignore filler words while agent is speaking
            print(f"[IGNORE] User said: '{text}' while agent was speaking")
            return None
            
        elif interrupt_type == InterruptType.INTERRUPT:
            # Interrupt agent immediately
            print(f"[INTERRUPT] User command: '{text}'")
            await self._interrupt_agent()
            return text
            
        elif interrupt_type == InterruptType.RESPOND:
            # Normal response handling
            print(f"[RESPOND] User input: '{text}'")
            return text


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    
    # Create enhanced session
    session = EnhancedAgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(),
    )
    
    agent = Agent(
        instructions="You are a helpful assistant that handles interruptions intelligently.",
        name="Enhanced Agent"
    )
    
    await session.start(agent=agent, room=ctx.room)
    
    # Hook into the STT stream
    async def on_transcription(text: str):
        if text.strip():  # Only process non-empty transcriptions
            processed_text = await session.handle_user_input(text)
            if processed_text and not session.is_speaking:
                # Generate response if agent isn't speaking
                await session.generate_reply(user_input=processed_text)
    
    # In a real implementation, you'd hook this to the actual STT stream
    # This depends on the specific STT plugin being used


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))