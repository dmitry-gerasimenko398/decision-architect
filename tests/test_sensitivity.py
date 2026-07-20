"""Phase 5 tests for fixed-sample linear weight sensitivity."""

from __future__ import annotations

import copy
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from decision_architect.engine import analyze_file, analyze_model
from decision_architect.models import (
    Alternative,
    Criterion,
    MultiCriteriaAnalysisSettings,
    MultiCriteriaModel,
    TriangularDistribution,
)
from decision_architect.result_serialization import validate_multi_criteria_result
from decision_architect.sensitivity import (
    UndefinedWeightProportionsError,
    analyze_weight_sensitivity,
    recalculate_weights,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_EXAMPLE = PROJECT_ROOT / "examples" / "job-choice.json"


def make_model(
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
    *,
    samples: int = 7,
    alternative_ids: tuple[str, ...] = ("alpha", "beta"),
) -> MultiCriteriaModel:
    criteria = tuple(
        Criterion(
            id=criterion_id,
            name=name,
            description=f"Synthetic {name} criterion.",
            weight=weight,
            preference_direction="maximize",
            worst_anchor=0.0,
            best_anchor=1.0,
            unit="utility",
        )
        for criterion_id, name, weight in zip(
            ("target", "second", "third"),
            ("Target", "Second", "Third"),
            weights,
        )
    )
    alternatives = tuple(
        Alternative(
            id=alternative_id,
            name=alternative_id.title(),
            description="Synthetic sensitivity alternative.",
            constraint_results={},
            criterion_estimates={
                criterion.id: TriangularDistribution(0.5, 0.5, 0.5)
                for criterion in criteria
            },
        )
        for alternative_id in alternative_ids
    )
    return MultiCriteriaModel(
        model_version="1.0",
        model_type="multi_criteria",
        decision_id="sensitivity-test",
        title="Sensitivity test",
        description="Hand-checkable fixed-sample sensitivity fixture.",
        time_horizon="One decision",
        confirmed_by_user=True,
        assumptions=("Synthetic utility means are supplied directly in focused tests.",),
        notes=None,
        criteria=criteria,
        hard_constraints=(),
        alternatives=alternatives,
        analysis_settings=MultiCriteriaAnalysisSettings(
            random_seed=123,
            monte_carlo_samples=samples,
            clamp_utility=True,
        ),
    )


def upper_switch_means() -> dict[str, dict[str, float]]:
    return {
        "alpha": {"target": 0.0, "second": 1.0, "third": 1.0},
        "beta": {"target": 1.0, "second": 0.0, "third": 0.0},
    }


class WeightTransformationTests(unittest.TestCase):
    def test_recalculated_weights_sum_to_one(self) -> None:
        original = {"target": 0.4, "second": 0.2, "third": 0.4}
        for target_weight in (0.0, 0.25, 0.4, 0.9, 1.0):
            with self.subTest(target_weight=target_weight):
                recalculated = recalculate_weights(original, "target", target_weight)
                self.assertTrue(math.isclose(math.fsum(recalculated.values()), 1.0, abs_tol=1e-12))
                self.assertTrue(all(value >= 0.0 for value in recalculated.values()))

    def test_non_target_proportions_are_preserved(self) -> None:
        recalculated = recalculate_weights(
            {"target": 0.4, "second": 0.2, "third": 0.4},
            "target",
            0.7,
        )
        self.assertAlmostEqual(recalculated["third"] / recalculated["second"], 2.0)

    def test_weight_one_target_is_undefined(self) -> None:
        with self.assertRaises(UndefinedWeightProportionsError):
            recalculate_weights(
                {"target": 1.0, "second": 0.0, "third": 0.0},
                "target",
                0.5,
            )


class AnalyticalThresholdTests(unittest.TestCase):
    def test_hand_checkable_upper_threshold_is_one_half(self) -> None:
        result = analyze_weight_sensitivity(make_model(), upper_switch_means())
        target = result.criteria[0]
        self.assertIsNone(target.lower_switch)
        self.assertAlmostEqual(target.upper_switch.threshold_weight, 0.5, places=12)
        self.assertAlmostEqual(target.upper_switch.mean_utility_at_threshold, 0.5, places=12)
        self.assertEqual(target.upper_switch.new_winner_id, "beta")

    def test_lower_switch_is_detected(self) -> None:
        means = {
            "alpha": {"target": 1.0, "second": 0.0, "third": 0.0},
            "beta": {"target": 0.0, "second": 1.0, "third": 1.0},
        }
        result = analyze_weight_sensitivity(make_model((0.6, 0.2, 0.2)), means)
        switch = result.criteria[0].lower_switch
        self.assertAlmostEqual(switch.threshold_weight, 0.5, places=12)
        self.assertEqual(switch.new_winner_id, "beta")

    def test_robust_interval_contains_baseline_weight(self) -> None:
        criterion = analyze_weight_sensitivity(make_model(), upper_switch_means()).criteria[0]
        self.assertLessEqual(criterion.robust_interval.minimum_weight, criterion.baseline_weight)
        self.assertGreaterEqual(criterion.robust_interval.maximum_weight, criterion.baseline_weight)

    def test_no_switch_uses_full_closed_interval(self) -> None:
        means = {
            "alpha": {"target": 0.8, "second": 0.8, "third": 0.8},
            "beta": {"target": 0.2, "second": 0.2, "third": 0.2},
        }
        criterion = analyze_weight_sensitivity(make_model(), means).criteria[0]
        self.assertIsNone(criterion.lower_switch)
        self.assertIsNone(criterion.upper_switch)
        self.assertEqual(criterion.robust_interval.minimum_weight, 0.0)
        self.assertEqual(criterion.robust_interval.maximum_weight, 1.0)
        self.assertTrue(criterion.robust_interval.minimum_inclusive)
        self.assertTrue(criterion.robust_interval.maximum_inclusive)

    def test_baseline_weight_zero_is_analyzable(self) -> None:
        result = analyze_weight_sensitivity(
            make_model((0.0, 0.5, 0.5)),
            upper_switch_means(),
        )
        self.assertEqual(result.criteria[0].status, "analyzed")
        self.assertAlmostEqual(result.criteria[0].upper_switch.threshold_weight, 0.5)

    def test_baseline_weight_one_is_marked_not_analyzable(self) -> None:
        means = {
            "alpha": {"target": 1.0, "second": 0.0, "third": 0.0},
            "beta": {"target": 0.0, "second": 1.0, "third": 1.0},
        }
        result = analyze_weight_sensitivity(make_model((1.0, 0.0, 0.0)), means)
        self.assertEqual(result.criteria[0].status, "not_analyzable_baseline_weight_one")
        self.assertIsNone(result.criteria[0].robust_interval)

    def test_parallel_lines_do_not_create_false_threshold(self) -> None:
        means = {
            "alpha": {"target": 0.8, "second": 0.8, "third": 0.8},
            "beta": {"target": 0.4, "second": 0.4, "third": 0.4},
        }
        criterion = analyze_weight_sensitivity(make_model(), means).criteria[0]
        self.assertIsNone(criterion.lower_switch)
        self.assertIsNone(criterion.upper_switch)

    def test_baseline_top_tie_has_no_arbitrary_winner(self) -> None:
        means = {
            "alpha": {"target": 0.5, "second": 0.5, "third": 0.5},
            "beta": {"target": 0.5, "second": 0.5, "third": 0.5},
        }
        result = analyze_weight_sensitivity(make_model(), means)
        self.assertEqual(result.status, "not_applicable_baseline_tie")
        self.assertIsNone(result.baseline_winner_id)
        self.assertEqual(result.baseline_tied_alternative_ids, ("alpha", "beta"))

    def test_only_one_feasible_alternative_is_not_applicable(self) -> None:
        result = analyze_weight_sensitivity(
            make_model(),
            {"alpha": {"target": 0.5, "second": 0.5, "third": 0.5}},
        )
        self.assertEqual(result.status, "not_applicable_only_one_feasible_alternative")

    def test_no_feasible_alternative_is_not_applicable(self) -> None:
        result = analyze_weight_sensitivity(make_model(), {})
        self.assertEqual(result.status, "not_applicable_no_feasible_alternatives")
        self.assertIsNone(result.baseline_winner_id)

    def test_crossing_at_zero_is_recorded_as_boundary_tie(self) -> None:
        means = {
            "alpha": {"target": 1.0, "second": 0.0, "third": 0.0},
            "beta": {"target": 0.0, "second": 0.0, "third": 0.0},
        }
        switch = analyze_weight_sensitivity(make_model(), means).criteria[0].lower_switch
        self.assertEqual(switch.threshold_weight, 0.0)
        self.assertEqual(switch.change_type, "boundary_tie")
        self.assertTrue(switch.verified)

    def test_crossing_at_one_is_recorded_as_boundary_tie(self) -> None:
        means = {
            "alpha": {"target": 0.0, "second": 1.0, "third": 1.0},
            "beta": {"target": 0.0, "second": 0.0, "third": 0.0},
        }
        switch = analyze_weight_sensitivity(make_model(), means).criteria[0].upper_switch
        self.assertEqual(switch.threshold_weight, 1.0)
        self.assertEqual(switch.change_type, "boundary_tie")
        self.assertTrue(switch.verified)

    def test_threshold_verification_checks_both_sides(self) -> None:
        switch = analyze_weight_sensitivity(make_model(), upper_switch_means()).criteria[0].upper_switch
        self.assertLess(switch.lower_probe_weight, switch.threshold_weight)
        self.assertGreater(switch.upper_probe_weight, switch.threshold_weight)
        self.assertEqual(switch.lower_probe_leader_ids, ("alpha",))
        self.assertEqual(switch.upper_probe_leader_ids, ("beta",))
        self.assertTrue(switch.verified)

    def test_nearly_simultaneous_competitor_crossings_are_explicit(self) -> None:
        model = make_model(alternative_ids=("alpha", "beta", "gamma"))
        means = {
            "alpha": {"target": 0.0, "second": 1.0, "third": 1.0},
            "beta": {"target": 1.0, "second": 0.0, "third": 0.0},
            "gamma": {"target": 0.999999999998, "second": 0.0, "third": 0.0},
        }
        switch = analyze_weight_sensitivity(model, means).criteria[0].upper_switch
        self.assertAlmostEqual(switch.threshold_weight, 0.5, places=10)
        self.assertEqual(
            set(switch.tie_alternative_ids),
            {"alpha", "beta", "gamma"},
        )
        self.assertTrue(switch.verified)


class EngineIntegrationTests(unittest.TestCase):
    def test_baseline_sensitivity_winner_matches_ordinary_winner(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        self.assertEqual(
            result["sensitivity"]["baseline_winner_id"],
            result["recommendation"]["alternative_id"],
        )

    def test_job_example_closest_switch_is_salary(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        candidates = []
        for criterion in result["sensitivity"]["criteria"]:
            for field in ("lower_switch", "upper_switch"):
                switch = criterion[field]
                if switch and switch["change_type"] == "winner_switch":
                    candidates.append(
                        (
                            abs(switch["threshold_weight"] - criterion["baseline_weight"]),
                            criterion["criterion_id"],
                            switch,
                        )
                    )
        distance, criterion_id, switch = min(candidates)
        self.assertEqual(criterion_id, "salary")
        self.assertAlmostEqual(switch["threshold_weight"], 0.8435903602946223)
        self.assertAlmostEqual(distance, 0.4935903602946223)

    def test_sensitivity_reuses_one_fixed_sample_without_resampling(self) -> None:
        model = make_model(samples=5)
        with patch("decision_architect.multi_criteria.random.Random") as random_factory:
            random_factory.return_value.triangular.return_value = 0.5
            analyze_model(model)
        self.assertEqual(
            random_factory.return_value.triangular.call_count,
            5 * len(model.alternatives) * len(model.criteria),
        )

    def test_excluded_alternative_never_participates(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        excluded_ids = {item["alternative_id"] for item in result["excluded_alternatives"]}
        self.assertIn("local-nonprofit", excluded_ids)
        for alternative in result["alternative_results"]:
            self.assertNotIn(alternative["alternative_id"], excluded_ids)
        for criterion in result["sensitivity"]["criteria"]:
            for switch_name in ("lower_switch", "upper_switch"):
                switch = criterion[switch_name]
                if switch:
                    participating = set(switch["tie_alternative_ids"])
                    participating.update(switch["new_tied_winner_ids"])
                    if switch["new_winner_id"]:
                        participating.add(switch["new_winner_id"])
                    self.assertTrue(participating.isdisjoint(excluded_ids))

    def test_repeated_runs_are_byte_equivalent_as_documents(self) -> None:
        self.assertEqual(analyze_file(JOB_EXAMPLE), analyze_file(JOB_EXAMPLE))

    def test_generated_result_matches_extended_contract(self) -> None:
        result = analyze_file(JOB_EXAMPLE)
        self.assertEqual(validate_multi_criteria_result(result), [])
        self.assertIn("criterion_mean_utilities", result["alternative_results"][0])
        self.assertIn("weighted_criterion_contributions", result["alternative_results"][0])
        self.assertEqual(result["sensitivity"]["method"], "fixed_sample_linear_weight_sensitivity")

    def test_result_validator_rejects_contradictory_sensitivity_data(self) -> None:
        valid = analyze_file(JOB_EXAMPLE)
        mutations = []

        empty_tie = copy.deepcopy(valid)
        empty_tie["sensitivity"]["criteria"][0]["upper_switch"]["tie_alternative_ids"] = []
        mutations.append(empty_tie)

        negative_epsilon = copy.deepcopy(valid)
        negative_epsilon["sensitivity"]["criteria"][0]["upper_switch"]["verification_epsilon"] = -1e-6
        mutations.append(negative_epsilon)

        reversed_probes = copy.deepcopy(valid)
        switch = reversed_probes["sensitivity"]["criteria"][0]["upper_switch"]
        switch["lower_probe_weight"] = 1.0
        switch["upper_probe_weight"] = 0.0
        mutations.append(reversed_probes)

        baseline_threshold = copy.deepcopy(valid)
        criterion = baseline_threshold["sensitivity"]["criteria"][0]
        criterion["upper_switch"]["threshold_weight"] = criterion["baseline_weight"]
        mutations.append(baseline_threshold)

        impossible_status = copy.deepcopy(valid)
        impossible_status["sensitivity"]["status"] = "not_applicable_no_feasible_alternatives"
        mutations.append(impossible_status)

        for index, mutated in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertTrue(validate_multi_criteria_result(mutated))


if __name__ == "__main__":
    unittest.main()
