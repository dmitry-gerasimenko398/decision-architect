"""Serialize and self-check Decision Architect result-v1 JSON documents."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .multi_criteria import (
    CLOSE_CALL_THRESHOLD,
    NUMERICAL_TOLERANCE,
    MultiCriteriaOutcome,
)
from .statistics import PERCENTILE_METHOD
from .sequential_exploration import (
    ACTION_COMPARISON_TOLERANCE,
    MEMOIZATION_DECIMAL_PLACES,
    SequentialExplorationOutcome,
    compare_actions,
)
from .sensitivity import WinnerSwitch, WeightSensitivityOutcome
from .text_io import atomic_write_utf8_lf


RESULT_VERSION = "1.0"
ENGINE_VERSION = "0.4.0"


def _winner_switch_to_dict(switch: WinnerSwitch | None) -> dict[str, Any] | None:
    if switch is None:
        return None
    return {
        "direction": switch.direction,
        "change_type": switch.change_type,
        "threshold_weight": switch.threshold_weight,
        "new_winner_id": switch.new_winner_id,
        "new_tied_winner_ids": list(switch.new_tied_winner_ids),
        "tie_alternative_ids": list(switch.tie_alternative_ids),
        "mean_utility_at_threshold": switch.mean_utility_at_threshold,
        "verified": switch.verified,
        "verification_epsilon": switch.verification_epsilon,
        "lower_probe_weight": switch.lower_probe_weight,
        "lower_probe_leader_ids": list(switch.lower_probe_leader_ids),
        "upper_probe_weight": switch.upper_probe_weight,
        "upper_probe_leader_ids": list(switch.upper_probe_leader_ids),
        "explanation": switch.explanation,
    }


def _sensitivity_to_dict(sensitivity: WeightSensitivityOutcome) -> dict[str, Any]:
    return {
        "status": sensitivity.status,
        "method": sensitivity.method,
        "ranking_basis": sensitivity.ranking_basis,
        "random_seed": sensitivity.random_seed,
        "simulation_count": sensitivity.simulation_count,
        "fixed_sample_reused": sensitivity.fixed_sample_reused,
        "numerical_tolerance": sensitivity.numerical_tolerance,
        "verification_epsilon_rule": sensitivity.verification_epsilon_rule,
        "baseline_winner_id": sensitivity.baseline_winner_id,
        "baseline_tied_alternative_ids": list(
            sensitivity.baseline_tied_alternative_ids
        ),
        "criteria": [
            {
                "criterion_id": criterion.criterion_id,
                "baseline_weight": criterion.baseline_weight,
                "status": criterion.status,
                "robust_interval": (
                    {
                        "minimum_weight": criterion.robust_interval.minimum_weight,
                        "maximum_weight": criterion.robust_interval.maximum_weight,
                        "minimum_inclusive": criterion.robust_interval.minimum_inclusive,
                        "maximum_inclusive": criterion.robust_interval.maximum_inclusive,
                    }
                    if criterion.robust_interval is not None
                    else None
                ),
                "lower_switch": _winner_switch_to_dict(criterion.lower_switch),
                "upper_switch": _winner_switch_to_dict(criterion.upper_switch),
                "explanation": criterion.explanation,
            }
            for criterion in sensitivity.criteria
        ],
        "explanation": sensitivity.explanation,
    }


def multi_criteria_result_to_dict(outcome: MultiCriteriaOutcome) -> dict[str, Any]:
    model = outcome.model
    alternative_results = []
    for result in outcome.alternative_results:
        summary = result.utility_distribution
        alternative_results.append(
            {
                "alternative_id": result.alternative_id,
                "analytical_raw_means": dict(result.analytical_raw_means),
                "analytical_utility": result.analytical_utility,
                "monte_carlo_mean_utility": result.monte_carlo_mean_utility,
                "criterion_mean_utilities": dict(result.criterion_mean_utilities),
                "weighted_criterion_contributions": dict(
                    result.weighted_criterion_contributions
                ),
                "win_probability": result.win_probability,
                "utility_distribution": {
                    "minimum": summary.minimum,
                    "maximum": summary.maximum,
                    "standard_deviation": summary.standard_deviation,
                    "percentile_10": summary.percentile_10,
                    "percentile_50": summary.percentile_50,
                    "percentile_90": summary.percentile_90,
                },
                "clamp_diagnostics": [
                    {
                        "criterion_id": diagnostic.criterion_id,
                        "analytical_mean_clamped": diagnostic.analytical_mean_clamped,
                        "sampled_below_zero_count": diagnostic.sampled_below_zero_count,
                        "sampled_above_one_count": diagnostic.sampled_above_one_count,
                    }
                    for diagnostic in result.clamp_diagnostics
                ],
            }
        )

    excluded_alternatives = [
        {
            "alternative_id": excluded.alternative_id,
            "failed_constraints": [
                {
                    "constraint_id": failure.constraint_id,
                    "criterion_id": failure.criterion_id,
                    "operator": failure.operator,
                    "threshold": failure.threshold,
                    "relevant_estimate_boundary": {
                        "name": failure.boundary_name,
                        "values": list(failure.boundary_values),
                    },
                    "human_explanation": failure.human_explanation,
                }
                for failure in excluded.failed_constraints
            ],
        }
        for excluded in outcome.excluded_alternatives
    ]
    recommendation = outcome.recommendation
    result_document: dict[str, Any] = {
        "result_version": RESULT_VERSION,
        "model_version": model.model_version,
        "model_type": "multi_criteria",
        "decision_id": model.decision_id,
        "engine_version": ENGINE_VERSION,
        "status": "completed",
        "assumptions": list(model.assumptions),
        "warnings": list(outcome.warnings),
        "method": {
            "name": "weighted_utility_with_monte_carlo",
            "recommendation_basis": "monte_carlo_mean_utility",
            "analytical_cross_check": "triangular_raw_mean_weighted_utility",
            "uncertainty_distribution": "triangular",
            "tie_handling": "split_win_credit",
            "numerical_tolerance": NUMERICAL_TOLERANCE,
            "close_call_threshold": CLOSE_CALL_THRESHOLD,
            "utility_clamping": True,
            "percentile_method": PERCENTILE_METHOD,
            "constraint_interpretation": "conservative_all_supported_values",
        },
        "reproducibility": {
            "random_seed": model.analysis_settings.random_seed,
            "monte_carlo_samples": model.analysis_settings.monte_carlo_samples,
            "random_generator": "python_random.Random",
        },
        "alternative_results": alternative_results,
        "excluded_alternatives": excluded_alternatives,
        "sensitivity": _sensitivity_to_dict(outcome.sensitivity),
        "recommendation": {
            "status": recommendation.status,
            "alternative_id": recommendation.alternative_id,
            "tied_alternative_ids": list(recommendation.tied_alternative_ids),
            "leading_monte_carlo_mean_utility": (
                recommendation.leading_monte_carlo_mean_utility
            ),
            "leading_win_probability": recommendation.leading_win_probability,
            "conditional_statement": recommendation.conditional_statement,
        },
    }
    errors = validate_multi_criteria_result(result_document)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Internal result-contract validation failed:\n{joined}")
    return result_document


def sequential_exploration_result_to_dict(
    outcome: SequentialExplorationOutcome,
) -> dict[str, Any]:
    """Serialize one sequential outcome into decision-result-v1."""

    model = outcome.model
    state = model.state
    action_values = outcome.current_action_values
    exploration_available = action_values.explore_value is not None
    if not exploration_available:
        recommendation_status = "exploration_unavailable"
    elif action_values.recommended_action == "indifferent":
        recommendation_status = "indifferent"
    else:
        recommendation_status = f"{action_values.recommended_action}_preferred"

    if exploration_available:
        conditional_statement = (
            f"Under the stated utility scale, triangular estimates, and {state.remaining_opportunities}-opportunity "
            f"horizon, {action_values.recommended_action} is preferable; this is conditional on those inputs "
            "and assumptions, not an objectively correct life choice."
            if action_values.recommended_action != "indifferent"
            else
            f"Under the stated utility scale, triangular estimates, and {state.remaining_opportunities}-opportunity "
            "horizon, explore and exploit are equal within the declared numerical tolerance."
        )
    else:
        conditional_statement = (
            "Exploit is the only available action because no unseen options remain; this conclusion is "
            "conditional on the stated model."
        )

    result_document: dict[str, Any] = {
        "result_version": RESULT_VERSION,
        "model_version": model.model_version,
        "model_type": "sequential_exploration",
        "decision_id": model.decision_id,
        "engine_version": ENGINE_VERSION,
        "status": "completed",
        "decision_metadata": {
            "title": model.title,
            "description": model.description,
            "time_horizon": model.time_horizon,
        },
        "recommended_action": action_values.recommended_action,
        "recommendation_status": recommendation_status,
        "expected_total_utility": outcome.expected_total_utility,
        "exploit_value": action_values.exploit_value,
        "explore_value": action_values.explore_value,
        "action_advantage": action_values.action_advantage,
        "conditional_statement": conditional_statement,
        "current_state": {
            "remaining_opportunities": state.remaining_opportunities,
            "unseen_options_remaining": state.unseen_options_remaining,
            "best_known_value": state.best_known_value,
        },
        "new_option_distribution": {
            "minimum": model.new_option_distribution.minimum,
            "most_likely": model.new_option_distribution.most_likely,
            "maximum": model.new_option_distribution.maximum,
        },
        "utility_scale": {
            "minimum": model.utility_scale.minimum,
            "maximum": model.utility_scale.maximum,
            "unit": model.utility_scale.unit,
            "description": model.utility_scale.description,
        },
        "method": {
            "name": "finite_horizon_dynamic_programming",
            "expectation_method": "midpoint_quantile_quadrature",
            "quadrature_points": model.analysis_settings.quadrature_points,
            "action_comparison_tolerance": ACTION_COMPARISON_TOLERANCE,
            "memoization_decimal_places": MEMOIZATION_DECIMAL_PLACES,
            "uncertainty_distribution": "triangular",
            "discount_factor": 1,
        },
        "assumptions": list(model.assumptions),
        "warnings": list(outcome.warnings),
        "reproducibility": {
            "deterministic": True,
            "random_sampling": False,
            "quadrature_points": model.analysis_settings.quadrature_points,
            "memoization_decimal_places": MEMOIZATION_DECIMAL_PLACES,
            "memoized_state_count": outcome.memoized_state_count,
        },
        "policy_by_remaining_opportunities": [
            {
                "remaining_opportunities": row.remaining_opportunities,
                "exploit_value": row.exploit_value,
                "explore_value": row.explore_value,
                "recommended_action": row.recommended_action,
                "action_advantage": row.action_advantage,
            }
            for row in outcome.policy_by_remaining_opportunities
        ],
        "action_switch_points": [
            {
                "remaining_opportunities": switch.remaining_opportunities,
                "previous_action": switch.previous_action,
                "recommended_action": switch.recommended_action,
            }
            for switch in outcome.action_switch_points
        ],
    }
    errors = validate_sequential_exploration_result(result_document)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Internal result-contract validation failed:\n{joined}")
    return result_document


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _check_exact_keys(
    value: Any,
    expected: set[str],
    path: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return False
    actual = set(value)
    for key in sorted(expected - actual):
        errors.append(f"{path}.{key} is required")
    for key in sorted(actual - expected):
        errors.append(f"{path}.{key} is not allowed")
    return expected.issubset(actual)


def _validate_sensitivity_result(
    sensitivity: Any,
    feasible_ids: set[str],
    errors: list[str],
) -> None:
    path = "$.sensitivity"
    root_keys = {
        "status", "method", "ranking_basis", "random_seed", "simulation_count",
        "fixed_sample_reused", "numerical_tolerance", "verification_epsilon_rule",
        "baseline_winner_id", "baseline_tied_alternative_ids", "criteria",
        "explanation",
    }
    if not _check_exact_keys(sensitivity, root_keys, path, errors):
        return
    statuses = {
        "analyzed",
        "not_applicable_no_feasible_alternatives",
        "not_applicable_only_one_feasible_alternative",
        "not_applicable_baseline_tie",
    }
    if sensitivity["status"] not in statuses:
        errors.append(f"{path}.status is invalid")
    elif not feasible_ids and sensitivity["status"] != "not_applicable_no_feasible_alternatives":
        errors.append(f"{path}.status must record no feasible alternatives")
    elif len(feasible_ids) == 1 and sensitivity["status"] != "not_applicable_only_one_feasible_alternative":
        errors.append(f"{path}.status must record only one feasible alternative")
    elif len(feasible_ids) >= 2 and sensitivity["status"] not in {
        "analyzed", "not_applicable_baseline_tie"
    }:
        errors.append(f"{path}.status is inconsistent with the feasible alternatives")
    constants = {
        "method": "fixed_sample_linear_weight_sensitivity",
        "ranking_basis": "monte_carlo_mean_utility",
        "fixed_sample_reused": True,
        "numerical_tolerance": NUMERICAL_TOLERANCE,
    }
    for field, expected in constants.items():
        if sensitivity[field] != expected:
            errors.append(f"{path}.{field} must equal {expected!r}")
    for field in ("random_seed", "simulation_count"):
        value = sensitivity[field]
        minimum = 1 if field == "simulation_count" else None
        if isinstance(value, bool) or not isinstance(value, int) or (
            minimum is not None and value < minimum
        ):
            errors.append(f"{path}.{field} must be a valid integer")
    for field in ("verification_epsilon_rule", "explanation"):
        if not isinstance(sensitivity[field], str) or not sensitivity[field]:
            errors.append(f"{path}.{field} must be non-empty text")
    baseline_winner = sensitivity["baseline_winner_id"]
    if baseline_winner is not None and (
        not isinstance(baseline_winner, str) or baseline_winner not in feasible_ids
    ):
        errors.append(f"{path}.baseline_winner_id must be null or a feasible ID")
    baseline_ties = sensitivity["baseline_tied_alternative_ids"]
    if not isinstance(baseline_ties, list) or not all(
        isinstance(item, str) and item in feasible_ids for item in baseline_ties
    ) or len(baseline_ties) != len(set(baseline_ties)):
        errors.append(f"{path}.baseline_tied_alternative_ids is invalid")
    if sensitivity["status"] == "analyzed" and (
        baseline_winner is None or baseline_ties != []
    ):
        errors.append(f"{path} analyzed status requires one baseline winner and no baseline tie")
    if sensitivity["status"] == "not_applicable_baseline_tie" and (
        baseline_winner is not None or not isinstance(baseline_ties, list) or len(baseline_ties) < 2
    ):
        errors.append(f"{path} baseline-tie status requires at least two tied IDs and no winner")

    criteria = sensitivity["criteria"]
    if not isinstance(criteria, list) or not criteria:
        errors.append(f"{path}.criteria must be a non-empty array")
        return
    criterion_keys = {
        "criterion_id", "baseline_weight", "status", "robust_interval",
        "lower_switch", "upper_switch", "explanation",
    }
    criterion_ids: list[str] = []
    switch_keys = {
        "direction", "change_type", "threshold_weight", "new_winner_id",
        "new_tied_winner_ids", "tie_alternative_ids",
        "mean_utility_at_threshold", "verified", "verification_epsilon",
        "lower_probe_weight", "lower_probe_leader_ids", "upper_probe_weight",
        "upper_probe_leader_ids", "explanation",
    }
    for index, criterion in enumerate(criteria):
        criterion_path = f"{path}.criteria[{index}]"
        if not _check_exact_keys(criterion, criterion_keys, criterion_path, errors):
            continue
        criterion_id = criterion["criterion_id"]
        if not isinstance(criterion_id, str) or not criterion_id:
            errors.append(f"{criterion_path}.criterion_id must be non-empty text")
        else:
            criterion_ids.append(criterion_id)
        weight = criterion["baseline_weight"]
        if not _is_finite_number(weight) or not 0.0 <= weight <= 1.0:
            errors.append(f"{criterion_path}.baseline_weight must be from 0 to 1")
        if criterion["status"] not in {
            "analyzed", "not_analyzable_baseline_weight_one", "not_applicable"
        }:
            errors.append(f"{criterion_path}.status is invalid")
        if not isinstance(criterion["explanation"], str) or not criterion["explanation"]:
            errors.append(f"{criterion_path}.explanation must be non-empty text")
        interval = criterion["robust_interval"]
        if interval is not None:
            interval_keys = {
                "minimum_weight", "maximum_weight", "minimum_inclusive",
                "maximum_inclusive",
            }
            if _check_exact_keys(
                interval, interval_keys, f"{criterion_path}.robust_interval", errors
            ):
                minimum = interval["minimum_weight"]
                maximum = interval["maximum_weight"]
                if (
                    not _is_finite_number(minimum)
                    or not _is_finite_number(maximum)
                    or not 0.0 <= minimum <= weight <= maximum <= 1.0
                ):
                    errors.append(f"{criterion_path}.robust_interval is invalid")
                for field in ("minimum_inclusive", "maximum_inclusive"):
                    if not isinstance(interval[field], bool):
                        errors.append(f"{criterion_path}.robust_interval.{field} must be boolean")
        elif criterion["status"] == "analyzed":
            errors.append(f"{criterion_path}.robust_interval is required when analyzed")

        for switch_field, expected_direction in (
            ("lower_switch", "lower"), ("upper_switch", "upper")
        ):
            switch = criterion[switch_field]
            if switch is None:
                continue
            switch_path = f"{criterion_path}.{switch_field}"
            if not _check_exact_keys(switch, switch_keys, switch_path, errors):
                continue
            if switch["direction"] != expected_direction:
                errors.append(f"{switch_path}.direction must be {expected_direction!r}")
            if switch["change_type"] not in {"winner_switch", "boundary_tie"}:
                errors.append(f"{switch_path}.change_type is invalid")
            for field in (
                "threshold_weight", "mean_utility_at_threshold", "verification_epsilon",
                "lower_probe_weight", "upper_probe_weight",
            ):
                if not _is_finite_number(switch[field]):
                    errors.append(f"{switch_path}.{field} must be finite")
            if _is_finite_number(switch["threshold_weight"]) and not 0.0 <= switch["threshold_weight"] <= 1.0:
                errors.append(f"{switch_path}.threshold_weight must be from 0 to 1")
            if _is_finite_number(switch["verification_epsilon"]) and switch["verification_epsilon"] <= 0.0:
                errors.append(f"{switch_path}.verification_epsilon must be positive")
            if all(
                _is_finite_number(switch[field])
                for field in ("lower_probe_weight", "threshold_weight", "upper_probe_weight")
            ) and not (
                0.0 <= switch["lower_probe_weight"]
                <= switch["threshold_weight"]
                <= switch["upper_probe_weight"] <= 1.0
            ):
                errors.append(f"{switch_path} probes must bracket the threshold within 0 to 1")
            if _is_finite_number(switch["threshold_weight"]) and _is_finite_number(weight):
                if expected_direction == "lower" and not switch["threshold_weight"] < weight:
                    errors.append(f"{switch_path}.threshold_weight must be below the baseline weight")
                if expected_direction == "upper" and not switch["threshold_weight"] > weight:
                    errors.append(f"{switch_path}.threshold_weight must be above the baseline weight")
                at_boundary = switch["threshold_weight"] in {0.0, 1.0}
                if at_boundary != (switch["change_type"] == "boundary_tie"):
                    errors.append(f"{switch_path}.change_type is inconsistent with the threshold")
            if switch["verified"] is not True:
                errors.append(f"{switch_path}.verified must be true")
            new_winner = switch["new_winner_id"]
            if new_winner is not None and (
                not isinstance(new_winner, str) or new_winner not in feasible_ids
            ):
                errors.append(f"{switch_path}.new_winner_id is invalid")
            for list_field in (
                "new_tied_winner_ids", "tie_alternative_ids",
                "lower_probe_leader_ids", "upper_probe_leader_ids",
            ):
                values = switch[list_field]
                if not isinstance(values, list) or not all(
                    isinstance(item, str) and item in feasible_ids for item in values
                ) or len(values) != len(set(values)):
                    errors.append(f"{switch_path}.{list_field} is invalid")
            if isinstance(switch["tie_alternative_ids"], list) and (
                len(switch["tie_alternative_ids"]) < 2
                or baseline_winner not in switch["tie_alternative_ids"]
            ):
                errors.append(f"{switch_path}.tie_alternative_ids must include the baseline winner and a competitor")
            if not isinstance(switch["explanation"], str) or not switch["explanation"]:
                errors.append(f"{switch_path}.explanation must be non-empty text")
        if isinstance(interval, dict):
            lower_switch = criterion["lower_switch"]
            upper_switch = criterion["upper_switch"]
            expected_minimum = lower_switch["threshold_weight"] if isinstance(lower_switch, dict) else 0.0
            expected_maximum = upper_switch["threshold_weight"] if isinstance(upper_switch, dict) else 1.0
            if interval.get("minimum_weight") != expected_minimum:
                errors.append(f"{criterion_path}.robust_interval.minimum_weight must match the lower switch or 0")
            if interval.get("maximum_weight") != expected_maximum:
                errors.append(f"{criterion_path}.robust_interval.maximum_weight must match the upper switch or 1")
            if interval.get("minimum_inclusive") is not (lower_switch is None):
                errors.append(f"{criterion_path}.robust_interval.minimum_inclusive is inconsistent")
            if interval.get("maximum_inclusive") is not (upper_switch is None):
                errors.append(f"{criterion_path}.robust_interval.maximum_inclusive is inconsistent")
    if len(criterion_ids) != len(set(criterion_ids)):
        errors.append(f"{path}.criteria contains duplicate criterion IDs")


def validate_multi_criteria_result(result: Any) -> list[str]:
    """Check the multi-criteria subset of decision-result-v1 without dependencies."""

    errors: list[str] = []
    root_keys = {
        "result_version",
        "model_version",
        "model_type",
        "decision_id",
        "engine_version",
        "status",
        "assumptions",
        "warnings",
        "method",
        "reproducibility",
        "alternative_results",
        "excluded_alternatives",
        "sensitivity",
        "recommendation",
    }
    if not _check_exact_keys(result, root_keys, "$", errors):
        return errors
    constants = {
        "result_version": RESULT_VERSION,
        "model_version": "1.0",
        "model_type": "multi_criteria",
        "engine_version": ENGINE_VERSION,
        "status": "completed",
    }
    for key, expected in constants.items():
        if result[key] != expected:
            errors.append(f"$.{key} must equal {expected!r}")
    if not isinstance(result["decision_id"], str) or not result["decision_id"]:
        errors.append("$.decision_id must be non-empty text")
    for field in ("assumptions", "warnings"):
        if not isinstance(result[field], list) or not all(
            isinstance(item, str) and item for item in result[field]
        ):
            errors.append(f"$.{field} must be an array of non-empty text")

    expected_method = {
        "name": "weighted_utility_with_monte_carlo",
        "recommendation_basis": "monte_carlo_mean_utility",
        "analytical_cross_check": "triangular_raw_mean_weighted_utility",
        "uncertainty_distribution": "triangular",
        "tie_handling": "split_win_credit",
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "close_call_threshold": CLOSE_CALL_THRESHOLD,
        "utility_clamping": True,
        "percentile_method": PERCENTILE_METHOD,
        "constraint_interpretation": "conservative_all_supported_values",
    }
    if _check_exact_keys(result["method"], set(expected_method), "$.method", errors):
        for key, expected in expected_method.items():
            if result["method"][key] != expected:
                errors.append(f"$.method.{key} must equal {expected!r}")

    reproducibility_keys = {"random_seed", "monte_carlo_samples", "random_generator"}
    if _check_exact_keys(
        result["reproducibility"],
        reproducibility_keys,
        "$.reproducibility",
        errors,
    ):
        reproducibility = result["reproducibility"]
        if isinstance(reproducibility["random_seed"], bool) or not isinstance(
            reproducibility["random_seed"], int
        ):
            errors.append("$.reproducibility.random_seed must be an integer")
        if (
            isinstance(reproducibility["monte_carlo_samples"], bool)
            or not isinstance(reproducibility["monte_carlo_samples"], int)
            or reproducibility["monte_carlo_samples"] < 1
        ):
            errors.append("$.reproducibility.monte_carlo_samples must be at least 1")
        if reproducibility["random_generator"] != "python_random.Random":
            errors.append("$.reproducibility.random_generator is invalid")

    alternatives = result["alternative_results"]
    excluded = result["excluded_alternatives"]
    if not isinstance(alternatives, list):
        errors.append("$.alternative_results must be an array")
        alternatives = []
    if not isinstance(excluded, list):
        errors.append("$.excluded_alternatives must be an array")
        excluded = []
    alternative_keys = {
        "alternative_id",
        "analytical_raw_means",
        "analytical_utility",
        "monte_carlo_mean_utility",
        "criterion_mean_utilities",
        "weighted_criterion_contributions",
        "win_probability",
        "utility_distribution",
        "clamp_diagnostics",
    }
    distribution_keys = {
        "minimum",
        "maximum",
        "standard_deviation",
        "percentile_10",
        "percentile_50",
        "percentile_90",
    }
    clamp_keys = {
        "criterion_id",
        "analytical_mean_clamped",
        "sampled_below_zero_count",
        "sampled_above_one_count",
    }
    feasible_ids: list[str] = []
    for index, alternative in enumerate(alternatives):
        path = f"$.alternative_results[{index}]"
        if not _check_exact_keys(alternative, alternative_keys, path, errors):
            continue
        if not isinstance(alternative["alternative_id"], str):
            errors.append(f"{path}.alternative_id must be text")
        else:
            feasible_ids.append(alternative["alternative_id"])
        raw_means = alternative["analytical_raw_means"]
        if not isinstance(raw_means, dict) or not raw_means or not all(
            isinstance(key, str) and _is_finite_number(value)
            for key, value in raw_means.items()
        ):
            errors.append(f"{path}.analytical_raw_means must map criterion IDs to finite numbers")
        for map_field in (
            "criterion_mean_utilities", "weighted_criterion_contributions"
        ):
            values = alternative[map_field]
            if not isinstance(values, dict) or not values or not all(
                isinstance(key, str)
                and _is_finite_number(value)
                and 0.0 <= value <= 1.0
                for key, value in values.items()
            ):
                errors.append(f"{path}.{map_field} must map criterion IDs to values from 0 to 1")
        for field in ("analytical_utility", "monte_carlo_mean_utility", "win_probability"):
            value = alternative[field]
            if not _is_finite_number(value) or not 0.0 <= value <= 1.0:
                errors.append(f"{path}.{field} must be a finite number from 0 to 1")
        if _check_exact_keys(
            alternative["utility_distribution"],
            distribution_keys,
            f"{path}.utility_distribution",
            errors,
        ):
            for field, value in alternative["utility_distribution"].items():
                if not _is_finite_number(value):
                    errors.append(f"{path}.utility_distribution.{field} must be finite")
            if alternative["utility_distribution"]["standard_deviation"] < 0:
                errors.append(f"{path}.utility_distribution.standard_deviation must be non-negative")
        diagnostics = alternative["clamp_diagnostics"]
        if not isinstance(diagnostics, list):
            errors.append(f"{path}.clamp_diagnostics must be an array")
        else:
            for diagnostic_index, diagnostic in enumerate(diagnostics):
                diagnostic_path = f"{path}.clamp_diagnostics[{diagnostic_index}]"
                if _check_exact_keys(diagnostic, clamp_keys, diagnostic_path, errors):
                    if not isinstance(diagnostic["criterion_id"], str):
                        errors.append(f"{diagnostic_path}.criterion_id must be text")
                    if not isinstance(diagnostic["analytical_mean_clamped"], bool):
                        errors.append(f"{diagnostic_path}.analytical_mean_clamped must be boolean")
                    for count_field in ("sampled_below_zero_count", "sampled_above_one_count"):
                        count = diagnostic[count_field]
                        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                            errors.append(f"{diagnostic_path}.{count_field} must be non-negative integer")

    excluded_keys = {"alternative_id", "failed_constraints"}
    failure_keys = {
        "constraint_id",
        "criterion_id",
        "operator",
        "threshold",
        "relevant_estimate_boundary",
        "human_explanation",
    }
    boundary_keys = {"name", "values"}
    excluded_ids: list[str] = []
    for index, item in enumerate(excluded):
        path = f"$.excluded_alternatives[{index}]"
        if not _check_exact_keys(item, excluded_keys, path, errors):
            continue
        if isinstance(item["alternative_id"], str):
            excluded_ids.append(item["alternative_id"])
        else:
            errors.append(f"{path}.alternative_id must be text")
        failures = item["failed_constraints"]
        if not isinstance(failures, list) or not failures:
            errors.append(f"{path}.failed_constraints must be a non-empty array")
            continue
        for failure_index, failure in enumerate(failures):
            failure_path = f"{path}.failed_constraints[{failure_index}]"
            if not _check_exact_keys(failure, failure_keys, failure_path, errors):
                continue
            for field in ("constraint_id", "criterion_id", "operator", "human_explanation"):
                if not isinstance(failure[field], str) or not failure[field]:
                    errors.append(f"{failure_path}.{field} must be non-empty text")
            if not _is_finite_number(failure["threshold"]):
                errors.append(f"{failure_path}.threshold must be finite")
            boundary = failure["relevant_estimate_boundary"]
            if _check_exact_keys(boundary, boundary_keys, f"{failure_path}.relevant_estimate_boundary", errors):
                if boundary["name"] not in {"minimum", "maximum", "all_values"}:
                    errors.append(f"{failure_path}.relevant_estimate_boundary.name is invalid")
                if not isinstance(boundary["values"], list) or not 1 <= len(boundary["values"]) <= 3 or not all(
                    _is_finite_number(value) for value in boundary["values"]
                ):
                    errors.append(f"{failure_path}.relevant_estimate_boundary.values is invalid")

    if set(feasible_ids) & set(excluded_ids):
        errors.append("An alternative cannot be both feasible and excluded")
    if not 2 <= len(feasible_ids) + len(excluded_ids) <= 4:
        errors.append("The result must account for 2-4 alternatives")
    if feasible_ids:
        probability_sum = math.fsum(item["win_probability"] for item in alternatives)
        if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
            errors.append(f"Win probabilities must sum to 1; received {probability_sum:.12g}")

    _validate_sensitivity_result(result["sensitivity"], set(feasible_ids), errors)
    sensitivity = result["sensitivity"]
    if isinstance(sensitivity, dict):
        if isinstance(result["reproducibility"], dict):
            if sensitivity.get("random_seed") != result["reproducibility"].get("random_seed"):
                errors.append("$.sensitivity.random_seed must match reproducibility")
            if sensitivity.get("simulation_count") != result["reproducibility"].get("monte_carlo_samples"):
                errors.append("$.sensitivity.simulation_count must match reproducibility")
        sensitivity_criteria = sensitivity.get("criteria")
        if isinstance(sensitivity_criteria, list) and all(
            isinstance(item, dict)
            and isinstance(item.get("criterion_id"), str)
            and _is_finite_number(item.get("baseline_weight"))
            for item in sensitivity_criteria
        ):
            baseline_weights = {
                item["criterion_id"]: item["baseline_weight"]
                for item in sensitivity_criteria
            }
            for index, alternative in enumerate(alternatives):
                if not isinstance(alternative, dict):
                    continue
                means = alternative.get("criterion_mean_utilities")
                contributions = alternative.get("weighted_criterion_contributions")
                if not isinstance(means, dict) or not isinstance(contributions, dict):
                    continue
                path = f"$.alternative_results[{index}]"
                if set(means) != set(baseline_weights) or set(contributions) != set(baseline_weights):
                    errors.append(f"{path} criterion utility maps must contain every sensitivity criterion")
                    continue
                for criterion_id, weight in baseline_weights.items():
                    if (
                        _is_finite_number(means[criterion_id])
                        and _is_finite_number(contributions[criterion_id])
                        and not math.isclose(
                            contributions[criterion_id],
                            weight * means[criterion_id],
                            rel_tol=0.0,
                            abs_tol=1e-12,
                        )
                    ):
                        errors.append(
                            f"{path}.weighted_criterion_contributions.{criterion_id} is inconsistent"
                        )
                if all(_is_finite_number(value) for value in contributions.values()) and _is_finite_number(
                    alternative.get("monte_carlo_mean_utility")
                ) and not math.isclose(
                    math.fsum(contributions.values()),
                    alternative["monte_carlo_mean_utility"],
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    errors.append(f"{path} weighted contributions must sum to Monte Carlo mean utility")

            means_by_alternative = {
                alternative["alternative_id"]: alternative["criterion_mean_utilities"]
                for alternative in alternatives
                if isinstance(alternative, dict)
                and isinstance(alternative.get("alternative_id"), str)
                and isinstance(alternative.get("criterion_mean_utilities"), dict)
                and set(alternative["criterion_mean_utilities"]) == set(baseline_weights)
                and all(
                    _is_finite_number(value)
                    for value in alternative["criterion_mean_utilities"].values()
                )
            }

            def leaders_for(values: dict[str, float]) -> list[str]:
                if not values:
                    return []
                highest = max(values.values())
                return sorted(
                    alternative_id
                    for alternative_id, value in values.items()
                    if math.isclose(
                        value,
                        highest,
                        rel_tol=0.0,
                        abs_tol=NUMERICAL_TOLERANCE,
                    )
                )

            if set(means_by_alternative) == set(feasible_ids):
                baseline_values = {
                    alternative_id: math.fsum(
                        baseline_weights[criterion_id] * means[criterion_id]
                        for criterion_id in baseline_weights
                    )
                    for alternative_id, means in means_by_alternative.items()
                }
                computed_baseline_leaders = leaders_for(baseline_values)
                if len(computed_baseline_leaders) == 1:
                    if sensitivity.get("baseline_winner_id") != computed_baseline_leaders[0]:
                        errors.append("$.sensitivity.baseline_winner_id is inconsistent with criterion means")
                elif sensitivity.get("baseline_tied_alternative_ids") != computed_baseline_leaders:
                    errors.append("$.sensitivity.baseline_tied_alternative_ids is inconsistent with criterion means")

                for criterion_index, criterion in enumerate(sensitivity_criteria):
                    criterion_id = criterion["criterion_id"]
                    baseline_weight = criterion["baseline_weight"]
                    if baseline_weight == 1.0:
                        continue
                    denominator = 1.0 - baseline_weight
                    lines = {}
                    for alternative_id, means in means_by_alternative.items():
                        other_mean = math.fsum(
                            baseline_weights[other_id] * means[other_id]
                            for other_id in baseline_weights
                            if other_id != criterion_id
                        ) / denominator
                        lines[alternative_id] = (
                            other_mean,
                            means[criterion_id] - other_mean,
                        )

                    def line_values(weight: float) -> dict[str, float]:
                        return {
                            alternative_id: intercept + slope * weight
                            for alternative_id, (intercept, slope) in lines.items()
                        }

                    for switch_field in ("lower_switch", "upper_switch"):
                        switch = criterion.get(switch_field)
                        if not isinstance(switch, dict) or not all(
                            _is_finite_number(switch.get(field))
                            for field in (
                                "threshold_weight", "lower_probe_weight",
                                "upper_probe_weight", "mean_utility_at_threshold",
                            )
                        ):
                            continue
                        switch_path = (
                            f"$.sensitivity.criteria[{criterion_index}].{switch_field}"
                        )
                        threshold_values = line_values(switch["threshold_weight"])
                        expected_ties = leaders_for(threshold_values)
                        expected_lower = leaders_for(line_values(switch["lower_probe_weight"]))
                        expected_upper = leaders_for(line_values(switch["upper_probe_weight"]))
                        if switch.get("tie_alternative_ids") != expected_ties:
                            errors.append(f"{switch_path}.tie_alternative_ids is inconsistent with criterion means")
                        if switch.get("lower_probe_leader_ids") != expected_lower:
                            errors.append(f"{switch_path}.lower_probe_leader_ids is inconsistent with criterion means")
                        if switch.get("upper_probe_leader_ids") != expected_upper:
                            errors.append(f"{switch_path}.upper_probe_leader_ids is inconsistent with criterion means")
                        if not math.isclose(
                            switch["mean_utility_at_threshold"],
                            max(threshold_values.values()),
                            rel_tol=0.0,
                            abs_tol=NUMERICAL_TOLERANCE,
                        ):
                            errors.append(f"{switch_path}.mean_utility_at_threshold is inconsistent")
                        outer_leaders = expected_lower if switch_field == "lower_switch" else expected_upper
                        inner_leaders = expected_upper if switch_field == "lower_switch" else expected_lower
                        if sensitivity.get("baseline_winner_id") is not None and inner_leaders != [
                            sensitivity["baseline_winner_id"]
                        ]:
                            errors.append(f"{switch_path} baseline-side probe must retain the baseline winner")
                        if switch.get("change_type") == "winner_switch":
                            expected_new_winner = outer_leaders[0] if len(outer_leaders) == 1 else None
                            expected_new_ties = outer_leaders if len(outer_leaders) > 1 else []
                            if switch.get("new_winner_id") != expected_new_winner:
                                errors.append(f"{switch_path}.new_winner_id is inconsistent")
                            if switch.get("new_tied_winner_ids") != expected_new_ties:
                                errors.append(f"{switch_path}.new_tied_winner_ids is inconsistent")
                        elif switch.get("change_type") == "boundary_tie":
                            if switch.get("new_winner_id") is not None:
                                errors.append(f"{switch_path}.new_winner_id must be null at a boundary tie")
                            if switch.get("new_tied_winner_ids") != expected_ties:
                                errors.append(f"{switch_path}.new_tied_winner_ids must match the boundary tie")

    recommendation_keys = {
        "status",
        "alternative_id",
        "tied_alternative_ids",
        "leading_monte_carlo_mean_utility",
        "leading_win_probability",
        "conditional_statement",
    }
    recommendation = result["recommendation"]
    if _check_exact_keys(recommendation, recommendation_keys, "$.recommendation", errors):
        statuses = {
            "recommended",
            "close_call",
            "mean_utility_tie",
            "only_feasible_alternative",
            "no_feasible_alternative",
        }
        if recommendation["status"] not in statuses:
            errors.append("$.recommendation.status is invalid")
        if recommendation["alternative_id"] is not None and not isinstance(
            recommendation["alternative_id"], str
        ):
            errors.append("$.recommendation.alternative_id must be text or null")
        if not isinstance(recommendation["tied_alternative_ids"], list) or not all(
            isinstance(value, str) for value in recommendation["tied_alternative_ids"]
        ):
            errors.append("$.recommendation.tied_alternative_ids must be an array of IDs")
        for field in ("leading_monte_carlo_mean_utility", "leading_win_probability"):
            value = recommendation[field]
            if value is not None and (
                not _is_finite_number(value) or not 0.0 <= value <= 1.0
            ):
                errors.append(f"$.recommendation.{field} must be null or a number from 0 to 1")
        if not isinstance(recommendation["conditional_statement"], str) or not recommendation[
            "conditional_statement"
        ]:
            errors.append("$.recommendation.conditional_statement must be non-empty text")

    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError) as error:
        errors.append(f"Result is not strict JSON: {error}")
    return errors


def validate_sequential_exploration_result(result: Any) -> list[str]:
    """Check the sequential-exploration subset of decision-result-v1."""

    errors: list[str] = []
    root_keys = {
        "result_version", "model_version", "model_type", "decision_id",
        "engine_version", "status", "decision_metadata", "recommended_action",
        "recommendation_status", "expected_total_utility", "exploit_value",
        "explore_value", "action_advantage", "conditional_statement",
        "current_state", "new_option_distribution", "utility_scale", "method",
        "assumptions", "warnings", "reproducibility",
        "policy_by_remaining_opportunities", "action_switch_points",
    }
    if not _check_exact_keys(result, root_keys, "$", errors):
        return errors
    constants = {
        "result_version": RESULT_VERSION,
        "model_version": "1.0",
        "model_type": "sequential_exploration",
        "engine_version": ENGINE_VERSION,
        "status": "completed",
    }
    for key, expected in constants.items():
        if result[key] != expected:
            errors.append(f"$.{key} must equal {expected!r}")
    if not isinstance(result["decision_id"], str) or not result["decision_id"]:
        errors.append("$.decision_id must be non-empty text")
    actions = {"explore", "exploit", "indifferent"}
    if result["recommended_action"] not in actions:
        errors.append("$.recommended_action is invalid")
    statuses = {
        "explore_preferred", "exploit_preferred", "indifferent",
        "exploration_unavailable",
    }
    if result["recommendation_status"] not in statuses:
        errors.append("$.recommendation_status is invalid")
    for field in ("expected_total_utility", "exploit_value"):
        if not _is_finite_number(result[field]):
            errors.append(f"$.{field} must be finite")
    for field in ("explore_value", "action_advantage"):
        value = result[field]
        if value is not None and not _is_finite_number(value):
            errors.append(f"$.{field} must be null or finite")
    if not isinstance(result["conditional_statement"], str) or not result["conditional_statement"]:
        errors.append("$.conditional_statement must be non-empty text")

    metadata_keys = {"title", "description", "time_horizon"}
    if _check_exact_keys(result["decision_metadata"], metadata_keys, "$.decision_metadata", errors):
        for field in metadata_keys:
            if not isinstance(result["decision_metadata"][field], str) or not result["decision_metadata"][field]:
                errors.append(f"$.decision_metadata.{field} must be non-empty text")

    state_keys = {"remaining_opportunities", "unseen_options_remaining", "best_known_value"}
    if _check_exact_keys(result["current_state"], state_keys, "$.current_state", errors):
        state = result["current_state"]
        for field, minimum in (("remaining_opportunities", 1), ("unseen_options_remaining", 0)):
            value = state[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                errors.append(f"$.current_state.{field} must be an integer of at least {minimum}")
        if not _is_finite_number(state["best_known_value"]):
            errors.append("$.current_state.best_known_value must be finite")

    triangle_keys = {"minimum", "most_likely", "maximum"}
    if _check_exact_keys(
        result["new_option_distribution"], triangle_keys,
        "$.new_option_distribution", errors,
    ):
        triangle = result["new_option_distribution"]
        if not all(_is_finite_number(triangle[field]) for field in triangle_keys):
            errors.append("$.new_option_distribution values must be finite")
        elif not triangle["minimum"] <= triangle["most_likely"] <= triangle["maximum"]:
            errors.append("$.new_option_distribution must be ordered")

    scale_keys = {"minimum", "maximum", "unit", "description"}
    if _check_exact_keys(result["utility_scale"], scale_keys, "$.utility_scale", errors):
        scale = result["utility_scale"]
        if not _is_finite_number(scale["minimum"]) or not _is_finite_number(scale["maximum"]):
            errors.append("$.utility_scale bounds must be finite")
        elif scale["minimum"] >= scale["maximum"]:
            errors.append("$.utility_scale minimum must be below maximum")
        for field in ("unit", "description"):
            if not isinstance(scale[field], str) or not scale[field]:
                errors.append(f"$.utility_scale.{field} must be non-empty text")

    method_expected = {
        "name": "finite_horizon_dynamic_programming",
        "expectation_method": "midpoint_quantile_quadrature",
        "action_comparison_tolerance": ACTION_COMPARISON_TOLERANCE,
        "memoization_decimal_places": MEMOIZATION_DECIMAL_PLACES,
        "uncertainty_distribution": "triangular",
        "discount_factor": 1,
    }
    method_keys = set(method_expected) | {"quadrature_points"}
    if _check_exact_keys(result["method"], method_keys, "$.method", errors):
        method = result["method"]
        for key, expected in method_expected.items():
            if method[key] != expected:
                errors.append(f"$.method.{key} must equal {expected!r}")
        points = method["quadrature_points"]
        if isinstance(points, bool) or not isinstance(points, int) or points < 1 or points % 2 == 0:
            errors.append("$.method.quadrature_points must be a positive odd integer")

    for field in ("assumptions", "warnings"):
        if not isinstance(result[field], list) or not all(
            isinstance(item, str) and item for item in result[field]
        ):
            errors.append(f"$.{field} must be an array of non-empty text")

    reproducibility_keys = {
        "deterministic", "random_sampling", "quadrature_points",
        "memoization_decimal_places", "memoized_state_count",
    }
    if _check_exact_keys(
        result["reproducibility"], reproducibility_keys,
        "$.reproducibility", errors,
    ):
        reproducibility = result["reproducibility"]
        if reproducibility["deterministic"] is not True:
            errors.append("$.reproducibility.deterministic must be true")
        if reproducibility["random_sampling"] is not False:
            errors.append("$.reproducibility.random_sampling must be false")
        method_points = (
            result["method"].get("quadrature_points")
            if isinstance(result["method"], dict)
            else None
        )
        if reproducibility["quadrature_points"] != method_points:
            errors.append("$.reproducibility.quadrature_points must match method")
        if reproducibility["memoization_decimal_places"] != MEMOIZATION_DECIMAL_PLACES:
            errors.append("$.reproducibility.memoization_decimal_places is invalid")
        count = reproducibility["memoized_state_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            errors.append("$.reproducibility.memoized_state_count must be a positive integer")

    row_keys = {
        "remaining_opportunities", "exploit_value", "explore_value",
        "recommended_action", "action_advantage",
    }
    policy = result["policy_by_remaining_opportunities"]
    if not isinstance(policy, list) or not policy:
        errors.append("$.policy_by_remaining_opportunities must be a non-empty array")
        policy = []
    horizons: list[int] = []
    for index, row in enumerate(policy):
        path = f"$.policy_by_remaining_opportunities[{index}]"
        if not _check_exact_keys(row, row_keys, path, errors):
            continue
        horizon = row["remaining_opportunities"]
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            errors.append(f"{path}.remaining_opportunities must be a positive integer")
        else:
            horizons.append(horizon)
        if row["recommended_action"] not in actions:
            errors.append(f"{path}.recommended_action is invalid")
        if not _is_finite_number(row["exploit_value"]):
            errors.append(f"{path}.exploit_value must be finite")
        for field in ("explore_value", "action_advantage"):
            if row[field] is not None and not _is_finite_number(row[field]):
                errors.append(f"{path}.{field} must be null or finite")
        if _is_finite_number(row["exploit_value"]) and (
            row["explore_value"] is None or _is_finite_number(row["explore_value"])
        ):
            expected_action = compare_actions(row["exploit_value"], row["explore_value"])
            if row["recommended_action"] != expected_action:
                errors.append(f"{path}.recommended_action does not match the action values")
            expected_advantage = (
                None if row["explore_value"] is None
                else row["explore_value"] - row["exploit_value"]
            )
            if expected_advantage is None:
                if row["action_advantage"] is not None:
                    errors.append(f"{path}.action_advantage must be null")
            elif _is_finite_number(row["action_advantage"]) and not math.isclose(
                row["action_advantage"], expected_advantage, rel_tol=0.0, abs_tol=1e-9
            ):
                errors.append(f"{path}.action_advantage is inconsistent")
    requested_horizon = (
        result["current_state"].get("remaining_opportunities", 0)
        if isinstance(result["current_state"], dict)
        else 0
    )
    if policy and horizons != list(range(1, requested_horizon + 1)):
        errors.append("$.policy_by_remaining_opportunities must contain every horizon in ascending order")

    switch_keys = {"remaining_opportunities", "previous_action", "recommended_action"}
    switches = result["action_switch_points"]
    if not isinstance(switches, list):
        errors.append("$.action_switch_points must be an array")
    else:
        for index, switch in enumerate(switches):
            path = f"$.action_switch_points[{index}]"
            if _check_exact_keys(switch, switch_keys, path, errors):
                if switch["previous_action"] not in actions or switch["recommended_action"] not in actions:
                    errors.append(f"{path} contains an invalid action")
                horizon = switch["remaining_opportunities"]
                if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 2:
                    errors.append(f"{path}.remaining_opportunities must be an integer of at least 2")
        valid_policy_actions = all(
            isinstance(row, dict)
            and row.get("recommended_action") in actions
            and isinstance(row.get("remaining_opportunities"), int)
            and not isinstance(row.get("remaining_opportunities"), bool)
            for row in policy
        )
        if valid_policy_actions:
            expected_switches = [
                {
                    "remaining_opportunities": current["remaining_opportunities"],
                    "previous_action": previous["recommended_action"],
                    "recommended_action": current["recommended_action"],
                }
                for previous, current in zip(policy, policy[1:])
                if previous["recommended_action"] != current["recommended_action"]
            ]
            if switches != expected_switches:
                errors.append("$.action_switch_points must contain every policy action change")

    unavailable = result["explore_value"] is None
    if unavailable:
        if result["action_advantage"] is not None:
            errors.append("$.action_advantage must be null when exploration is unavailable")
        if result["recommended_action"] != "exploit":
            errors.append("$.recommended_action must be exploit when exploration is unavailable")
        if result["recommendation_status"] != "exploration_unavailable":
            errors.append("$.recommendation_status must record exploration_unavailable")
    elif not _is_finite_number(result["action_advantage"]):
        errors.append("$.action_advantage must be finite when exploration is available")
    elif (
        _is_finite_number(result["action_advantage"])
        and _is_finite_number(result["explore_value"])
        and _is_finite_number(result["exploit_value"])
        and not math.isclose(
            result["action_advantage"],
            result["explore_value"] - result["exploit_value"],
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    ):
        errors.append("$.action_advantage must equal explore_value minus exploit_value")

    if not unavailable and _is_finite_number(result["exploit_value"]) and _is_finite_number(result["explore_value"]):
        expected_action = compare_actions(result["exploit_value"], result["explore_value"])
        if result["recommended_action"] != expected_action:
            errors.append("$.recommended_action does not match the action values")
        expected_status = (
            "indifferent" if expected_action == "indifferent"
            else f"{expected_action}_preferred"
        )
        if result["recommendation_status"] != expected_status:
            errors.append("$.recommendation_status does not match the action values")

    if (
        _is_finite_number(result["expected_total_utility"])
        and _is_finite_number(result["exploit_value"])
        and (unavailable or _is_finite_number(result["explore_value"]))
    ):
        expected = (
            result["exploit_value"] if unavailable
            else max(result["exploit_value"], result["explore_value"])
        )
        if not math.isclose(result["expected_total_utility"], expected, rel_tol=0.0, abs_tol=1e-9):
            errors.append("$.expected_total_utility must equal the best available action value")
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError) as error:
        errors.append(f"Result is not strict JSON: {error}")
    return errors


def validate_result(result: Any) -> list[str]:
    if not isinstance(result, dict):
        return ["$ must be an object"]
    if result.get("model_type") == "multi_criteria":
        return validate_multi_criteria_result(result)
    if result.get("model_type") == "sequential_exploration":
        return validate_sequential_exploration_result(result)
    return ["$.model_type is not supported by decision-result-v1"]


def result_to_json_text(result: dict[str, Any]) -> str:
    errors = validate_result(result)
    if errors:
        raise ValueError("Result does not match decision-result-v1: " + "; ".join(errors))
    return json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def write_result_json(result: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    return atomic_write_utf8_lf(target, result_to_json_text(result))
