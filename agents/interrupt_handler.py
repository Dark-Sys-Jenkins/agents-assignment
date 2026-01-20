import asyncio
import re
from typing import Callable, Optional


class IntelligentInterruptHandler:

    DEFAULT_IGNORE_WORDS = {
        "yeah",
        "ok",
        "okay",
        "hmm",
        "uh",
        "uhh",
        "uh-huh",
        "mm-hmm",
        "right",
    }

    DEFAULT_INTERRUPT_WORDS = {
        "stop",
        "wait",
        "no",
        "cancel",
        "hold on",
    }

    def __init__(
        self,
        *,
        is_agent_speaking: Callable[[], bool],
        stop_audio: Callable[[], None],
        continue_audio: Callable[[], None],
        decision_delay_ms: int = 150,
        ignore_words: Optional[set] = None,
        interrupt_words: Optional[set] = None,
    ):
        self.is_agent_speaking = is_agent_speaking
        self.stop_audio = stop_audio
        self.continue_audio = continue_audio

        self.ignore_words = ignore_words or self.DEFAULT_IGNORE_WORDS
        self.interrupt_words = interrupt_words or self.DEFAULT_INTERRUPT_WORDS

        self.decision_delay_ms = decision_delay_ms

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return text.strip()

    def _contains_interrupt(self, text: str) -> bool:
        return any(word in text for word in self.interrupt_words)

    def _is_only_backchannel(self, text: str) -> bool:
        words = text.split()
        return all(word in self.ignore_words for word in words)

    # logic code ka #

    async def handle_stt_result(self, text: str):
        normalized = self._normalize(text)

        print(f"[STT] '{normalized}'")

        if not self.is_agent_speaking():
            print("[DECISION] agent silent → respond normally")
            return "respond"

        if self._contains_interrupt(normalized):
            print("[DECISION] interrupt detected → stopping agent")
            self.stop_audio()
            return "interrupt"

        if self._is_only_backchannel(normalized):
            print("[DECISION] backchannel detected → ignoring")
            self.continue_audio()
            return "ignore"
        print("[DECISION] non-filler speech → stopping agent")
        self.stop_audio()
        return "interrupt"

    def on_vad_detected(self, stt_future: asyncio.Future):

        if not self.is_agent_speaking():
            return

        async def decision_task():
            try:
                text = await asyncio.wait_for(
                    stt_future,
                    timeout=self.decision_delay_ms / 1000,
                )
                await self.handle_stt_result(text)
            except asyncio.TimeoutError:
                print("[DECISION] STT timeout → stopping agent (safety)")
                self.stop_audio()

        asyncio.create_task(decision_task())
