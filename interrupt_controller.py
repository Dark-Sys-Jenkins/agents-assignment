import time
import re

from logging_utils import configure_logger

logger = configure_logger("history-agent")

class InterruptController:
    def __init__(
        self,
        ignore_words=None,
        interrupt_words=None,
        grace_ms=250,
    ):
        self.ignore_words = ignore_words or {
            "yeah", "ok", "okay", "hmm", "uh", "uh-huh", "aha", "right","correct"
        }
        self.interrupt_words = interrupt_words or {
            "stop", "wait", "no", "cancel", "hold"
        }

        self.grace_ms = grace_ms

        self.agent_is_speaking = False
        self.pending_interrupt = False
        self.pending_since = None

    # ---------- Agent state ----------
    def on_agent_state_changed(self, new_state: str):
        if new_state == "speaking":
            self.agent_is_speaking = True
            logger.debug("AgentSpeaking:%s Agent state changed to speaking", self.agent_is_speaking)
        else:
            self.agent_is_speaking = False
            logger.debug(
                "AgentSpeaking:%s Agent state changed to %s, clearing pending interrupts",
                self.agent_is_speaking,
                new_state,
            )
            self._reset_pending()
        

    # ---------- User speech (VAD inferred) ----------
    def on_user_speech_detected(self):
        if self.agent_is_speaking:
            self.pending_interrupt = True
            self.pending_since = time.time()
            logger.debug("AgentSpeaking:%s User speech detected while agent speaking", self.agent_is_speaking)

    # ---------- STT final ----------
    def should_interrupt(self, transcript: str) -> bool:
        logger.debug("AgentSpeaking:%s Evaluating should_interrupt for transcript=%r", self.agent_is_speaking, transcript)

        # Tokenize first so explicit interrupt words are honored anytime
        tokens = self._tokenize(transcript)
        logger.debug("AgentSpeaking:%s Tokenized transcript: %s", self.agent_is_speaking, tokens)

        # If explicit interrupt words found → interrupt immediately
        found_interrupts = [t for t in tokens if t in self.interrupt_words]
        if found_interrupts:
            logger.info("AgentSpeaking:%s Interrupt words detected: %s — interrupting flow", self.agent_is_speaking, found_interrupts)
            self._reset_pending()
            return True
        
        # Grace period expired: consider it an interruption
        if self._grace_expired():
            logger.info("AgentSpeaking:%s Grace period expired (%.1f ms) — treating as interrupt", self.agent_is_speaking, self.grace_ms)
            self._reset_pending()
            return True
        
        # 2. Backchannel while speaking → ignore completely
        if (
            self.agent_is_speaking
            and tokens
            and all(t in self.ignore_words for t in tokens)
        ):
            logger.info("AgentSpeaking:%s Backchanneling detected: %s — ignoring", self.agent_is_speaking, tokens)
            self._reset_pending()
            return False
        
        # 3. Mixed / semantic input → interrupt
        if self.agent_is_speaking and tokens:
            logger.info("AgentSpeaking:%s Mixed/non-ignored expression detected: %s — treating as interrupt", self.agent_is_speaking, tokens)
            self._reset_pending()
            return True
        # If we don't have a pending interrupt (user didn't start speaking during agent speech),
        # we won't treat non-explicit tokens as interrupts.
        # if not self.pending_interrupt:
        #     logger.debug("AgentSpeaking:%s No pending interrupt — will not interrupt", self.agent_is_speaking)
        #     return False


        # # If all tokens are ignore words → do not interrupt
        # if tokens and all(t in self.ignore_words for t in tokens):
        #     logger.info("AgentSpeaking:%s All tokens are ignore words: %s — not interrupting", self.agent_is_speaking, tokens)
        #     self._reset_pending()
        #     return False    #, tokens

        # # Mixed or other non-empty expression: treat as interruption
        # if tokens:
        #     logger.info("AgentSpeaking:%s Mixed/non-ignored expression detected: %s — treating as interrupt", self.agent_is_speaking, tokens)
        #     self._reset_pending()
        #     return True

        # Empty tokens (silence or punctuation) — do not interrupt
        logger.debug("AgentSpeaking:%s No meaningful tokens in transcript — not interrupting", self.agent_is_speaking)
        self._reset_pending()
        return False

    # ---------- Helpers ----------
    def _grace_expired(self):
        if self.pending_since is None:
            return False
        return (time.time() - self.pending_since) * 1000 > self.grace_ms

    def _reset_pending(self):
        self.pending_interrupt = False
        self.pending_since = None

    def _tokenize(self, text: str):
        text = text.lower().strip()
        return re.findall(r"\b[\w-]+\b", text)
    
    