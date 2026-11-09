from __future__ import annotations

import unittest

from interview_coach.questions import (
    available_levels,
    available_roles,
    get_question_plan,
)


class QuestionPlanTests(unittest.TestCase):
    def test_every_supported_plan_has_four_questions(self) -> None:
        for role in available_roles():
            for level in available_levels():
                with self.subTest(role=role, level=level):
                    self.assertEqual(len(get_question_plan(role, level)), 4)

    def test_lookup_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            get_question_plan("  BACKEND ENGINEER ", " INTERMEDIATE "),
            get_question_plan("backend engineer", "intermediate"),
        )

    def test_role_changes_the_question_plan(self) -> None:
        self.assertNotEqual(
            get_question_plan("backend engineer", "intermediate"),
            get_question_plan("data analyst", "intermediate"),
        )

    def test_unsupported_role_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported role.*backend engineer"):
            get_question_plan("astronaut", "intermediate")

    def test_unsupported_level_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported level.*beginner"):
            get_question_plan("backend engineer", "expert")


if __name__ == "__main__":
    unittest.main()
