"""Deterministic helpers for the conversational interview layer.

These functions structure user-provided answers. They do not conduct an interview,
infer preferences, or perform decision calculations.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal


ModelSelection = Literal["multi_criteria", "sequential_exploration"]
ConditionKind = Literal["hard_constraint", "preference"]


@dataclass(frozen=True)
class SelectionResult:
    model_type: ModelSelection | None
    explanation: str
    clarification_question: str | None = None


def safe_identifier(value: str, *, fallback: str = "item", maximum_length: int = 64) -> str:
    """Convert a user label to a stable model-v1 identifier."""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    identifier = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not identifier or not identifier[0].isalpha():
        fallback_id = re.sub(r"[^a-z0-9]+", "-", fallback.lower()).strip("-")
        identifier = fallback_id if fallback_id and fallback_id[0].isalpha() else "item"
    return identifier[:maximum_length].rstrip("-") or "item"


def select_model_type(
    *,
    repeated_choice: bool | None,
    trying_new_produces_information: bool | None,
    discovered_option_reusable: bool | None,
    finite_opportunities: bool | None,
    known_alternatives: bool | None,
    competing_criteria: bool | None,
) -> SelectionResult:
    """Select a supported structure from explicitly answered structural questions."""

    sequential_signals = (
        repeated_choice,
        trying_new_produces_information,
        discovered_option_reusable,
        finite_opportunities,
    )
    if all(signal is True for signal in sequential_signals):
        return SelectionResult(
            "sequential_exploration",
            "The choice repeats over a finite horizon, exploration reveals reusable information, "
            "and the central structure is explore versus exploit.",
        )
    if repeated_choice is False and known_alternatives is True and competing_criteria is True:
        return SelectionResult(
            "multi_criteria",
            "This is primarily a one-time comparison of known alternatives across competing criteria.",
        )
    if any(signal is None for signal in sequential_signals) or repeated_choice is None:
        return SelectionResult(
            None,
            "The decision structure is not yet clear enough to choose a supported model honestly.",
            "Will you make this choice only once, or will you have several future opportunities "
            "to try new options and reuse the best one you discover?",
        )
    return SelectionResult(
        None,
        "The situation does not clearly fit either supported model without distorting it.",
    )


def classify_condition(*, eliminate_if_violated: bool) -> ConditionKind:
    """Classify the user's explicit answer about compensation versus elimination."""

    return "hard_constraint" if eliminate_if_violated else "preference"


def triangle_contradiction(
    minimum: float,
    most_likely: float,
    maximum: float,
) -> str | None:
    """Return a targeted correction message for a malformed three-point estimate."""

    values = (minimum, most_likely, maximum)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return "Minimum, most likely, and maximum must each be numbers."
    if any(not math.isfinite(float(value)) for value in values):
        return "Minimum, most likely, and maximum must each be finite numbers."
    if minimum > most_likely:
        return "The minimum is greater than the most likely value. Which value should be corrected?"
    if most_likely > maximum:
        return "The most likely value is greater than the maximum. Which value should be corrected?"
    return None


def swing_points_to_weights(points: dict[str, float]) -> dict[str, float]:
    """Convert user-allocated swing-importance points to normalized weights."""

    if len(points) < 2:
        raise ValueError("Swing weighting requires at least two criteria.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value < 0
        for value in points.values()
    ):
        raise ValueError("Importance points must be finite non-negative numbers.")
    total = math.fsum(float(value) for value in points.values())
    if total <= 0:
        raise ValueError("At least one criterion must receive positive importance points.")
    return {criterion_id: float(value) / total for criterion_id, value in points.items()}
