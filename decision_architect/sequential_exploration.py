"""Deterministic finite-horizon explore-versus-exploit calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, TypeAlias

from .models import SequentialExplorationModel, TriangularDistribution


DEFAULT_QUADRATURE_POINTS = 101
ACTION_COMPARISON_TOLERANCE = 1e-10
MEMOIZATION_DECIMAL_PLACES = 12

Action: TypeAlias = Literal["explore", "exploit", "indifferent"]


class SequentialCalculationError(ValueError):
    """Raised when a validated sequential model cannot be calculated safely."""


@dataclass(frozen=True)
class ActionValues:
    exploit_value: float
    explore_value: float | None
    recommended_action: Action
    action_advantage: float | None


@dataclass(frozen=True)
class HorizonPolicy:
    remaining_opportunities: int
    exploit_value: float
    explore_value: float | None
    recommended_action: Action
    action_advantage: float | None


@dataclass(frozen=True)
class ActionSwitchPoint:
    remaining_opportunities: int
    previous_action: Action
    recommended_action: Action


@dataclass(frozen=True)
class SequentialExplorationOutcome:
    model: SequentialExplorationModel
    expected_total_utility: float
    current_action_values: ActionValues
    policy_by_remaining_opportunities: tuple[HorizonPolicy, ...]
    action_switch_points: tuple[ActionSwitchPoint, ...]
    memoized_state_count: int
    warnings: tuple[str, ...]


def inverse_triangular_cdf(
    probability: float,
    distribution: TriangularDistribution,
) -> float:
    """Return the triangular quantile for a probability from 0 through 1."""

    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    minimum = distribution.minimum
    mode = distribution.most_likely
    maximum = distribution.maximum
    if not minimum <= mode <= maximum:
        raise ValueError("triangular distribution requires minimum <= mode <= maximum")
    if minimum == maximum:
        return minimum

    split_probability = (mode - minimum) / (maximum - minimum)
    if probability < split_probability:
        return minimum + math.sqrt(
            probability * (maximum - minimum) * (mode - minimum)
        )
    return maximum - math.sqrt(
        (1.0 - probability) * (maximum - minimum) * (maximum - mode)
    )


def midpoint_quantile_nodes(
    distribution: TriangularDistribution,
    quadrature_points: int = DEFAULT_QUADRATURE_POINTS,
) -> tuple[float, ...]:
    """Build the fixed midpoint-quantile grid used for every expectation."""

    if (
        isinstance(quadrature_points, bool)
        or not isinstance(quadrature_points, int)
        or quadrature_points < 1
        or quadrature_points % 2 == 0
    ):
        raise ValueError("quadrature_points must be a positive odd integer")
    return tuple(
        inverse_triangular_cdf((index + 0.5) / quadrature_points, distribution)
        for index in range(quadrature_points)
    )


def compare_actions(exploit_value: float, explore_value: float | None) -> Action:
    """Compare available action values without choosing arbitrarily on a tie."""

    if explore_value is None:
        return "exploit"
    advantage = explore_value - exploit_value
    if advantage > ACTION_COMPARISON_TOLERANCE:
        return "explore"
    if advantage < -ACTION_COMPARISON_TOLERANCE:
        return "exploit"
    return "indifferent"


class SequentialDynamicProgram:
    """Memoized Bellman recursion over a deterministic quadrature grid."""

    def __init__(
        self,
        distribution: TriangularDistribution,
        quadrature_points: int = DEFAULT_QUADRATURE_POINTS,
    ) -> None:
        self.distribution = distribution
        self.quadrature_points = quadrature_points
        self.nodes = midpoint_quantile_nodes(distribution, quadrature_points)
        self._memoized_values: dict[tuple[int, int, float], float] = {}

    @staticmethod
    def canonical_best_known(value: float) -> float:
        canonical = round(float(value), MEMOIZATION_DECIMAL_PLACES)
        return 0.0 if canonical == 0.0 else canonical

    def _value(self, remaining: int, unseen: int, best_known: float) -> float:
        if remaining < 0 or unseen < 0:
            raise SequentialCalculationError("state counts cannot be negative")
        target = (remaining, unseen, best_known)
        stack = [target]
        expanded: set[tuple[int, int, float]] = set()
        while stack:
            state = stack[-1]
            if state in self._memoized_values:
                stack.pop()
                continue
            state_remaining, state_unseen, state_best = state
            if state_remaining == 0:
                self._memoized_values[state] = 0.0
                stack.pop()
                continue

            exploit_child = (state_remaining - 1, state_unseen, state_best)
            dependencies = [exploit_child]
            if state_unseen > 0:
                dependencies.extend(
                    (
                        state_remaining - 1,
                        state_unseen - 1,
                        self.canonical_best_known(max(state_best, sampled_value)),
                    )
                    for sampled_value in self.nodes
                )
            if state not in expanded:
                expanded.add(state)
                missing = list(
                    dict.fromkeys(
                        dependency
                        for dependency in dependencies
                        if dependency not in self._memoized_values
                    )
                )
                stack.extend(missing)
                continue

            exploit_value = state_best + self._memoized_values[exploit_child]
            if state_unseen == 0:
                self._memoized_values[state] = exploit_value
            else:
                explore_value = math.fsum(
                    sampled_value
                    + self._memoized_values[
                        (
                            state_remaining - 1,
                            state_unseen - 1,
                            self.canonical_best_known(max(state_best, sampled_value)),
                        )
                    ]
                    for sampled_value in self.nodes
                ) / self.quadrature_points
                self._memoized_values[state] = max(exploit_value, explore_value)
            expanded.remove(state)
            stack.pop()
        return self._memoized_values[target]

    def optimal_value(self, remaining: int, unseen: int, best_known: float) -> float:
        """Return V(t, u, b), including the public zero-horizon base case."""

        return self._value(remaining, unseen, self.canonical_best_known(best_known))

    def action_values(self, remaining: int, unseen: int, best_known: float) -> ActionValues:
        if remaining < 1:
            raise SequentialCalculationError("action values require at least one opportunity")
        canonical_best = self.canonical_best_known(best_known)
        exploit_value = canonical_best + self._value(
            remaining - 1,
            unseen,
            canonical_best,
        )
        explore_value: float | None = None
        if unseen > 0:
            explore_value = math.fsum(
                sampled_value
                + self._value(
                    remaining - 1,
                    unseen - 1,
                    self.canonical_best_known(max(canonical_best, sampled_value)),
                )
                for sampled_value in self.nodes
            ) / self.quadrature_points
        action = compare_actions(exploit_value, explore_value)
        advantage = None if explore_value is None else explore_value - exploit_value
        return ActionValues(exploit_value, explore_value, action, advantage)

    @property
    def memoized_state_count(self) -> int:
        return len(self._memoized_values)


def analyze_sequential_exploration(
    model: SequentialExplorationModel,
) -> SequentialExplorationOutcome:
    """Calculate the current action and horizon policy for a confirmed model."""

    state = model.state
    program = SequentialDynamicProgram(
        model.new_option_distribution,
        model.analysis_settings.quadrature_points,
    )
    current = program.action_values(
        state.remaining_opportunities,
        state.unseen_options_remaining,
        state.best_known_value,
    )
    expected_total_utility = program.optimal_value(
        state.remaining_opportunities,
        state.unseen_options_remaining,
        state.best_known_value,
    )

    policy = tuple(
        HorizonPolicy(
            remaining_opportunities=horizon,
            exploit_value=values.exploit_value,
            explore_value=values.explore_value,
            recommended_action=values.recommended_action,
            action_advantage=values.action_advantage,
        )
        for horizon in range(1, state.remaining_opportunities + 1)
        for values in (
            program.action_values(
                horizon,
                state.unseen_options_remaining,
                state.best_known_value,
            ),
        )
    )
    switches = tuple(
        ActionSwitchPoint(
            remaining_opportunities=current_row.remaining_opportunities,
            previous_action=previous_row.recommended_action,
            recommended_action=current_row.recommended_action,
        )
        for previous_row, current_row in zip(policy, policy[1:])
        if previous_row.recommended_action != current_row.recommended_action
    )
    warnings = (
        "Continuous expectations use deterministic midpoint quantile quadrature, so values are numerical approximations.",
    )
    return SequentialExplorationOutcome(
        model=model,
        expected_total_utility=expected_total_utility,
        current_action_values=current,
        policy_by_remaining_opportunities=policy,
        action_switch_points=switches,
        memoized_state_count=program.memoized_state_count,
        warnings=warnings,
    )
