"""Deterministic core calculations for the multi-criteria model."""

from __future__ import annotations

import math
import random
import statistics as stdlib_statistics
from dataclasses import dataclass

from .models import (
    Alternative,
    Criterion,
    HardConstraint,
    MultiCriteriaModel,
    TriangularDistribution,
)
from .statistics import DistributionSummary, summarize_distribution
from .sensitivity import WeightSensitivityOutcome, analyze_weight_sensitivity


NUMERICAL_TOLERANCE = 1e-12
CLOSE_CALL_THRESHOLD = 0.60


class CalculationError(ValueError):
    """Raised when a validated model still cannot be calculated consistently."""


class ConstraintDeclarationMismatchError(CalculationError):
    """Raised when a stored constraint result contradicts its executable rule."""


@dataclass(frozen=True)
class ConstraintEvaluation:
    passed: bool
    boundary_name: str
    boundary_values: tuple[float, ...]
    explanation: str


@dataclass(frozen=True)
class ConstraintFailure:
    constraint_id: str
    criterion_id: str
    operator: str
    threshold: float
    boundary_name: str
    boundary_values: tuple[float, ...]
    human_explanation: str


@dataclass(frozen=True)
class ExcludedAlternative:
    alternative_id: str
    failed_constraints: tuple[ConstraintFailure, ...]


@dataclass(frozen=True)
class ClampDiagnostic:
    criterion_id: str
    analytical_mean_clamped: bool
    sampled_below_zero_count: int
    sampled_above_one_count: int


@dataclass(frozen=True)
class AlternativeCalculation:
    alternative_id: str
    analytical_raw_means: dict[str, float]
    analytical_utility: float
    monte_carlo_mean_utility: float
    criterion_mean_utilities: dict[str, float]
    weighted_criterion_contributions: dict[str, float]
    win_probability: float
    utility_distribution: DistributionSummary
    clamp_diagnostics: tuple[ClampDiagnostic, ...]


@dataclass(frozen=True)
class Recommendation:
    status: str
    alternative_id: str | None
    tied_alternative_ids: tuple[str, ...]
    leading_monte_carlo_mean_utility: float | None
    leading_win_probability: float | None
    conditional_statement: str


@dataclass(frozen=True)
class MultiCriteriaOutcome:
    model: MultiCriteriaModel
    alternative_results: tuple[AlternativeCalculation, ...]
    excluded_alternatives: tuple[ExcludedAlternative, ...]
    recommendation: Recommendation
    sensitivity: WeightSensitivityOutcome
    warnings: tuple[str, ...]


def triangular_raw_mean(distribution: TriangularDistribution) -> float:
    return (
        distribution.minimum
        + distribution.most_likely
        + distribution.maximum
    ) / 3.0


def normalize_utility(value: float, criterion: Criterion) -> tuple[float, int]:
    """Normalize and clamp a raw value.

    The second return value is -1 for a below-zero clamp, 1 for an above-one
    clamp, and 0 when no clamp was needed.
    """

    utility = (value - criterion.worst_anchor) / (
        criterion.best_anchor - criterion.worst_anchor
    )
    if utility < 0.0:
        return 0.0, -1
    if utility > 1.0:
        return 1.0, 1
    return utility, 0


def evaluate_constraint(
    constraint: HardConstraint,
    estimate: TriangularDistribution,
    *,
    tolerance: float = NUMERICAL_TOLERANCE,
) -> ConstraintEvaluation:
    """Evaluate a constraint against every value supported by a triangle."""

    operator = constraint.operator
    threshold = constraint.threshold
    if operator in {"<=", "<"}:
        boundary_name = "maximum"
        boundary_values = (estimate.maximum,)
        passed = estimate.maximum <= threshold if operator == "<=" else estimate.maximum < threshold
        relation = "at most" if operator == "<=" else "strictly below"
        explanation = (
            f"maximum {estimate.maximum:g} must be {relation} {threshold:g}"
        )
    elif operator in {">=", ">"}:
        boundary_name = "minimum"
        boundary_values = (estimate.minimum,)
        passed = estimate.minimum >= threshold if operator == ">=" else estimate.minimum > threshold
        relation = "at least" if operator == ">=" else "strictly above"
        explanation = (
            f"minimum {estimate.minimum:g} must be {relation} {threshold:g}"
        )
    elif operator == "==":
        boundary_name = "all_values"
        boundary_values = (
            estimate.minimum,
            estimate.most_likely,
            estimate.maximum,
        )
        passed = all(
            math.isclose(value, threshold, rel_tol=0.0, abs_tol=tolerance)
            for value in boundary_values
        )
        explanation = (
            f"minimum, most likely, and maximum must all equal {threshold:g} "
            f"within tolerance {tolerance:g}"
        )
    elif operator == "!=":
        boundary_name = "all_values"
        boundary_values = (
            estimate.minimum,
            estimate.most_likely,
            estimate.maximum,
        )
        all_forbidden = all(
            math.isclose(value, threshold, rel_tol=0.0, abs_tol=tolerance)
            for value in boundary_values
        )
        passed = not all_forbidden
        explanation = (
            f"the estimate is rejected only when minimum, most likely, and maximum "
            f"all equal forbidden value {threshold:g} within tolerance {tolerance:g}"
        )
    else:  # Defensive guard for direct typed-model construction.
        raise CalculationError(f"Unsupported constraint operator: {operator!r}.")
    return ConstraintEvaluation(
        passed=passed,
        boundary_name=boundary_name,
        boundary_values=boundary_values,
        explanation=explanation,
    )


def _filter_alternatives(
    model: MultiCriteriaModel,
) -> tuple[list[Alternative], list[ExcludedAlternative]]:
    feasible: list[Alternative] = []
    excluded: list[ExcludedAlternative] = []
    for alternative in model.alternatives:
        failures: list[ConstraintFailure] = []
        for constraint in model.hard_constraints:
            estimate = alternative.criterion_estimates[constraint.criterion_id]
            evaluation = evaluate_constraint(constraint, estimate)
            declared = alternative.constraint_results[constraint.id]
            if declared is not evaluation.passed:
                raise ConstraintDeclarationMismatchError(
                    f"Alternative {alternative.id!r} declares constraint {constraint.id!r} "
                    f"as {declared}, but {constraint.criterion_id} {constraint.operator} "
                    f"{constraint.threshold:g} evaluates to {evaluation.passed} under the "
                    "conservative all-supported-values rule. Correct and reconfirm the input model."
                )
            if not evaluation.passed:
                failures.append(
                    ConstraintFailure(
                        constraint_id=constraint.id,
                        criterion_id=constraint.criterion_id,
                        operator=constraint.operator,
                        threshold=constraint.threshold,
                        boundary_name=evaluation.boundary_name,
                        boundary_values=evaluation.boundary_values,
                        human_explanation=(
                            f"Alternative {alternative.id!r} fails constraint "
                            f"{constraint.id!r}: {evaluation.explanation}."
                        ),
                    )
                )
        if failures:
            excluded.append(
                ExcludedAlternative(
                    alternative_id=alternative.id,
                    failed_constraints=tuple(failures),
                )
            )
        else:
            feasible.append(alternative)
    return feasible, excluded


def _analytical_values(
    alternative: Alternative,
    criteria: tuple[Criterion, ...],
) -> tuple[dict[str, float], float, dict[str, bool]]:
    raw_means: dict[str, float] = {}
    weighted_utilities: list[float] = []
    clamped: dict[str, bool] = {}
    for criterion in criteria:
        raw_mean = triangular_raw_mean(alternative.criterion_estimates[criterion.id])
        raw_means[criterion.id] = raw_mean
        utility, clamp_direction = normalize_utility(raw_mean, criterion)
        weighted_utilities.append(criterion.weight * utility)
        clamped[criterion.id] = clamp_direction != 0
    return raw_means, math.fsum(weighted_utilities), clamped


def _recommend(
    model: MultiCriteriaModel,
    results: tuple[AlternativeCalculation, ...],
) -> Recommendation:
    if not results:
        return Recommendation(
            status="no_feasible_alternative",
            alternative_id=None,
            tied_alternative_ids=(),
            leading_monte_carlo_mean_utility=None,
            leading_win_probability=None,
            conditional_statement=(
                "Under the confirmed hard constraints, no alternative is feasible; "
                "the model therefore makes no recommendation."
            ),
        )

    names = {alternative.id: alternative.name for alternative in model.alternatives}
    leader = results[0]
    if len(results) == 1:
        return Recommendation(
            status="only_feasible_alternative",
            alternative_id=leader.alternative_id,
            tied_alternative_ids=(),
            leading_monte_carlo_mean_utility=leader.monte_carlo_mean_utility,
            leading_win_probability=leader.win_probability,
            conditional_statement=(
                f"Under the confirmed preferences, estimates, constraints, time horizon, "
                f"and assumptions, {names[leader.alternative_id]} is the only feasible alternative."
            ),
        )

    tied = tuple(
        sorted(
            result.alternative_id
            for result in results
            if math.isclose(
                result.monte_carlo_mean_utility,
                leader.monte_carlo_mean_utility,
                rel_tol=0.0,
                abs_tol=NUMERICAL_TOLERANCE,
            )
        )
    )
    if len(tied) > 1:
        tied_names = ", ".join(names[alternative_id] for alternative_id in tied)
        return Recommendation(
            status="mean_utility_tie",
            alternative_id=None,
            tied_alternative_ids=tied,
            leading_monte_carlo_mean_utility=leader.monte_carlo_mean_utility,
            leading_win_probability=max(
                result.win_probability
                for result in results
                if result.alternative_id in tied
            ),
            conditional_statement=(
                f"Under the confirmed preferences, estimates, constraints, time horizon, "
                f"and assumptions, {tied_names} have equal leading Monte Carlo mean utility "
                f"within tolerance {NUMERICAL_TOLERANCE:g}; no arbitrary winner was selected."
            ),
        )

    if leader.win_probability >= CLOSE_CALL_THRESHOLD:
        status = "recommended"
        explanation = (
            f"{names[leader.alternative_id]} has the unique highest Monte Carlo mean utility "
            f"and wins {leader.win_probability:.1%} of simulated scenarios."
        )
    else:
        status = "close_call"
        explanation = (
            f"{names[leader.alternative_id]} has the unique highest Monte Carlo mean utility, "
            f"but wins only {leader.win_probability:.1%} of simulated scenarios, below the "
            f"{CLOSE_CALL_THRESHOLD:.0%} strong-recommendation threshold."
        )
    return Recommendation(
        status=status,
        alternative_id=leader.alternative_id,
        tied_alternative_ids=(),
        leading_monte_carlo_mean_utility=leader.monte_carlo_mean_utility,
        leading_win_probability=leader.win_probability,
        conditional_statement=(
            "Under the confirmed preferences, estimates, constraints, time horizon, and "
            f"assumptions, {explanation}"
        ),
    )


def analyze_multi_criteria(model: MultiCriteriaModel) -> MultiCriteriaOutcome:
    """Calculate a reproducible multi-criteria result without mutating the model."""

    if model.analysis_settings.clamp_utility is not True:
        raise CalculationError("Model version 1.0 requires utility clamping to be enabled.")

    feasible, excluded = _filter_alternatives(model)
    if not feasible:
        results: tuple[AlternativeCalculation, ...] = ()
        return MultiCriteriaOutcome(
            model=model,
            alternative_results=results,
            excluded_alternatives=tuple(sorted(excluded, key=lambda item: item.alternative_id)),
            recommendation=_recommend(model, results),
            sensitivity=analyze_weight_sensitivity(model, {}),
            warnings=(),
        )

    rng = random.Random(model.analysis_settings.random_seed)
    sample_totals: dict[str, list[float]] = {
        alternative.id: [] for alternative in feasible
    }
    win_credits: dict[str, float] = {
        alternative.id: 0.0 for alternative in feasible
    }
    analytical_data: dict[str, tuple[dict[str, float], float, dict[str, bool]]] = {
        alternative.id: _analytical_values(alternative, model.criteria)
        for alternative in feasible
    }
    clamp_counts: dict[str, dict[str, list[int]]] = {
        alternative.id: {
            criterion.id: [0, 0] for criterion in model.criteria
        }
        for alternative in feasible
    }
    criterion_utility_samples: dict[str, dict[str, list[float]]] = {
        alternative.id: {
            criterion.id: [] for criterion in model.criteria
        }
        for alternative in feasible
    }

    for _ in range(model.analysis_settings.monte_carlo_samples):
        scenario: dict[str, float] = {}
        for alternative in feasible:
            weighted: list[float] = []
            for criterion in model.criteria:
                estimate = alternative.criterion_estimates[criterion.id]
                sampled_value = rng.triangular(
                    estimate.minimum,
                    estimate.maximum,
                    estimate.most_likely,
                )
                utility, clamp_direction = normalize_utility(sampled_value, criterion)
                criterion_utility_samples[alternative.id][criterion.id].append(utility)
                if clamp_direction < 0:
                    clamp_counts[alternative.id][criterion.id][0] += 1
                elif clamp_direction > 0:
                    clamp_counts[alternative.id][criterion.id][1] += 1
                weighted.append(criterion.weight * utility)
            total = math.fsum(weighted)
            sample_totals[alternative.id].append(total)
            scenario[alternative.id] = total

        highest = max(scenario.values())
        winners = [
            alternative_id
            for alternative_id, utility in scenario.items()
            if math.isclose(
                utility,
                highest,
                rel_tol=0.0,
                abs_tol=NUMERICAL_TOLERANCE,
            )
        ]
        credit = 1.0 / len(winners)
        for alternative_id in winners:
            win_credits[alternative_id] += credit

    calculations: list[AlternativeCalculation] = []
    warnings: list[str] = []
    for alternative in feasible:
        raw_means, analytical_utility, analytical_clamped = analytical_data[alternative.id]
        diagnostics: list[ClampDiagnostic] = []
        for criterion in model.criteria:
            below_count, above_count = clamp_counts[alternative.id][criterion.id]
            mean_clamped = analytical_clamped[criterion.id]
            if mean_clamped or below_count or above_count:
                diagnostics.append(
                    ClampDiagnostic(
                        criterion_id=criterion.id,
                        analytical_mean_clamped=mean_clamped,
                        sampled_below_zero_count=below_count,
                        sampled_above_one_count=above_count,
                    )
                )
                warnings.append(
                    f"Clamping occurred for alternative {alternative.id!r}, criterion "
                    f"{criterion.id!r}: analytical mean clamped={mean_clamped}, "
                    f"sampled below 0={below_count}, sampled above 1={above_count}."
                )
        values = sample_totals[alternative.id]
        criterion_means = {
            criterion.id: float(
                stdlib_statistics.fmean(
                    criterion_utility_samples[alternative.id][criterion.id]
                )
            )
            for criterion in model.criteria
        }
        calculations.append(
            AlternativeCalculation(
                alternative_id=alternative.id,
                analytical_raw_means=raw_means,
                analytical_utility=analytical_utility,
                monte_carlo_mean_utility=float(stdlib_statistics.fmean(values)),
                criterion_mean_utilities=criterion_means,
                weighted_criterion_contributions={
                    criterion.id: criterion.weight * criterion_means[criterion.id]
                    for criterion in model.criteria
                },
                win_probability=(
                    win_credits[alternative.id]
                    / model.analysis_settings.monte_carlo_samples
                ),
                utility_distribution=summarize_distribution(values),
                clamp_diagnostics=tuple(diagnostics),
            )
        )

    ordered = tuple(
        sorted(
            calculations,
            key=lambda item: (
                -item.monte_carlo_mean_utility,
                -item.win_probability,
                item.alternative_id,
            ),
        )
    )
    sensitivity = analyze_weight_sensitivity(
        model,
        {
            result.alternative_id: result.criterion_mean_utilities
            for result in ordered
        },
    )
    return MultiCriteriaOutcome(
        model=model,
        alternative_results=ordered,
        excluded_alternatives=tuple(sorted(excluded, key=lambda item: item.alternative_id)),
        recommendation=_recommend(model, ordered),
        sensitivity=sensitivity,
        warnings=tuple(warnings),
    )
