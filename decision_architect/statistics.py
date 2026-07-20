"""Small deterministic statistics helpers using only Python's standard library."""

from __future__ import annotations

import math
import statistics as stdlib_statistics
from dataclasses import dataclass
from typing import Sequence


PERCENTILE_METHOD = "linear_interpolation_index_n_minus_1"


@dataclass(frozen=True)
class DistributionSummary:
    minimum: float
    maximum: float
    standard_deviation: float
    percentile_10: float
    percentile_50: float
    percentile_90: float


def percentile(values: Sequence[float], probability: float) -> float:
    """Return a percentile using linear interpolation at index ``(n - 1) * p``."""

    if not values:
        raise ValueError("Cannot calculate a percentile of an empty sequence.")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("Percentile probability must be between 0 and 1.")

    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return float(ordered[lower_index])
    fraction = position - lower_index
    return float(
        ordered[lower_index]
        + fraction * (ordered[upper_index] - ordered[lower_index])
    )

def summarize_distribution(values: Sequence[float]) -> DistributionSummary:
    if not values:
        raise ValueError("Cannot summarize an empty distribution.")
    return DistributionSummary(
        minimum=float(min(values)),
        maximum=float(max(values)),
        standard_deviation=float(stdlib_statistics.pstdev(values)),
        percentile_10=percentile(values, 0.10),
        percentile_50=percentile(values, 0.50),
        percentile_90=percentile(values, 0.90),
    )
