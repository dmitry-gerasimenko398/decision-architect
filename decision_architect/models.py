"""Typed, calculation-free data structures for Decision Architect model v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


ModelType: TypeAlias = Literal["multi_criteria", "sequential_exploration"]
PreferenceDirection: TypeAlias = Literal["maximize", "minimize"]
ConstraintOperator: TypeAlias = Literal["<=", "<", ">=", ">", "==", "!="]


@dataclass(frozen=True)
class TriangularDistribution:
    minimum: float
    most_likely: float
    maximum: float


@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    description: str
    weight: float
    preference_direction: PreferenceDirection
    worst_anchor: float
    best_anchor: float
    unit: str


@dataclass(frozen=True)
class HardConstraint:
    id: str
    name: str
    description: str
    criterion_id: str
    operator: ConstraintOperator
    threshold: float


@dataclass(frozen=True)
class Alternative:
    id: str
    name: str
    description: str
    constraint_results: dict[str, bool]
    criterion_estimates: dict[str, TriangularDistribution]


@dataclass(frozen=True)
class MultiCriteriaAnalysisSettings:
    random_seed: int
    monte_carlo_samples: int
    clamp_utility: bool


@dataclass(frozen=True)
class MultiCriteriaModel:
    model_version: str
    model_type: Literal["multi_criteria"]
    decision_id: str
    title: str
    description: str
    time_horizon: str
    confirmed_by_user: bool
    assumptions: tuple[str, ...]
    notes: str | None
    criteria: tuple[Criterion, ...]
    hard_constraints: tuple[HardConstraint, ...]
    alternatives: tuple[Alternative, ...]
    analysis_settings: MultiCriteriaAnalysisSettings


@dataclass(frozen=True)
class UtilityScale:
    minimum: float
    maximum: float
    unit: str
    description: str


@dataclass(frozen=True)
class SequentialState:
    remaining_opportunities: int
    unseen_options_remaining: int
    best_known_value: float


@dataclass(frozen=True)
class SequentialAnalysisSettings:
    quadrature_points: int


@dataclass(frozen=True)
class SequentialExplorationModel:
    model_version: str
    model_type: Literal["sequential_exploration"]
    decision_id: str
    title: str
    description: str
    time_horizon: str
    confirmed_by_user: bool
    assumptions: tuple[str, ...]
    notes: str | None
    utility_scale: UtilityScale
    state: SequentialState
    new_option_distribution: TriangularDistribution
    analysis_settings: SequentialAnalysisSettings


DecisionModel: TypeAlias = MultiCriteriaModel | SequentialExplorationModel


def _triangle_from_dict(data: dict[str, Any]) -> TriangularDistribution:
    return TriangularDistribution(
        minimum=float(data["minimum"]),
        most_likely=float(data["most_likely"]),
        maximum=float(data["maximum"]),
    )


def model_from_validated_dict(data: dict[str, Any]) -> DecisionModel:
    """Convert an already validated v1 dictionary into typed data structures.

    Call ``validation.validate_model_or_raise`` before this function. The function
    deliberately does not repair, normalize, or otherwise reinterpret data. The one
    contract-defined default is 101 sequential quadrature points when that optional
    settings object is absent.
    """

    common = {
        "model_version": data["model_version"],
        "decision_id": data["decision_id"],
        "title": data["title"],
        "description": data["description"],
        "time_horizon": data["time_horizon"],
        "confirmed_by_user": data["confirmed_by_user"],
        "assumptions": tuple(data["assumptions"]),
        "notes": data.get("notes"),
    }

    if data["model_type"] == "multi_criteria":
        criteria = tuple(
            Criterion(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                weight=float(item["weight"]),
                preference_direction=item["preference_direction"],
                worst_anchor=float(item["worst_anchor"]),
                best_anchor=float(item["best_anchor"]),
                unit=item["unit"],
            )
            for item in data["criteria"]
        )
        constraints = tuple(
            HardConstraint(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                criterion_id=item["criterion_id"],
                operator=item["operator"],
                threshold=float(item["threshold"]),
            )
            for item in data["hard_constraints"]
        )
        alternatives = tuple(
            Alternative(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                constraint_results=dict(item["constraint_results"]),
                criterion_estimates={
                    criterion_id: _triangle_from_dict(estimate)
                    for criterion_id, estimate in item["criterion_estimates"].items()
                },
            )
            for item in data["alternatives"]
        )
        settings = data["analysis_settings"]
        return MultiCriteriaModel(
            **common,
            model_type="multi_criteria",
            criteria=criteria,
            hard_constraints=constraints,
            alternatives=alternatives,
            analysis_settings=MultiCriteriaAnalysisSettings(
                random_seed=settings["random_seed"],
                monte_carlo_samples=settings["monte_carlo_samples"],
                clamp_utility=settings["clamp_utility"],
            ),
        )

    scale = data["utility_scale"]
    state = data["state"]
    settings = data.get("analysis_settings", {"quadrature_points": 101})
    return SequentialExplorationModel(
        **common,
        model_type="sequential_exploration",
        utility_scale=UtilityScale(
            minimum=float(scale["minimum"]),
            maximum=float(scale["maximum"]),
            unit=scale["unit"],
            description=scale["description"],
        ),
        state=SequentialState(
            remaining_opportunities=state["remaining_opportunities"],
            unseen_options_remaining=state["unseen_options_remaining"],
            best_known_value=float(state["best_known_value"]),
        ),
        new_option_distribution=_triangle_from_dict(data["new_option_distribution"]),
        analysis_settings=SequentialAnalysisSettings(
            quadrature_points=settings["quadrature_points"],
        ),
    )
