import asyncio
import os
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)

# ---------------- ENV FALLBACK ----------------
os.environ.setdefault("LIVEKIT_URL", "ws://localhost:7880")
os.environ.setdefault("LIVEKIT_API_KEY", "devkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "devsecret")

# ---------------- WORD LISTS ----------------
PASSIVE_ACKNOWLEDGEMENTS = {
    "yeah", "ok", "okay", "hmm", "uh-huh", "right",
    "sure", "yep", "mm", "mhm", "alright"
}

INTERRUPT_TRIGGERS = {
    "stop", "wait", "no", "hold", "pause", "cancel"
}

# ---------------- SAFE DUMMY LLM ----------------
class DummyLLM(llm.LLM):
    def chat(self, *args, **kwargs):
        return None


# ---------------- AGENT ----------------
class ConsoleAgent(Agent):
    def __init__(self):
        super().__init__(instructions="Console Agent")
        self._speaking = asyncio.Event()

    # Disable LLM pipeline
    async def llm_node(self, *args, **kwargs):
        return None

    async def on_enter(self):
        print("\n[AGENT READY]")
        print("Type anything. Try: yeah (ignore), stop (interrupt)\n")

        @self.session.on("conversation_item_added")
        def handle(ev):
            try:
                if ev.item.role != "user":
                    return

                # -------- SAFE CONTENT EXTRACTION --------
                content = ev.item.content

                if isinstance(content, list):
                    if len(content) > 0:
                        first = content[0]
                        if isinstance(first, dict):
                            text = first.get("text", "")
                        elif isinstance(first, str):
                            text = first
                        else:
                            text = str(first)
                    else:
                        text = ""
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)

                text = text.strip()

                if not text:
                    return

                asyncio.create_task(self.process_input(text))

            except Exception as e:
                print(f"[ERROR]: {e}")

    async def process_input(self, text):
        if not text:
            return

        words = set(text.lower().split())

        if self._speaking.is_set():
            # ---- SPEAKING ----
            if words & INTERRUPT_TRIGGERS:
                print(f"[INTERRUPT] {text}")
                self._speaking.clear()
                self.session.interrupt()

            elif words.issubset(PASSIVE_ACKNOWLEDGEMENTS):
                return 

            else:
                print(f"[INTERRUPT - meaningful] {text}")
                self._speaking.clear()
                self.session.interrupt()

        else:
            # ---- RESPOND ----
            print(f"[RESPOND] {text}")
            asyncio.create_task(self.fake_speaking(text))

    async def fake_speaking(self, text):
        if self._speaking.is_set():
            return

        self._speaking.set()

        msg = f"You said '{text}'. agent is speaking"
        words = msg.split()

        print("\n[AGENT]", end=" ", flush=True)

        try:
            for w in words:
                if not self._speaking.is_set():
                    print(" <-- interrupted")
                    return

                print(w, end=" ", flush=True)
                await asyncio.sleep(0.2)

            print("\n[AGENT DONE]\n")

        finally:
            self._speaking.clear()


# ---------------- ENTRYPOINT ----------------
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(llm=DummyLLM())

    await session.start(
        room=ctx.room,
        agent=ConsoleAgent(),
    )


# ---------------- MAIN ----------------
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint)
    )