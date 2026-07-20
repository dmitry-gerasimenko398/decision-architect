"""Phase 4 tests for finite-horizon sequential exploration."""

from __future__ import annotations

import copy
import json
import math
import random
import unittest
from pathlib import Path

from decision_architect.engine import analyze_file
from decision_architect.models import (
    SequentialExplorationModel,
    TriangularDistribution,
    model_from_validated_dict,
)
from decision_architect.result_serialization import (
    sequential_exploration_result_to_dict,
    validate_sequential_exploration_result,
)
from decision_architect.sequential_exploration import (
    SequentialDynamicProgram,
    analyze_sequential_exploration,
    compare_actions,
    inverse_triangular_cdf,
    midpoint_quantile_nodes,
)
from decision_architect.validation import validate_model_or_raise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LONG_EXAMPLE = PROJECT_ROOT / "examples" / "feynman-restaurant.json"
SHORT_EXAMPLE = PROJECT_ROOT / "examples" / "feynman-restaurant-short-horizon.json"


def load_data(path: Path = LONG_EXAMPLE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def typed_model(data: dict) -> SequentialExplorationModel:
    validate_model_or_raise(data)
    model = model_from_validated_dict(data)
    if not isinstance(model, SequentialExplorationModel):
        raise AssertionError("Expected a sequential-exploration model")
    return model


class NumericalMethodTests(unittest.TestCase):
    def test_zero_horizon_base_value_is_zero(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0))
        self.assertEqual(program.optimal_value(0, 10, 6.5), 0.0)

    def test_no_unseen_options_forces_exploitation(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0))
        values = program.action_values(3, 0, 6.5)
        self.assertEqual(values.recommended_action, "exploit")
        self.assertIsNone(values.explore_value)
        self.assertEqual(values.exploit_value, 19.5)

    def test_one_opportunity_compares_known_value_with_expected_new_value(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0))
        values = program.action_values(1, 5, 6.5)
        self.assertAlmostEqual(values.exploit_value, 6.5, places=10)
        self.assertAlmostEqual(values.explore_value, 6.0, places=10)
        self.assertEqual(values.recommended_action, "exploit")

    def test_degenerate_distribution_works_and_exact_equality_is_indifferent(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(6.5, 6.5, 6.5))
        values = program.action_values(4, 3, 6.5)
        self.assertEqual(values.recommended_action, "indifferent")
        self.assertAlmostEqual(values.exploit_value, values.explore_value)

    def test_action_comparison_uses_explicit_tolerance(self) -> None:
        self.assertEqual(compare_actions(1.0, 1.0 + 5e-11), "indifferent")
        self.assertEqual(compare_actions(1.0, 1.0 + 2e-10), "explore")
        self.assertEqual(compare_actions(1.0, 1.0 - 2e-10), "exploit")

    def test_inverse_triangular_cdf_at_representative_quantiles(self) -> None:
        distribution = TriangularDistribution(0.0, 5.0, 10.0)
        self.assertEqual(inverse_triangular_cdf(0.0, distribution), 0.0)
        self.assertAlmostEqual(inverse_triangular_cdf(0.125, distribution), 2.5)
        self.assertAlmostEqual(inverse_triangular_cdf(0.5, distribution), 5.0)
        self.assertAlmostEqual(inverse_triangular_cdf(0.875, distribution), 7.5)
        self.assertEqual(inverse_triangular_cdf(1.0, distribution), 10.0)

    def test_quadrature_nodes_stay_within_distribution_bounds(self) -> None:
        distribution = TriangularDistribution(2.0, 3.0, 10.0)
        nodes = midpoint_quantile_nodes(distribution, 101)
        self.assertEqual(len(nodes), 101)
        self.assertGreater(min(nodes), distribution.minimum)
        self.assertLess(max(nodes), distribution.maximum)

    def test_increasing_best_known_value_cannot_reduce_optimal_value(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0), 51)
        lower = program.optimal_value(5, 5, 5.5)
        higher = program.optimal_value(5, 5, 6.5)
        self.assertGreaterEqual(higher, lower)

    def test_nonnegative_extra_opportunity_cannot_reduce_total_value(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0), 51)
        values = [program.optimal_value(horizon, 5, 6.5) for horizon in range(1, 6)]
        self.assertTrue(all(later >= earlier for earlier, later in zip(values, values[1:])))

    def test_exploration_consumes_the_only_unseen_option(self) -> None:
        distribution = TriangularDistribution(0.0, 0.0, 10.0)
        program = SequentialDynamicProgram(distribution, 51)
        values = program.action_values(2, 1, 0.0)
        hand_calculated = math.fsum(value + value for value in program.nodes) / 51
        self.assertAlmostEqual(values.explore_value, hand_calculated, places=10)

    def test_memoization_keys_use_twelve_decimal_places(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0), 11)
        first = 6.5000000000001
        second = 6.5000000000002
        self.assertEqual(
            program.canonical_best_known(first),
            program.canonical_best_known(second),
        )
        program.optimal_value(2, 1, first)
        state_count = program.memoized_state_count
        program.optimal_value(2, 1, second)
        self.assertEqual(program.memoized_state_count, state_count)

    def test_large_exploit_only_horizon_avoids_python_recursion_limit(self) -> None:
        program = SequentialDynamicProgram(TriangularDistribution(2.0, 6.0, 10.0), 11)
        self.assertEqual(program.optimal_value(1000, 0, 6.5), 6500.0)


class DemonstrationTests(unittest.TestCase):
    def test_long_horizon_recommends_explore(self) -> None:
        self.assertEqual(analyze_file(LONG_EXAMPLE)["recommended_action"], "explore")

    def test_short_horizon_recommends_exploit(self) -> None:
        self.assertEqual(analyze_file(SHORT_EXAMPLE)["recommended_action"], "exploit")

    def test_examples_differ_only_in_horizon_and_descriptive_metadata(self) -> None:
        long_data = load_data(LONG_EXAMPLE)
        short_data = load_data(SHORT_EXAMPLE)
        descriptive = {"decision_id", "title", "description", "time_horizon", "notes"}
        for data in (long_data, short_data):
            for field in descriptive:
                data.pop(field, None)
            data["state"] = dict(data["state"])
            data["state"].pop("remaining_opportunities")
        self.assertEqual(long_data, short_data)

    def test_policy_contains_every_requested_horizon(self) -> None:
        result = analyze_file(LONG_EXAMPLE)
        self.assertEqual(
            [row["remaining_opportunities"] for row in result["policy_by_remaining_opportunities"]],
            list(range(1, 9)),
        )

    def test_demonstration_action_switch_occurs_at_three(self) -> None:
        result = analyze_file(LONG_EXAMPLE)
        self.assertEqual(
            result["action_switch_points"],
            [{
                "remaining_opportunities": 3,
                "previous_action": "exploit",
                "recommended_action": "explore",
            }],
        )

    def test_51_and_101_point_results_are_close(self) -> None:
        data_51 = load_data()
        data_51["analysis_settings"]["quadrature_points"] = 51
        outcome_51 = analyze_sequential_exploration(typed_model(data_51))
        outcome_101 = analyze_sequential_exploration(typed_model(load_data()))
        self.assertAlmostEqual(
            outcome_51.expected_total_utility,
            outcome_101.expected_total_utility,
            delta=0.02,
        )
        self.assertEqual(
            outcome_51.current_action_values.recommended_action,
            outcome_101.current_action_values.recommended_action,
        )

    def test_engine_is_exactly_deterministic_across_repeated_runs(self) -> None:
        self.assertEqual(analyze_file(LONG_EXAMPLE), analyze_file(LONG_EXAMPLE))

    def test_engine_does_not_change_global_random_state(self) -> None:
        random.seed(2468)
        expected = random.random()
        random.seed(2468)
        analyze_file(LONG_EXAMPLE)
        self.assertEqual(random.random(), expected)

    def test_sequential_result_matches_result_contract(self) -> None:
        result = analyze_file(LONG_EXAMPLE)
        self.assertEqual(validate_sequential_exploration_result(result), [])
        schema = json.loads(
            (PROJECT_ROOT / "schemas" / "decision-result-v1.schema.json").read_text(encoding="utf-8")
        )
        required = set(schema["$defs"]["sequentialExplorationResult"]["allOf"][1]["required"])
        self.assertTrue(required.issubset(result))

    def test_missing_settings_uses_documented_default_101(self) -> None:
        data = load_data()
        data.pop("analysis_settings")
        model = typed_model(data)
        self.assertEqual(model.analysis_settings.quadrature_points, 101)

    def test_serialized_no_unseen_options_records_unavailable_exploration(self) -> None:
        data = load_data()
        data["state"]["unseen_options_remaining"] = 0
        outcome = analyze_sequential_exploration(typed_model(data))
        result = sequential_exploration_result_to_dict(outcome)
        self.assertEqual(result["recommended_action"], "exploit")
        self.assertEqual(result["recommendation_status"], "exploration_unavailable")
        self.assertIsNone(result["explore_value"])
        self.assertIsNone(result["action_advantage"])

    def test_result_validator_rejects_incomplete_switch_points(self) -> None:
        result = analyze_file(LONG_EXAMPLE)
        result["action_switch_points"] = []
        errors = validate_sequential_exploration_result(result)
        self.assertTrue(any("every policy action change" in error for error in errors))

    def test_result_validator_reports_malformed_fields_without_crashing(self) -> None:
        malformed_method = copy.deepcopy(analyze_file(LONG_EXAMPLE))
        malformed_method["method"] = []
        self.assertTrue(validate_sequential_exploration_result(malformed_method))

        missing_advantage = copy.deepcopy(analyze_file(LONG_EXAMPLE))
        missing_advantage["action_advantage"] = None
        self.assertTrue(validate_sequential_exploration_result(missing_advantage))


if __name__ == "__main__":
    unittest.main()
