"""Fixed-sample analytical one-at-a-time weight sensitivity."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Mapping, TypeAlias

from .models import MultiCriteriaModel


SENSITIVITY_TOLERANCE = 1e-12
SwitchDirection: TypeAlias = Literal["lower", "upper"]
ChangeType: TypeAlias = Literal["winner_switch", "boundary_tie"]


class UndefinedWeightProportionsError(ValueError):
    """Raised when a target originally has all weight and others have no proportions."""


@dataclass(frozen=True)
class RobustWeightInterval:
    minimum_weight: float
    maximum_weight: float
    minimum_inclusive: bool
    maximum_inclusive: bool


@dataclass(frozen=True)
class WinnerSwitch:
    direction: SwitchDirection
    change_type: ChangeType
    threshold_weight: float
    new_winner_id: str | None
    new_tied_winner_ids: tuple[str, ...]
    tie_alternative_ids: tuple[str, ...]
    mean_utility_at_threshold: float
    verified: bool
    verification_epsilon: float
    lower_probe_weight: float
    lower_probe_leader_ids: tuple[str, ...]
    upper_probe_weight: float
    upper_probe_leader_ids: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class CriterionSensitivity:
    criterion_id: str
    baseline_weight: float
    status: str
    robust_interval: RobustWeightInterval | None
    lower_switch: WinnerSwitch | None
    upper_switch: WinnerSwitch | None
    explanation: str


@dataclass(frozen=True)
class WeightSensitivityOutcome:
    status: str
    method: str
    ranking_basis: str
    random_seed: int
    simulation_count: int
    fixed_sample_reused: bool
    numerical_tolerance: float
    verification_epsilon_rule: str
    baseline_winner_id: str | None
    baseline_tied_alternative_ids: tuple[str, ...]
    criteria: tuple[CriterionSensitivity, ...]
    explanation: str


@dataclass(frozen=True)
class _UtilityLine:
    intercept: float
    slope: float

    def evaluate(self, weight: float) -> float:
        return self.intercept + self.slope * weight


def recalculate_weights(
    original_weights: Mapping[str, float],
    target_criterion_id: str,
    target_weight: float,
) -> dict[str, float]:
    """Vary one weight and preserve every non-target weight proportion."""

    if not 0.0 <= target_weight <= 1.0:
        raise ValueError("target_weight must be between 0 and 1")
    if target_criterion_id not in original_weights:
        raise KeyError(target_criterion_id)
    original_target = original_weights[target_criterion_id]
    if original_target == 1.0:
        raise UndefinedWeightProportionsError(
            "The target criterion has weight 1, so the relative proportions of all other weights are undefined."
        )
    scale = (1.0 - target_weight) / (1.0 - original_target)
    return {
        criterion_id: (
            target_weight
            if criterion_id == target_criterion_id
            else original_weight * scale
        )
        for criterion_id, original_weight in original_weights.items()
    }


def _leaders(
    values: Mapping[str, float],
    *,
    tolerance: float = SENSITIVITY_TOLERANCE,
) -> tuple[str, ...]:
    if not values:
        return ()
    highest = max(values.values())
    return tuple(
        sorted(
            alternative_id
            for alternative_id, value in values.items()
            if math.isclose(value, highest, rel_tol=0.0, abs_tol=tolerance)
        )
    )


def winner_ids_at_weight(
    lines: Mapping[str, tuple[float, float] | _UtilityLine],
    weight: float,
) -> tuple[str, ...]:
    """Return every top mean-utility alternative at one target weight."""

    values = {
        alternative_id: (
            line.evaluate(weight)
            if isinstance(line, _UtilityLine)
            else line[0] + line[1] * weight
        )
        for alternative_id, line in lines.items()
    }
    return _leaders(values)


def _utility_lines(
    model: MultiCriteriaModel,
    target_criterion_id: str,
    criterion_mean_utilities: Mapping[str, Mapping[str, float]],
) -> dict[str, _UtilityLine]:
    weights = {criterion.id: criterion.weight for criterion in model.criteria}
    original_target = weights[target_criterion_id]
    if original_target == 1.0:
        raise UndefinedWeightProportionsError(target_criterion_id)

    denominator = 1.0 - original_target
    lines: dict[str, _UtilityLine] = {}
    for alternative_id, means in criterion_mean_utilities.items():
        target_mean = means[target_criterion_id]
        other_mean = math.fsum(
            weights[criterion_id] * mean
            for criterion_id, mean in means.items()
            if criterion_id != target_criterion_id
        ) / denominator
        lines[alternative_id] = _UtilityLine(
            intercept=other_mean,
            slope=target_mean - other_mean,
        )
    return lines


def _line_values(
    lines: Mapping[str, _UtilityLine],
    weight: float,
) -> dict[str, float]:
    return {
        alternative_id: line.evaluate(weight)
        for alternative_id, line in lines.items()
    }


def _candidate_crossings(
    lines: Mapping[str, _UtilityLine],
    baseline_winner_id: str,
) -> list[tuple[float, str]]:
    winner_line = lines[baseline_winner_id]
    crossings: list[tuple[float, str]] = []
    for competitor_id, competitor_line in lines.items():
        if competitor_id == baseline_winner_id:
            continue
        intercept_difference = winner_line.intercept - competitor_line.intercept
        slope_difference = winner_line.slope - competitor_line.slope
        if math.isclose(
            slope_difference,
            0.0,
            rel_tol=0.0,
            abs_tol=SENSITIVITY_TOLERANCE,
        ):
            continue
        crossing = -intercept_difference / slope_difference
        if -SENSITIVITY_TOLERANCE <= crossing <= 1.0 + SENSITIVITY_TOLERANCE:
            crossings.append((min(1.0, max(0.0, crossing)), competitor_id))
    return crossings


def _verification_delta(
    threshold: float,
    baseline_weight: float,
    all_crossings: list[tuple[float, str]],
) -> float:
    preferred = max(1e-7, 1e-6 * max(1.0, abs(threshold)))
    positive_limits = [abs(baseline_weight - threshold) / 2.0]
    positive_limits.extend(
        abs(other_threshold - threshold) / 3.0
        for other_threshold, _ in all_crossings
        if abs(other_threshold - threshold) > SENSITIVITY_TOLERANCE
    )
    usable = [limit for limit in positive_limits if limit > SENSITIVITY_TOLERANCE]
    return min([preferred, *usable]) if usable else preferred


def _build_switch(
    *,
    model: MultiCriteriaModel,
    criterion_id: str,
    direction: SwitchDirection,
    threshold: float,
    baseline_weight: float,
    baseline_winner_id: str,
    lines: Mapping[str, _UtilityLine],
    crossings: list[tuple[float, str]],
) -> WinnerSwitch | None:
    epsilon = _verification_delta(threshold, baseline_weight, crossings)
    lower_probe = max(0.0, threshold - epsilon)
    upper_probe = min(1.0, threshold + epsilon)
    threshold_values = _line_values(lines, threshold)
    tie_ids = _leaders(threshold_values)
    lower_leaders = _leaders(_line_values(lines, lower_probe))
    upper_leaders = _leaders(_line_values(lines, upper_probe))
    inner_leaders = upper_leaders if direction == "lower" else lower_leaders
    outer_leaders = lower_leaders if direction == "lower" else upper_leaders
    at_boundary = threshold in {0.0, 1.0}
    tied_at_threshold = (
        baseline_winner_id in tie_ids and len(tie_ids) > 1
    )
    if at_boundary:
        verified = tied_at_threshold and inner_leaders == (baseline_winner_id,)
        change_type: ChangeType = "boundary_tie"
        new_winner_id = None
        new_tied_winner_ids = tie_ids
    else:
        verified = (
            tied_at_threshold
            and inner_leaders == (baseline_winner_id,)
            and outer_leaders != (baseline_winner_id,)
        )
        change_type = "winner_switch"
        new_winner_id = outer_leaders[0] if len(outer_leaders) == 1 else None
        new_tied_winner_ids = outer_leaders if len(outer_leaders) > 1 else ()
    if not verified:
        return None

    names = {alternative.id: alternative.name for alternative in model.alternatives}
    criterion_name = next(
        criterion.name for criterion in model.criteria if criterion.id == criterion_id
    )
    if change_type == "boundary_tie":
        explanation = (
            f"At the permitted boundary weight {threshold:.12g} for {criterion_name}, "
            f"{names[baseline_winner_id]} ties with "
            f"{', '.join(names[item] for item in tie_ids if item != baseline_winner_id)}; "
            "there is no permitted weight beyond that boundary."
        )
    elif new_winner_id is not None:
        relation = "below" if direction == "lower" else "above"
        explanation = (
            f"When the weight of {criterion_name} moves {relation} {threshold:.12g}, "
            f"the fixed-sample mean-utility winner changes from {names[baseline_winner_id]} "
            f"to {names[new_winner_id]}."
        )
    else:
        relation = "below" if direction == "lower" else "above"
        explanation = (
            f"When the weight of {criterion_name} moves {relation} {threshold:.12g}, "
            f"{names[baseline_winner_id]} is no longer the unique fixed-sample winner; "
            f"the new leaders are {', '.join(names[item] for item in outer_leaders)}."
        )
    return WinnerSwitch(
        direction=direction,
        change_type=change_type,
        threshold_weight=threshold,
        new_winner_id=new_winner_id,
        new_tied_winner_ids=new_tied_winner_ids,
        tie_alternative_ids=tie_ids,
        mean_utility_at_threshold=max(threshold_values.values()),
        verified=True,
        verification_epsilon=epsilon,
        lower_probe_weight=lower_probe,
        lower_probe_leader_ids=lower_leaders,
        upper_probe_weight=upper_probe,
        upper_probe_leader_ids=upper_leaders,
        explanation=explanation,
    )


def _not_applicable_criteria(
    model: MultiCriteriaModel,
    status: str,
    explanation: str,
) -> tuple[CriterionSensitivity, ...]:
    return tuple(
        CriterionSensitivity(
            criterion_id=criterion.id,
            baseline_weight=criterion.weight,
            status=status,
            robust_interval=None,
            lower_switch=None,
            upper_switch=None,
            explanation=explanation,
        )
        for criterion in model.criteria
    )


def analyze_weight_sensitivity(
    model: MultiCriteriaModel,
    criterion_mean_utilities: Mapping[str, Mapping[str, float]],
) -> WeightSensitivityOutcome:
    """Analyze every criterion without drawing any additional random samples."""

    common = {
        "method": "fixed_sample_linear_weight_sensitivity",
        "ranking_basis": "monte_carlo_mean_utility",
        "random_seed": model.analysis_settings.random_seed,
        "simulation_count": model.analysis_settings.monte_carlo_samples,
        "fixed_sample_reused": True,
        "numerical_tolerance": SENSITIVITY_TOLERANCE,
        "verification_epsilon_rule": "preferred max(1e-7, 1e-6 * max(1, abs(threshold))), reduced near adjacent crossings",
    }
    feasible_ids = tuple(sorted(criterion_mean_utilities))
    if not feasible_ids:
        explanation = "Weight sensitivity is not applicable because no alternative is feasible."
        return WeightSensitivityOutcome(
            **common,
            status="not_applicable_no_feasible_alternatives",
            baseline_winner_id=None,
            baseline_tied_alternative_ids=(),
            criteria=_not_applicable_criteria(model, "not_applicable", explanation),
            explanation=explanation,
        )
    if len(feasible_ids) == 1:
        explanation = "Weight sensitivity is not applicable because only one alternative is feasible."
        return WeightSensitivityOutcome(
            **common,
            status="not_applicable_only_one_feasible_alternative",
            baseline_winner_id=feasible_ids[0],
            baseline_tied_alternative_ids=(),
            criteria=_not_applicable_criteria(model, "not_applicable", explanation),
            explanation=explanation,
        )

    original_weights = {criterion.id: criterion.weight for criterion in model.criteria}
    baseline_values = {
        alternative_id: math.fsum(
            original_weights[criterion_id] * mean
            for criterion_id, mean in means.items()
        )
        for alternative_id, means in criterion_mean_utilities.items()
    }
    baseline_leaders = _leaders(baseline_values)
    if len(baseline_leaders) != 1:
        explanation = (
            "Weight sensitivity is not applicable because the baseline fixed-sample mean utilities "
            "are tied; no arbitrary baseline winner was selected."
        )
        return WeightSensitivityOutcome(
            **common,
            status="not_applicable_baseline_tie",
            baseline_winner_id=None,
            baseline_tied_alternative_ids=baseline_leaders,
            criteria=_not_applicable_criteria(model, "not_applicable", explanation),
            explanation=explanation,
        )

    baseline_winner_id = baseline_leaders[0]
    criterion_results: list[CriterionSensitivity] = []
    for criterion in model.criteria:
        if criterion.weight == 1.0:
            explanation = (
                "This criterion has baseline weight 1, so the relative proportions of every "
                "other criterion are undefined and are not invented."
            )
            criterion_results.append(
                CriterionSensitivity(
                    criterion_id=criterion.id,
                    baseline_weight=criterion.weight,
                    status="not_analyzable_baseline_weight_one",
                    robust_interval=None,
                    lower_switch=None,
                    upper_switch=None,
                    explanation=explanation,
                )
            )
            continue

        lines = _utility_lines(model, criterion.id, criterion_mean_utilities)
        crossings = _candidate_crossings(lines, baseline_winner_id)
        lower_candidates = [
            value for value, _ in crossings
            if value < criterion.weight - SENSITIVITY_TOLERANCE
        ]
        upper_candidates = [
            value for value, _ in crossings
            if value > criterion.weight + SENSITIVITY_TOLERANCE
        ]
        lower_switch = None
        for threshold in sorted(set(lower_candidates), reverse=True):
            lower_switch = _build_switch(
                model=model,
                criterion_id=criterion.id,
                direction="lower",
                threshold=threshold,
                baseline_weight=criterion.weight,
                baseline_winner_id=baseline_winner_id,
                lines=lines,
                crossings=crossings,
            )
            if lower_switch is not None:
                break
        upper_switch = None
        for threshold in sorted(set(upper_candidates)):
            upper_switch = _build_switch(
                model=model,
                criterion_id=criterion.id,
                direction="upper",
                threshold=threshold,
                baseline_weight=criterion.weight,
                baseline_winner_id=baseline_winner_id,
                lines=lines,
                crossings=crossings,
            )
            if upper_switch is not None:
                break

        robust = RobustWeightInterval(
            minimum_weight=(lower_switch.threshold_weight if lower_switch else 0.0),
            maximum_weight=(upper_switch.threshold_weight if upper_switch else 1.0),
            minimum_inclusive=lower_switch is None,
            maximum_inclusive=upper_switch is None,
        )
        if lower_switch is None and upper_switch is None:
            explanation = (
                f"{baseline_winner_id!r} remains the unique fixed-sample mean-utility winner "
                "across the full permitted weight range from 0 to 1."
            )
        else:
            explanation = (
                f"{baseline_winner_id!r} remains the unique fixed-sample mean-utility winner "
                f"inside the robust interval from {robust.minimum_weight:.12g} to "
                f"{robust.maximum_weight:.12g}; a switch boundary is a tie and is excluded."
            )
        criterion_results.append(
            CriterionSensitivity(
                criterion_id=criterion.id,
                baseline_weight=criterion.weight,
                status="analyzed",
                robust_interval=robust,
                lower_switch=lower_switch,
                upper_switch=upper_switch,
                explanation=explanation,
            )
        )

    return WeightSensitivityOutcome(
        **common,
        status="analyzed",
        baseline_winner_id=baseline_winner_id,
        baseline_tied_alternative_ids=(),
        criteria=tuple(criterion_results),
        explanation=(
            "Each criterion was varied independently from 0 to 1 using the same Monte Carlo "
            "sample; winner switches concern mean-utility ranking, not the 60% close-call classification."
        ),
    )
