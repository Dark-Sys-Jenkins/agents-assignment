from __future__ import annotations

import unittest

from interview_coach.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_applied_with_required_api_key(self) -> None:
        settings = Settings.from_env({"OPENAI_API_KEY": "test-key"})

        self.assertEqual(settings.role, "backend engineer")
        self.assertEqual(settings.level, "intermediate")
        self.assertEqual(settings.llm_model, "gpt-4o-mini")
        self.assertEqual(settings.tts_voice, "echo")

    def test_role_and_level_are_normalized(self) -> None:
        settings = Settings.from_env(
            {
                "OPENAI_API_KEY": "test-key",
                "INTERVIEW_ROLE": " Data Analyst ",
                "INTERVIEW_LEVEL": "ADVANCED",
            }
        )

        self.assertEqual(settings.role, "data analyst")
        self.assertEqual(settings.level, "advanced")

    def test_api_key_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY is required"):
            Settings.from_env({})

    def test_invalid_role_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported INTERVIEW_ROLE"):
            Settings.from_env(
                {"OPENAI_API_KEY": "test-key", "INTERVIEW_ROLE": "astronaut"}
            )

    def test_invalid_level_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported INTERVIEW_LEVEL"):
            Settings.from_env(
                {"OPENAI_API_KEY": "test-key", "INTERVIEW_LEVEL": "expert"}
            )

    def test_empty_model_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "OPENAI_LLM_MODEL must not be empty"):
            Settings.from_env(
                {"OPENAI_API_KEY": "test-key", "OPENAI_LLM_MODEL": " "}
            )


if __name__ == "__main__":
    unittest.main()
