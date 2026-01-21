# interaction_manager.py

import os
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger("interaction-manager")

def _load_lex(key: str, default: List[str]) -> List[str]:
    """Shorthand for loading normalized vocabulary from env."""
    raw = os.getenv(key, "")
    if not raw:
        return [w.strip().lower() for w in default]
    return [w.strip().lower() for w in raw.split(",") if w.strip()]

def _normalize(text: str) -> str:
    """Internal string cleanup."""
    s = text.strip().lower().replace("-", " ")
    s = re.sub(r"[^a-z0-9'\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

@dataclass
class InteractionManager:
    """
    Ultra-simplified Interaction Controller for Kelly.
    - Fillers: Noise to ignore.
    - Commands: Explicit triggers to stop/pause.
    """
    session: any # AgentSession

    # Rebranded & Collapsed Lexicons
    fillers: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)

    _status: str = "init"
    
    # Timing
    recovery_window: float = 15.0

    def __post_init__(self):
        self._sync()
        self._init_storage()

    def _sync(self):
        # Env: INTERACT_FILLERS, INTERACT_COMMANDS
        self.fillers = _load_lex("INTERACT_FILLERS", ["yeah", "ya", "yep", "yup", "yes", "ok", "okay", "k", "hmm", "mm", "mhmm", "mmm", "uh", "uh huh", "uh-huh", "mm hmm", "mm-hmm", "right", "sure", "alright", "gotcha", "got it", "i see", "aha"])
        self.commands = _load_lex("INTERACT_COMMANDS", ["stop", "wait", "pause", "cancel", "hold on", "hang on", "no", "nope", "nah"])
        
        self.fillers.sort(key=len, reverse=True)
        self.commands.sort(key=len, reverse=True)

    def _init_storage(self):
        ud = self.session.userdata
        ud.setdefault("ignore_intent", False)
        ud.setdefault("interaction_lock", 0.0)
        ud.setdefault("paused_state", False)
        ud.setdefault("paused_expiry", 0.0)

    def attach(self):
        self.session.on("agent_state_changed", self._on_state_change)
        self.session.on("user_input_transcribed", self._on_transcript)

    def _on_state_change(self, ev: any):
        old = self._status
        self._status = getattr(ev, "new_state", old)
        if old != self._status:
            logger.debug(f"State: {old} -> {self._status}")

    def _on_transcript(self, ev: any):
        raw = ev.transcript or ""
        if not raw.strip(): return
        
        text = _normalize(raw)
        self._run_audit(text, raw, ev.is_final)

    def _run_audit(self, text: str, original: str, final: bool):
        is_active = self._status in ("thinking", "speaking")
        is_filler = self._is_filler(text)
        is_stop = self._is_stop(text)

        logger.debug(f"Audit: {self._status}, text={text!r}, filler={is_filler}, stop={is_stop}, final={final}")

        # Auto-clear pause
        if not is_active and final:
            if self.session.userdata.get("paused_state"):
                if (not is_filler and not is_stop) or not self._is_recoverable():
                    self._clear_pause_state()

        # Stop Processor
        if is_stop:
            if is_active or (not final):
                logger.info(f"Stop Detected: {original!r}")
                self._apply_lock(1.2)
                self._set_pause_state()
                self._kill_and_ignore()
            elif final:
                logger.info(f"Idle Stop Ignored: {original!r}")
                self._apply_lock(0.8)
                self._set_ignore_flag()
                self._stop_audio()
            return

        # Active Session Logic
        if is_active:
            if final and is_filler:
                logger.info(f"Filter Filler: {original!r}")
                self._set_ignore_flag()
            elif not is_filler:
                if final or len(text.split()) >= 2:
                    logger.info(f"Direct Override: {original!r}")
                    self._clear_pause_state()
                    self._stop_keep_turn()
            return

        # Passive Recovery
        if final and is_filler and self._is_recoverable():
            logger.info(f"Kelly Recovery: {original!r}")
            self._clear_pause_state()
            self._set_ignore_flag()
            self._resume_prev()

    def _is_filler(self, text: str) -> bool:
        if len(text.split()) > 4: return False
        return self._strip_lex(text, self.fillers) == ""

    def _is_stop(self, text: str) -> bool:
        # Simplest possible check: strip fillers, see if it starts with or matches a command.
        core = self._strip_prefix(text, self.fillers)
        if not core: return False
        return any(core == c or core.startswith(c + " ") for c in self.commands)

    def _strip_lex(self, text: str, lex: List[str]) -> str:
        s = f" {text} "
        for term in lex:
            s = re.sub(rf"\b{re.escape(term)}\b", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _strip_prefix(self, text: str, lex: List[str]) -> str:
        curr = text.strip()
        while True:
            found = False
            for term in lex:
                if not term: continue
                if curr == term: return ""
                if curr.startswith(term + " "):
                    curr = curr[len(term):].strip()
                    found = True
                    break
            if not found: break
        return curr

    # Session Management
    def _apply_lock(self, sec: float):
        try: self.session.userdata["interaction_lock"] = time.monotonic() + sec
        except: pass

    def _set_pause_state(self):
        try:
            ud = self.session.userdata
            ud["paused_state"] = True
            ud["paused_expiry"] = time.monotonic() + self.recovery_window
        except: pass

    def _clear_pause_state(self):
        try:
            ud = self.session.userdata
            ud["paused_state"] = False
            ud["paused_expiry"] = 0.0
        except: pass

    def _is_recoverable(self) -> bool:
        try:
            ud = self.session.userdata
            return ud.get("paused_state") and time.monotonic() <= ud.get("paused_expiry", 0.0)
        except: return False

    def _resume_prev(self):
        try:
            meth = getattr(self.session, "generate_reply", None)
            if callable(meth): meth(instructions="Pick up where you left off.")
        except: pass

    def _set_ignore_flag(self):
        try:
            self.session.userdata["ignore_intent"] = True
            self.session.clear_user_turn()
        except: pass

    def _kill_and_ignore(self):
        self._set_ignore_flag()
        try:
            can = getattr(self.session, "cancel_reply", None)
            if callable(can): can()
        except: pass
        self._stop_audio()
        try: self.session.clear_user_turn()
        except: pass

    def _stop_keep_turn(self):
        try:
            self.session.userdata["ignore_intent"] = False
            self._stop_audio()
        except: pass

    def _stop_audio(self):
        try: self.session.interrupt(force=True)
        except:
            try: self.session.interrupt()
            except: pass
