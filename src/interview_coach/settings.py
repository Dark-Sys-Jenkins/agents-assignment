"""Validated environment configuration for the interview coach."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .questions import available_levels, available_roles


@dataclass(frozen=True)
class Settings:
    role: str
    level: str
    llm_model: str
    tts_voice: str

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> Settings:
        """Create settings from an environment mapping and validate required values."""
        env = os.environ if values is None else values
        if not env.get("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY is required to run the interview coach.")

        role = env.get("INTERVIEW_ROLE", "backend engineer").strip().casefold()
        if role not in available_roles():
            choices = ", ".join(available_roles())
            raise ValueError(f"Unsupported INTERVIEW_ROLE {role!r}. Choose one of: {choices}.")

        level = env.get("INTERVIEW_LEVEL", "intermediate").strip().casefold()
        if level not in available_levels():
            choices = ", ".join(available_levels())
            raise ValueError(f"Unsupported INTERVIEW_LEVEL {level!r}. Choose one of: {choices}.")

        llm_model = env.get("OPENAI_LLM_MODEL", "gpt-4o-mini").strip()
        if not llm_model:
            raise ValueError("OPENAI_LLM_MODEL must not be empty.")

        tts_voice = env.get("OPENAI_TTS_VOICE", "echo").strip()
        if not tts_voice:
            raise ValueError("OPENAI_TTS_VOICE must not be empty.")

        return cls(
            role=role,
            level=level,
            llm_model=llm_model,
            tts_voice=tts_voice,
        )
