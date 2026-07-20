"""Validated model dispatch for implemented Decision Architect engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DecisionModel, MultiCriteriaModel, SequentialExplorationModel
from .multi_criteria import analyze_multi_criteria
from .result_serialization import (
    multi_criteria_result_to_dict,
    sequential_exploration_result_to_dict,
)
from .sequential_exploration import analyze_sequential_exploration
from .validation import load_validated_model


class UnsupportedModelTypeError(ValueError):
    pass


def analyze_model(model: DecisionModel) -> dict[str, Any]:
    if isinstance(model, MultiCriteriaModel):
        return multi_criteria_result_to_dict(analyze_multi_criteria(model))
    if isinstance(model, SequentialExplorationModel):
        return sequential_exploration_result_to_dict(
            analyze_sequential_exploration(model)
        )
    raise UnsupportedModelTypeError(f"Unsupported model type: {type(model).__name__}")


def analyze_file(path: str | Path) -> dict[str, Any]:
    return analyze_model(load_validated_model(path))
