"""Deterministic support tests for adaptive-interview structure."""

from __future__ import annotations

import unittest

from decision_architect.interview import (
    classify_condition,
    safe_identifier,
    select_model_type,
    swing_points_to_weights,
    triangle_contradiction,
)


class InterviewSupportTests(unittest.TestCase):
    def test_safe_identifier_preserves_readable_words(self) -> None:
        self.assertEqual(safe_identifier("Remote Startup!"), "remote-startup")
        self.assertEqual(safe_identifier("Café & Growth"), "cafe-growth")

    def test_safe_identifier_cannot_create_a_path(self) -> None:
        identifier = safe_identifier(r"..\..\outside/session")
        self.assertEqual(identifier, "outside-session")
        self.assertNotIn("/", identifier)
        self.assertNotIn("\\", identifier)
        self.assertNotIn("..", identifier)

    def test_model_selection_recognizes_sequential_structure(self) -> None:
        result = select_model_type(
            repeated_choice=True,
            trying_new_produces_information=True,
            discovered_option_reusable=True,
            finite_opportunities=True,
            known_alternatives=False,
            competing_criteria=False,
        )
        self.assertEqual(result.model_type, "sequential_exploration")
        self.assertIn("finite horizon", result.explanation)

    def test_model_selection_recognizes_one_time_comparison(self) -> None:
        result = select_model_type(
            repeated_choice=False,
            trying_new_produces_information=False,
            discovered_option_reusable=False,
            finite_opportunities=False,
            known_alternatives=True,
            competing_criteria=True,
        )
        self.assertEqual(result.model_type, "multi_criteria")

    def test_unclear_structure_returns_one_classification_question(self) -> None:
        result = select_model_type(
            repeated_choice=None,
            trying_new_produces_information=None,
            discovered_option_reusable=None,
            finite_opportunities=None,
            known_alternatives=None,
            competing_criteria=None,
        )
        self.assertIsNone(result.model_type)
        self.assertIn("only once", result.clarification_question or "")

    def test_unsupported_structure_is_not_forced(self) -> None:
        result = select_model_type(
            repeated_choice=True,
            trying_new_produces_information=False,
            discovered_option_reusable=False,
            finite_opportunities=False,
            known_alternatives=False,
            competing_criteria=False,
        )
        self.assertIsNone(result.model_type)
        self.assertIsNone(result.clarification_question)

    def test_hard_constraint_and_preference_remain_distinct(self) -> None:
        self.assertEqual(classify_condition(eliminate_if_violated=True), "hard_constraint")
        self.assertEqual(classify_condition(eliminate_if_violated=False), "preference")

    def test_contradictory_triangular_values_get_targeted_correction(self) -> None:
        self.assertIn("minimum is greater", triangle_contradiction(8, 6, 10) or "")
        self.assertIn("most likely", triangle_contradiction(2, 11, 10) or "")
        self.assertIsNone(triangle_contradiction(2, 6, 10))

    def test_swing_points_create_reproducible_weights(self) -> None:
        weights = swing_points_to_weights({"salary": 40, "balance": 35, "growth": 25})
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertEqual(weights["salary"], 0.4)

    def test_swing_weighting_does_not_invent_missing_importance(self) -> None:
        with self.assertRaises(ValueError):
            swing_points_to_weights({"salary": 0, "balance": 0})


if __name__ == "__main__":
    unittest.main()
