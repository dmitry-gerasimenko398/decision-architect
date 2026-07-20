"""Transparent decision-model contracts and deterministic analysis components."""

from .models import (
    Alternative,
    Criterion,
    DecisionModel,
    HardConstraint,
    MultiCriteriaModel,
    SequentialAnalysisSettings,
    SequentialExplorationModel,
    TriangularDistribution,
)

__version__ = "1.0.0-rc1"

__all__ = [
    "Alternative",
    "Criterion",
    "DecisionModel",
    "HardConstraint",
    "MultiCriteriaModel",
    "SequentialAnalysisSettings",
    "SequentialExplorationModel",
    "TriangularDistribution",
    "__version__",
]
