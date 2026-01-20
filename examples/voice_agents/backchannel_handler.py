# backchannel_handler.py

import os
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Iterable, List

from livekit.agents import (
    AgentSession,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)

logger = logging.getLogger("backchannel-handler")


def _load_list(env_var: str, default: Iterable[str]) -> List[str]:
    raw = os.getenv(env_var)
    if not raw:
        return [w.strip().lower() for w in default if w.strip()]
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


def _normalize(text: str) -> str:
    t = text.strip().lower()
    t = t.replace("-", " ")
    t = re.sub(r"[^a-z0-9'\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


@dataclass
class BackchannelInterruptionHandler:
    """
    Behavior you want:

    - If user says "stop" while agent is speaking:
        agent stops talking immediately
        we enter paused_by_stop mode for a short window

    - If paused_by_stop is active and user says a pass word (yeah/ok/hmm):
        we RESUME and continue the previous response

    - Any other user utterance:
        should be treated as a normal prompt (NOT swallowed),
        and should exit paused_by_stop mode.

    IMPORTANT FIX (your current behavior):
    - When the agent is silent and NOT in the resume-after-stop window,
      do NOT swallow "yeah/ok/uh-huh/hmm".
      Let it be committed as a real user turn (so yes/no answers work).

    NEW FIX (your request):
    - Treat phrases like "yeah wait a second" / "ok hold on" as commands too.
      i.e., allow a short backchannel lead-in before a command.
    """

    session: AgentSession

    ignore_phrases: List[str] = field(default_factory=list)

    # Strong commands that should stop/pause even if embedded in short phrases
    command_phrases: List[str] = field(default_factory=list)

    # Soft “negation” phrases that should only be treated as command if said alone
    negation_phrases: List[str] = field(default_factory=list)

    _agent_state: str = "initializing"

    # How long after "stop" a backchannel can trigger "resume"
    resume_window_seconds: float = 15.0

    # Interrupt quickly on partial transcripts if we detect a strong command and agent is speaking
    fast_command_partial_word_limit: int = 4

    # Polite filler words allowed after a command without making it a “real” user turn
    polite_fillers: List[str] = field(
        default_factory=lambda: ["please", "thanks", "thank", "you", "ok", "okay"]
    )

    # Words allowed after a command while still counting as a command
    # Examples: "wait a second", "hold on one sec", "wait for a moment"
    command_trailing_words: List[str] = field(
        default_factory=lambda: ["a", "an", "one", "sec", "secs", "second", "seconds", "moment", "bit", "for"]
    )

    # How long we should swallow FINAL transcripts after we decide to swallow something
    # (prevents swallowing the user's next real prompt)
    swallow_window_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not self.ignore_phrases:
            self.ignore_phrases = _load_list(
                "BACKCHANNEL_IGNORE_WORDS",
                [
                    # Do NOT treat greetings as backchannels.
                    # "hi", "hello", "hey",

                    "yeah", "ya", "yep", "yup", "yes",
                    "ok", "okay", "k",
                    "hmm", "mm", "mhmm", "mmm",
                    "uh", "uh huh", "uh-huh", "mm hmm", "mm-hmm",
                    "right", "sure", "alright",
                    "gotcha", "got it", "i see",
                    "aha",
                ],
            )

        if not self.command_phrases:
            self.command_phrases = _load_list(
                "BACKCHANNEL_COMMAND_WORDS",
                [
                    "stop", "wait", "pause", "cancel",
                    "hold on", "hang on",
                ],
            )

        if not self.negation_phrases:
            self.negation_phrases = _load_list(
                "BACKCHANNEL_NEGATION_WORDS",
                [
                    "no", "nope", "nah",
                ],
            )

        # Longest phrases first (better matching)
        self.ignore_phrases.sort(key=len, reverse=True)
        self.command_phrases.sort(key=len, reverse=True)
        self.negation_phrases.sort(key=len, reverse=True)

        try:
            self.session.userdata.setdefault("swallow_next_commit", False)
            self.session.userdata.setdefault("swallow_until", 0.0)  # time-bounded swallow
            self.session.userdata.setdefault("suppress_commits_until", 0.0)
            self.session.userdata.setdefault("paused_by_stop", False)
            self.session.userdata.setdefault("paused_resume_deadline", 0.0)
        except Exception:
            pass

    def attach(self) -> None:
        @self.session.on("agent_state_changed")
        def _on_agent_state_changed(ev: AgentStateChangedEvent) -> None:
            self._agent_state = getattr(ev, "new_state", self._agent_state)

        @self.session.on("user_input_transcribed")
        def _on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
            text = (ev.transcript or "").strip()
            if not text:
                return
            self._handle_transcript(text, is_final=ev.is_final)

    def _contains_any_phrase(self, normalized_text: str, phrases: List[str]) -> bool:
        for p in phrases:
            if re.search(rf"\b{re.escape(p)}\b", normalized_text):
                return True
        return False

    def _strip_phrases(self, normalized_text: str, phrases: List[str]) -> str:
        t = f" {normalized_text} "
        for p in phrases:
            t = re.sub(rf"\b{re.escape(p)}\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _strip_leading_phrases(self, normalized_text: str, phrases: List[str]) -> str:
        """
        Remove phrases only if they appear at the beginning, repeatedly.
        Supports multi-word phrases as long as they are normalized the same way.
        """
        t = normalized_text.strip()
        changed = True
        while changed and t:
            changed = False
            for p in phrases:
                if not p:
                    continue
                if t == p:
                    return ""
                if t.startswith(p + " "):
                    t = t[len(p):].strip()
                    changed = True
                    break
        return t

    def _is_pure_backchannel(self, normalized_text: str) -> bool:
        words = normalized_text.split()
        if len(words) > 4:
            return False
        leftover = self._strip_phrases(normalized_text, self.ignore_phrases)
        return leftover == ""

    def _is_pure_negation(self, normalized_text: str) -> bool:
        words = normalized_text.split()
        if len(words) > 3:
            return False
        leftover = self._strip_phrases(normalized_text, self.negation_phrases)
        return leftover == ""

    def _is_pure_command(self, normalized_text: str) -> bool:
        """
        Pure command OR command with:
        - polite fillers
        - AND/OR a short backchannel lead-in (yeah/ok/hmm/etc.)

        Examples that should be treated as command:
        - "wait"
        - "wait a second"
        - "yeah wait a second"
        - "ok hold on"
        - "hmm hang on one sec please"

        Avoid false positives like:
        - "i can't wait for tomorrow"
        (we require command at the START after removing lead-ins)
        """
        # Allow leading backchannel like "yeah", "ok", "hmm"
        t = self._strip_leading_phrases(normalized_text, self.ignore_phrases)
        t = self._strip_leading_phrases(t, self.polite_fillers)

        if not t:
            return False

        # Must START with a command phrase (after lead-ins)
        starts_with_cmd = any(t == p or t.startswith(p + " ") for p in self.command_phrases)
        if not starts_with_cmd:
            return False

        # Remove the command phrases and see what's left
        stripped = self._strip_phrases(t, self.command_phrases)
        if stripped == "":
            return True

        stripped2 = self._strip_phrases(stripped, self.polite_fillers)
        if stripped2 == "":
            return True

        # Allow short timing-ish tails: "a second", "one sec", "for a moment"
        tail_words = stripped2.split()
        if len(tail_words) <= 4 and all(w in self.command_trailing_words for w in tail_words):
            return True

        return False

    def _detect_command(self, normalized_text: str) -> bool:
        if self._contains_any_phrase(normalized_text, self.command_phrases):
            return self._is_pure_command(normalized_text)
        if self._contains_any_phrase(normalized_text, self.negation_phrases):
            return self._is_pure_negation(normalized_text)
        return False

    def _set_commit_suppression(self, seconds: float) -> None:
        try:
            self.session.userdata["suppress_commits_until"] = time.monotonic() + seconds
        except Exception:
            pass

    def _arm_swallow_window(self) -> None:
        # Swallow ONLY for a short time window (prevents swallowing next real user prompt)
        now = time.monotonic()
        try:
            self.session.userdata["swallow_next_commit"] = True
            self.session.userdata["swallow_until"] = now + float(self.swallow_window_seconds)
        except Exception:
            pass

    def _set_paused_by_stop(self) -> None:
        try:
            self.session.userdata["paused_by_stop"] = True
            self.session.userdata["paused_resume_deadline"] = (
                time.monotonic() + float(self.resume_window_seconds)
            )
        except Exception:
            pass

    def _clear_paused_by_stop(self) -> None:
        try:
            self.session.userdata["paused_by_stop"] = False
            self.session.userdata["paused_resume_deadline"] = 0.0
        except Exception:
            pass

    def _is_resume_window_active(self) -> bool:
        try:
            if not self.session.userdata.get("paused_by_stop"):
                return False
            deadline = float(self.session.userdata.get("paused_resume_deadline", 0.0))
            return time.monotonic() <= deadline
        except Exception:
            return False

    def _resume_continue(self) -> None:
        """
        Resume should continue the previous answer.
        Use `instructions` so it does NOT become a user prompt.
        """
        try:
            gen = getattr(self.session, "generate_reply", None)
            if callable(gen):
                gen(
                    instructions=(
                        "Continue your previous response from exactly where you stopped. "
                        "Do not restart from the beginning. "
                        "Do not mention that you were paused or interrupted."
                    )
                )
        except Exception:
            logger.exception("Failed to resume via session.generate_reply(instructions=...)")

    def _handle_transcript(self, raw_text: str, is_final: bool) -> None:
        text = _normalize(raw_text)
        if not text:
            return

        agent_speaking = (self._agent_state == "speaking")
        is_backchannel = self._is_pure_backchannel(text)
        is_command = self._detect_command(text)

        # If user says something meaningful while paused, drop pause state so their next words are normal prompts.
        if (
            not agent_speaking
            and is_final
            and self.session.userdata.get("paused_by_stop")
            and not is_backchannel
            and not is_command
        ):
            self._clear_paused_by_stop()

        # If resume window expired, clear paused_by_stop to avoid sticky state.
        if (not agent_speaking) and is_final and self.session.userdata.get("paused_by_stop"):
            if not self._is_resume_window_active():
                self._clear_paused_by_stop()

        # Fast path: if agent is speaking and we detect command on partial, interrupt immediately.
        if agent_speaking and is_command and not is_final:
            if len(text.split()) <= int(self.fast_command_partial_word_limit):
                logger.info(f"INTERRUPT EARLY (partial command) while speaking: {raw_text!r}")
                self._set_commit_suppression(1.2)
                self._set_paused_by_stop()
                self._interrupt_and_swallow()
                return

        # Commands: never become a user turn.
        if is_command:
            if agent_speaking:
                logger.info(f"INTERRUPT (command) while speaking: {raw_text!r}")
                self._set_commit_suppression(1.2)
                self._set_paused_by_stop()
                self._interrupt_and_swallow()
                return
            else:
                if is_final:
                    logger.info(f"SWALLOW (command) while silent: {raw_text!r}")
                    self._set_commit_suppression(0.8)
                    self._swallow_only()
                return

        # CASE A: agent is speaking
        if agent_speaking:
            if is_final and is_backchannel:
                logger.info(f"SWALLOW (backchannel) while speaking: {raw_text!r}")
                self._swallow_only()
                return

            if is_final and not is_backchannel:
                logger.info(f"INTERRUPT (non-backchannel) while speaking: {raw_text!r}")
                self._clear_paused_by_stop()
                self._interrupt_keep_user_turn()
                return

            return

        # CASE B: agent is silent
        if is_final and is_backchannel:
            # If we recently stopped mid-speech, treat backchannel as "continue"
            if self._is_resume_window_active():
                logger.info(f"RESUME (backchannel) after stop: {raw_text!r}")
                self._clear_paused_by_stop()

                # swallow the pass word only (time-bounded) so it doesn't become a user turn
                self._swallow_only()

                # kick off continuation
                self._resume_continue()
                return

            # IMPORTANT FIX:
            # Do NOT swallow backchannels while silent (outside resume window).
            # Let "yeah" be committed normally so it can answer questions like "Do you like pizza?"
            logger.info(f"ALLOW (backchannel) while silent: {raw_text!r}")
            return

        # anything else while silent: normal pipeline (do nothing)

    def _swallow_only(self) -> None:
        # Time-bounded swallow so we don't swallow the user's next real prompt.
        self._arm_swallow_window()
        try:
            self.session.clear_user_turn()
        except Exception:
            pass

    def _interrupt_and_swallow(self) -> None:
        # Time-bounded swallow so we don't swallow the user's next real prompt.
        self._arm_swallow_window()

        # Try to cancel any ongoing reply generation if the SDK exposes it.
        # Note: canceling means resume will generate a continuation (not the same stream).
        try:
            cancel = getattr(self.session, "cancel_reply", None)
            if callable(cancel):
                cancel()
        except Exception:
            pass

        try:
            self.session.interrupt(force=True)
        except TypeError:
            try:
                self.session.interrupt()
            except Exception:
                pass
        except Exception:
            pass

        try:
            self.session.clear_user_turn()
        except Exception:
            pass

    def _interrupt_keep_user_turn(self) -> None:
        # Make sure we DON'T swallow this one (it's a real user turn)
        try:
            self.session.userdata["swallow_next_commit"] = False
            self.session.userdata["swallow_until"] = 0.0
        except Exception:
            pass

        try:
            self.session.interrupt(force=True)
        except TypeError:
            try:
                self.session.interrupt()
            except Exception:
                pass
        except Exception:
            pass
