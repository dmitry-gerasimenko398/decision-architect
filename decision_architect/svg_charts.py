"""Small, deterministic, accessible SVG charts for HTML reports."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Chart values must be numbers.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Chart values must be finite.")
    return number


def _label(value: object) -> str:
    return html.escape(str(value), quote=True)


def uncertainty_chart(alternatives: Sequence[Mapping[str, Any]]) -> str:
    """Render P10-P90 ranges, medians, and means on a shared 0-1 scale."""

    width = 760
    left = 180
    right = 34
    top = 58
    row_height = 54
    plot_width = width - left - right
    height = top + row_height * len(alternatives) + 48

    rows: list[str] = []
    descriptions: list[str] = []
    for index, alternative in enumerate(alternatives):
        distribution = alternative["utility_distribution"]
        p10 = _number(distribution["percentile_10"])
        median = _number(distribution["percentile_50"])
        p90 = _number(distribution["percentile_90"])
        mean = _number(alternative["monte_carlo_mean_utility"])
        name = _label(alternative["display_name"])
        y = top + index * row_height + 20
        x10 = left + max(0.0, min(1.0, p10)) * plot_width
        x50 = left + max(0.0, min(1.0, median)) * plot_width
        x90 = left + max(0.0, min(1.0, p90)) * plot_width
        xmean = left + max(0.0, min(1.0, mean)) * plot_width
        descriptions.append(
            f"{name}: P10 {p10:.3f}, median {median:.3f}, "
            f"mean {mean:.3f}, P90 {p90:.3f}."
        )
        rows.append(
            f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" '
            f'class="svg-label">{name}</text>'
            f'<line x1="{x10:.2f}" y1="{y:.2f}" x2="{x90:.2f}" y2="{y:.2f}" '
            'class="range-line" />'
            f'<line x1="{x10:.2f}" y1="{y - 7:.2f}" x2="{x10:.2f}" y2="{y + 7:.2f}" '
            'class="range-cap" />'
            f'<line x1="{x90:.2f}" y1="{y - 7:.2f}" x2="{x90:.2f}" y2="{y + 7:.2f}" '
            'class="range-cap" />'
            f'<rect x="{x50 - 4:.2f}" y="{y - 4:.2f}" width="8" height="8" '
            'class="median-marker"><title>Median</title></rect>'
            f'<circle cx="{xmean:.2f}" cy="{y:.2f}" r="5" class="mean-marker">'
            '<title>Mean</title></circle>'
        )

    ticks: list[str] = []
    for tick in range(6):
        value = tick / 5
        x = left + value * plot_width
        ticks.append(
            f'<line x1="{x:.2f}" y1="{top - 12}" x2="{x:.2f}" '
            f'y2="{height - 38}" class="grid-line" />'
            f'<text x="{x:.2f}" y="{height - 16}" text-anchor="middle" '
            f'class="svg-tick">{value:.1f}</text>'
        )

    description = " ".join(descriptions)
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="uncertainty-chart-title uncertainty-chart-desc">'
        '<title id="uncertainty-chart-title">Utility uncertainty by feasible alternative</title>'
        f'<desc id="uncertainty-chart-desc">{description} Circles mark means; squares mark medians.</desc>'
        '<text x="180" y="25" class="svg-heading">P10-P90 utility range on a shared 0-1 scale</text>'
        f'{"".join(ticks)}{"".join(rows)}'
        '<g transform="translate(180,44)">'
        '<circle cx="5" cy="0" r="5" class="mean-marker" />'
        '<text x="16" y="4" class="svg-tick">Mean</text>'
        '<rect x="76" y="-4" width="8" height="8" class="median-marker" />'
        '<text x="92" y="4" class="svg-tick">Median</text>'
        '</g></svg>'
    )


def contribution_chart(
    alternative_name: str,
    contributions: Sequence[tuple[str, float]],
    chart_index: int,
) -> str:
    """Render weighted criterion contributions for one alternative."""

    width = 700
    left = 190
    plot_width = 470
    row_height = 38
    height = 46 + row_height * len(contributions) + 28
    rows: list[str] = []
    descriptions: list[str] = []
    for index, (criterion, raw_value) in enumerate(contributions):
        value = _number(raw_value)
        y = 42 + index * row_height
        bar_width = max(0.0, min(1.0, value)) * plot_width
        criterion_text = _label(criterion)
        descriptions.append(f"{criterion_text} contributes {value:.4f} utility points.")
        rows.append(
            f'<text x="{left - 12}" y="{y + 15}" text-anchor="end" '
            f'class="svg-label">{criterion_text}</text>'
            f'<rect x="{left}" y="{y}" width="{plot_width}" height="20" class="bar-track" />'
            f'<rect x="{left}" y="{y}" width="{bar_width:.2f}" height="20" class="contribution-bar" />'
            f'<text x="{min(left + bar_width + 8, width - 36):.2f}" y="{y + 15}" '
            f'class="svg-value">{value:.4f}</text>'
        )
    safe_name = _label(alternative_name)
    title_id = f"contribution-chart-title-{chart_index}"
    desc_id = f"contribution-chart-desc-{chart_index}"
    return (
        f'<svg class="chart compact-chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{title_id} {desc_id}">'
        f'<title id="{title_id}">Weighted criterion contributions for {safe_name}</title>'
        f'<desc id="{desc_id}">{" ".join(descriptions)} '
        'These are modeled utility contributions, not causal effects.</desc>'
        f'<text x="{left}" y="22" class="svg-heading">{safe_name}</text>'
        f'{"".join(rows)}</svg>'
    )


def horizon_chart(policy: Sequence[Mapping[str, Any]], current_horizon: int) -> str:
    """Render stored explore-minus-exploit advantages by remaining horizon."""

    numeric_rows = [
        row
        for row in policy
        if row.get("action_advantage") is not None
    ]
    if not numeric_rows:
        return '<p class="empty-state">No numerical horizon advantages are available.</p>'

    width = 780
    height = 360
    left = 74
    right = 34
    top = 42
    bottom = 62
    plot_width = width - left - right
    plot_height = height - top - bottom
    horizons = [_number(row["remaining_opportunities"]) for row in numeric_rows]
    advantages = [_number(row["action_advantage"]) for row in numeric_rows]
    minimum_horizon = min(horizons)
    maximum_horizon = max(horizons)
    horizon_span = max(1.0, maximum_horizon - minimum_horizon)
    magnitude = max(0.1, max(abs(value) for value in advantages))

    def x_position(horizon: float) -> float:
        return left + (horizon - minimum_horizon) / horizon_span * plot_width

    def y_position(advantage: float) -> float:
        return top + (magnitude - advantage) / (2 * magnitude) * plot_height

    points = [
        (x_position(horizon), y_position(advantage))
        for horizon, advantage in zip(horizons, advantages, strict=True)
    ]
    path = " ".join(
        ("M" if index == 0 else "L") + f" {x:.2f} {y:.2f}"
        for index, (x, y) in enumerate(points)
    )
    point_markup: list[str] = []
    descriptions: list[str] = []
    for row, (x, y), advantage in zip(numeric_rows, points, advantages, strict=True):
        horizon = int(row["remaining_opportunities"])
        action = _label(str(row["recommended_action"]).upper())
        current = horizon == current_horizon
        marker_class = "policy-point current-point" if current else "policy-point"
        marker = (
            f'<rect x="{x - 6:.2f}" y="{y - 6:.2f}" width="12" height="12" '
            f'class="{marker_class}">'
            if current
            else f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" class="{marker_class}">'
        )
        closing = "</rect>" if current else "</circle>"
        point_markup.append(
            f'{marker}<title>{horizon} opportunities: {action}; advantage {advantage:.4f}'
            f'{"; current horizon" if current else ""}</title>{closing}'
            f'<text x="{x:.2f}" y="{height - 34}" text-anchor="middle" '
            f'class="svg-tick">{horizon}</text>'
        )
        descriptions.append(
            f"At {horizon} remaining {'opportunity' if horizon == 1 else 'opportunities'} the stored action is {action}, "
            f"with advantage {advantage:.4f}."
        )

    zero_y = y_position(0.0)
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="horizon-chart-title horizon-chart-desc">'
        '<title id="horizon-chart-title">Explore advantage by remaining opportunities</title>'
        f'<desc id="horizon-chart-desc">{" ".join(descriptions)} '
        'Positive values favor explore; negative values favor exploit. The square marks the current horizon.</desc>'
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{zero_y - top:.2f}" '
        'class="explore-region" />'
        f'<rect x="{left}" y="{zero_y:.2f}" width="{plot_width}" '
        f'height="{top + plot_height - zero_y:.2f}" class="exploit-region" />'
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{left + plot_width}" '
        f'y2="{zero_y:.2f}" class="zero-line" />'
        f'<text x="{left + 10}" y="{top + 18}" class="svg-region-label">EXPLORE region (+)</text>'
        f'<text x="{left + 10}" y="{top + plot_height - 10}" class="svg-region-label">EXPLOIT region (-)</text>'
        f'<path d="{path}" class="policy-line" />{"".join(point_markup)}'
        f'<text x="{left + plot_width / 2:.2f}" y="{height - 8}" text-anchor="middle" '
        'class="svg-label">Remaining opportunities</text>'
        f'<text x="18" y="{top + plot_height / 2:.2f}" text-anchor="middle" '
        'transform="rotate(-90 18 170)" class="svg-label">Explore − exploit</text>'
        '</svg>'
    )
