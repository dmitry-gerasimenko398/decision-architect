"""Phase 3 tests for the deterministic multi-criteria engine."""

from __future__ import annotations

import copy
import json
import random
import unittest
from pathlib import Path

from decision_architect.engine import analyze_file, analyze_model
from decision_architect.models import (
    Criterion,
    HardConstraint,
    MultiCriteriaModel,
    TriangularDistribution,
    model_from_validated_dict,
)
from decision_architect.multi_criteria import (
    ConstraintDeclarationMismatchError,
    evaluate_constraint,
    normalize_utility,
    triangular_raw_mean,
)
from decision_architect.result_serialization import validate_multi_criteria_result
from decision_architect.validation import validate_model_or_raise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_EXAMPLE = PROJECT_ROOT / "examples" / "job-choice.json"


def load_job_data(*, samples: int = 500) -> dict:
    data = json.loads(JOB_EXAMPLE.read_text(encoding="utf-8"))
    data["analysis_settings"]["monte_carlo_samples"] = samples
    return data


def typed_model(data: dict) -> MultiCriteriaModel:
    validate_model_or_raise(data)
    model = model_from_validated_dict(data)
    if not isinstance(model, MultiCriteriaModel):
        raise AssertionError("Expected a multi-criteria model")
    return model


def two_alternative_model(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    samples: int = 500,
    seed: int = 123,
    constraint: dict | None = None,
    constraint_results: tuple[bool, bool] = (True, True),
) -> dict:
    constraints = [constraint] if constraint else []
    result_maps = (
        {constraint["id"]: constraint_results[0]} if constraint else {},
        {constraint["id"]: constraint_results[1]} if constraint else {},
    )
    return {
        "model_version": "1.0",
        "model_type": "multi_criteria",
        "decision_id": "two-alternative-test",
        "title": "Two alternative test",
        "description": "Small deterministic engine fixture.",
        "time_horizon": "One decision",
        "confirmed_by_user": True,
        "assumptions": ["Synthetic test data."],
        "criteria": [
            {
                "id": "primary",
                "name": "Primary",
                "description": "Primary test criterion.",
                "weight": 1.0,
                "preference_direction": "maximize",
                "worst_anchor": 0.0,
                "best_anchor": 1.0,
                "unit": "utility input",
            },
            {
                "id": "secondary",
                "name": "Secondary",
                "description": "Zero-weight criterion retained to exercise the multi-criteria contract.",
                "weight": 0.0,
                "preference_direction": "maximize",
                "worst_anchor": 0.0,
                "best_anchor": 1.0,
                "unit": "utility input",
            },
        ],
        "hard_constraints": constraints,
        "alternatives": [
            {
                "id": "alpha",
                "name": "Alpha",
                "description": "First option.",
                "constraint_results": result_maps[0],
                "criterion_estimates": {
                    "primary": {
                        "minimum": first[0],
                        "most_likely": first[1],
                        "maximum": first[2],
                    },
                    "secondary": {"minimum": 0.5, "most_likely": 0.5, "maximum": 0.5},
                },
            },
            {
                "id": "beta",
                "name": "Beta",
                "description": "Second option.",
                "constraint_results": result_maps[1],
                "criterion_estimates": {
                    "primary": {
                        "minimum": second[0],
                        "most_likely": second[1],
                        "maximum": second[2],
                    },
                    "secondary": {"minimum": 0.5, "most_likely": 0.5, "maximum": 0.5},
                },
            },
        ],
        "analysis_settings": {
            "random_seed": seed,
            "monte_carlo_samples": samples,
            "clamp_utility": True,
        },
    }


class FormulaTests(unittest.TestCase):
    def test_analytical_triangular_mean_is_correct(self) -> None:
        distribution = TriangularDistribution(2.0, 5.0, 11.0)
        self.assertEqual(triangular_raw_mean(distribution), 6.0)

    def test_maximize_style_anchors_normalize_correctly(self) -> None:
        criterion = Criterion("c", "C", "C", 1.0, "maximize", 0.0, 10.0, "points")
        self.assertEqual(normalize_utility(7.5, criterion), (0.75, 0))

    def test_minimize_style_anchors_normalize_correctly(self) -> None:
        criterion = Criterion("c", "C", "C", 1.0, "minimize", 100.0, 0.0, "minutes")
        self.assertEqual(normalize_utility(25.0, criterion), (0.75, 0))

    def test_utility_values_are_clamped(self) -> None:
        criterion = Criterion("c", "C", "C", 1.0, "maximize", 0.0, 10.0, "points")
        self.assertEqual(normalize_utility(-2.0, criterion), (0.0, -1))
        self.assertEqual(normalize_utility(12.0, criterion), (1.0, 1))

    def test_constraint_less_than_or_equal_uses_maximum(self) -> None:
        constraint = HardConstraint("cap", "Cap", "Cap", "primary", "<=", 5.0)
        passing = evaluate_constraint(constraint, TriangularDistribution(1.0, 3.0, 5.0))
        failing = evaluate_constraint(constraint, TriangularDistribution(1.0, 3.0, 5.1))
        self.assertTrue(passing.passed)
        self.assertFalse(failing.passed)
        self.assertEqual(failing.boundary_name, "maximum")

    def test_constraint_greater_than_or_equal_uses_minimum(self) -> None:
        constraint = HardConstraint("floor", "Floor", "Floor", "primary", ">=", 5.0)
        passing = evaluate_constraint(constraint, TriangularDistribution(5.0, 6.0, 7.0))
        failing = evaluate_constraint(constraint, TriangularDistribution(4.9, 6.0, 7.0))
        self.assertTrue(passing.passed)
        self.assertFalse(failing.passed)
        self.assertEqual(failing.boundary_name, "minimum")

    def test_strict_equality_and_inequality_constraint_rules(self) -> None:
        cases = [
            (HardConstraint("lt", "LT", "LT", "primary", "<", 5.0), (1.0, 3.0, 5.0), False),
            (HardConstraint("gt", "GT", "GT", "primary", ">", 5.0), (5.0, 6.0, 7.0), False),
            (HardConstraint("eq", "EQ", "EQ", "primary", "==", 5.0), (5.0, 5.0, 5.0), True),
            (HardConstraint("eq", "EQ", "EQ", "primary", "==", 5.0), (5.0, 5.0, 5.1), False),
            (HardConstraint("ne", "NE", "NE", "primary", "!=", 5.0), (5.0, 5.0, 5.0), False),
            (HardConstraint("ne", "NE", "NE", "primary", "!=", 5.0), (5.0, 5.0, 5.1), True),
        ]
        for constraint, values, expected in cases:
            with self.subTest(operator=constraint.operator, values=values):
                self.assertEqual(
                    evaluate_constraint(constraint, TriangularDistribution(*values)).passed,
                    expected,
                )


class EngineBehaviorTests(unittest.TestCase):
    def test_valid_job_example_calculates_successfully(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["recommendation"]["alternative_id"], "remote-startup")

    def test_same_seed_repeats_exactly(self) -> None:
        model = typed_model(load_job_data(samples=200))
        self.assertEqual(analyze_model(model), analyze_model(model))

    def test_changing_seed_changes_simulated_details(self) -> None:
        first_data = two_alternative_model((0.51, 0.51, 0.51), (0.0, 0.5, 1.0), samples=30, seed=1)
        second_data = copy.deepcopy(first_data)
        second_data["analysis_settings"]["random_seed"] = 2
        first = analyze_model(typed_model(first_data))
        second = analyze_model(typed_model(second_data))
        self.assertNotEqual(
            first["alternative_results"][1]["monte_carlo_mean_utility"],
            second["alternative_results"][1]["monte_carlo_mean_utility"],
        )

    def test_engine_does_not_change_global_random_state(self) -> None:
        random.seed(9876)
        expected = random.random()
        random.seed(9876)
        analyze_model(typed_model(two_alternative_model((0.8, 0.8, 0.8), (0.2, 0.2, 0.2), samples=5)))
        self.assertEqual(random.random(), expected)

    def test_clamp_warnings_and_diagnostics_are_recorded(self) -> None:
        data = two_alternative_model((2.0, 2.0, 2.0), (0.5, 0.5, 0.5), samples=20)
        result = analyze_model(typed_model(data))
        alpha = next(item for item in result["alternative_results"] if item["alternative_id"] == "alpha")
        self.assertTrue(result["warnings"])
        self.assertEqual(alpha["analytical_utility"], 1.0)
        self.assertEqual(alpha["clamp_diagnostics"][0]["sampled_above_one_count"], 20)
        self.assertTrue(alpha["clamp_diagnostics"][0]["analytical_mean_clamped"])

    def test_excluded_alternative_receives_no_utility_result(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        feasible_ids = {item["alternative_id"] for item in result["alternative_results"]}
        excluded_ids = {item["alternative_id"] for item in result["excluded_alternatives"]}
        self.assertNotIn("local-nonprofit", feasible_ids)
        self.assertIn("local-nonprofit", excluded_ids)
        excluded = result["excluded_alternatives"][0]
        self.assertNotIn("monte_carlo_mean_utility", excluded)

    def test_one_feasible_alternative_status(self) -> None:
        constraint = {
            "id": "floor",
            "name": "Floor",
            "description": "All values must be at least 0.5.",
            "criterion_id": "primary",
            "operator": ">=",
            "threshold": 0.5,
        }
        data = two_alternative_model(
            (0.6, 0.7, 0.8),
            (0.4, 0.6, 0.8),
            constraint=constraint,
            constraint_results=(True, False),
        )
        result = analyze_model(typed_model(data))
        self.assertEqual(result["recommendation"]["status"], "only_feasible_alternative")
        self.assertEqual(result["alternative_results"][0]["win_probability"], 1.0)

    def test_zero_feasible_alternatives_status(self) -> None:
        constraint = {
            "id": "floor",
            "name": "Floor",
            "description": "All values must be at least 0.5.",
            "criterion_id": "primary",
            "operator": ">=",
            "threshold": 0.5,
        }
        data = two_alternative_model(
            (0.1, 0.2, 0.4),
            (0.2, 0.3, 0.49),
            constraint=constraint,
            constraint_results=(False, False),
        )
        result = analyze_model(typed_model(data))
        self.assertEqual(result["recommendation"]["status"], "no_feasible_alternative")
        self.assertEqual(result["alternative_results"], [])

    def test_constraint_declaration_mismatch_stops_analysis(self) -> None:
        constraint = {
            "id": "floor",
            "name": "Floor",
            "description": "All values must be at least 0.5.",
            "criterion_id": "primary",
            "operator": ">=",
            "threshold": 0.5,
        }
        data = two_alternative_model(
            (0.6, 0.7, 0.8),
            (0.4, 0.6, 0.8),
            constraint=constraint,
            constraint_results=(True, True),
        )
        with self.assertRaises(ConstraintDeclarationMismatchError):
            analyze_model(typed_model(data))

    def test_strong_leader_is_recommended(self) -> None:
        data = two_alternative_model((0.9, 0.9, 0.9), (0.1, 0.1, 0.1), samples=20)
        result = analyze_model(typed_model(data))
        self.assertEqual(result["recommendation"]["status"], "recommended")
        self.assertEqual(result["recommendation"]["leading_win_probability"], 1.0)

    def test_unique_leader_below_sixty_percent_is_close_call(self) -> None:
        data = two_alternative_model((0.51, 0.51, 0.51), (0.0, 0.5, 1.0), samples=2000, seed=7)
        result = analyze_model(typed_model(data))
        self.assertEqual(result["recommendation"]["status"], "close_call")
        self.assertLess(result["recommendation"]["leading_win_probability"], 0.60)

    def test_equal_simulation_values_split_win_credit_and_mean_tie(self) -> None:
        data = two_alternative_model((0.5, 0.5, 0.5), (0.5, 0.5, 0.5), samples=9)
        result = analyze_model(typed_model(data))
        probabilities = [item["win_probability"] for item in result["alternative_results"]]
        self.assertEqual(probabilities, [0.5, 0.5])
        self.assertEqual(result["recommendation"]["status"], "mean_utility_tie")
        self.assertEqual(result["recommendation"]["tied_alternative_ids"], ["alpha", "beta"])

    def test_win_probabilities_sum_to_one(self) -> None:
        result = analyze_model(typed_model(load_job_data(samples=100)))
        self.assertAlmostEqual(
            sum(item["win_probability"] for item in result["alternative_results"]),
            1.0,
            places=12,
        )

    def test_result_matches_phase_2_result_contract(self) -> None:
        result = analyze_model(typed_model(load_job_data(samples=100)))
        self.assertEqual(validate_multi_criteria_result(result), [])
        schema = json.loads(
            (PROJECT_ROOT / "schemas" / "decision-result-v1.schema.json").read_text(encoding="utf-8")
        )
        required = set(schema["$defs"]["multiCriteriaResult"]["allOf"][1]["required"])
        self.assertTrue(required.issubset(result))

    def test_results_use_required_deterministic_display_order(self) -> None:
        result = analyze_model(
            typed_model(two_alternative_model((0.1, 0.1, 0.1), (0.9, 0.9, 0.9), samples=5))
        )
        self.assertEqual(
            [item["alternative_id"] for item in result["alternative_results"]],
            ["beta", "alpha"],
        )


if __name__ == "__main__":
    unittest.main()
