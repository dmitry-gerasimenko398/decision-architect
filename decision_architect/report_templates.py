"""Pure, escaped HTML templates for Decision Architect reports."""

from __future__ import annotations

import html
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .svg_charts import contribution_chart, horizon_chart, uncertainty_chart


CONDITIONALITY_STATEMENT = (
    "This is a conditional recommendation based on the user’s stated preferences, "
    "estimates, constraints, and assumptions—not an objectively correct life decision."
)
REPORT_GENERATOR_VERSION = "1.0.0-rc2"


BASE_STYLES = r"""
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #526079;
  --line: #d8deea;
  --paper: #ffffff;
  --wash: #f4f6fa;
  --brand: #143c7d;
  --brand-2: #0b6b67;
  --accent: #d97706;
  --danger: #a72c37;
  --radius: 16px;
  --shadow: 0 12px 34px rgba(23, 32, 51, 0.09);
}
* { box-sizing: border-box; }
html { background: #e9edf4; }
body {
  margin: 0;
  color: var(--ink);
  background: linear-gradient(180deg, #e8eef9 0, #f6f7fa 380px, #f6f7fa 100%);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
  line-height: 1.55;
}
a { color: var(--brand); text-underline-offset: 3px; }
.page { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 60px; }
.product-header {
  display: flex; justify-content: space-between; gap: 24px; align-items: flex-start;
  color: #fff; background: #102d5c; border-radius: 20px; padding: 28px 32px;
  box-shadow: var(--shadow); border-top: 5px solid #38a69d;
}
.eyebrow { margin: 0 0 4px; font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.product-header h1 { margin: 0; font-size: clamp(1.65rem, 4vw, 2.6rem); line-height: 1.1; }
.product-header p { margin: 10px 0 0; color: #dce8ff; max-width: 760px; }
.version-stack { min-width: 172px; margin: 0; font-size: .86rem; }
.version-stack div { display: flex; justify-content: space-between; gap: 14px; border-bottom: 1px solid #ffffff35; padding: 4px 0; }
.version-stack dt { color: #bcd0f1; }
.version-stack dd { margin: 0; font-weight: 700; }
.conditionality {
  margin: 18px 0 0; padding: 15px 18px; border: 2px solid #8b5a04; border-radius: 12px;
  background: #fff8e7; color: #563600; font-weight: 700;
}
main section { margin-top: 24px; }
.panel { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 24px; box-shadow: 0 5px 16px rgba(23,32,51,.045); }
.recommendation { border-left: 7px solid var(--brand-2); padding: 28px; }
.recommendation.tie, .recommendation.close { border-left-color: var(--accent); }
.recommendation.infeasible { border-left-color: var(--danger); }
.section-kicker { color: var(--brand-2); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; font-size: .76rem; margin: 0 0 4px; }
h2 { margin: 0 0 14px; font-size: 1.45rem; line-height: 1.2; }
h3 { margin: 24px 0 10px; font-size: 1.08rem; }
p { margin: 8px 0 14px; }
.lede { font-size: 1.08rem; color: #34415a; max-width: 880px; }
.status { display: inline-block; margin-bottom: 12px; padding: 5px 10px; border-radius: 999px; background: #e2f3ef; color: #075b56; font-size: .78rem; font-weight: 850; letter-spacing: .06em; text-transform: uppercase; }
.status.caution { background: #fff0cf; color: #774800; }
.status.danger { background: #fde8ea; color: #84212c; }
.hero-action { margin: 2px 0 8px; font-size: clamp(1.7rem, 4vw, 2.65rem); line-height: 1.05; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 12px; margin: 20px 0 0; }
.metric { padding: 14px 16px; border-radius: 12px; background: var(--wash); border: 1px solid #e2e6ee; }
.metric span { display: block; color: var(--muted); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.metric strong { display: block; margin-top: 3px; font-size: 1.25rem; font-variant-numeric: tabular-nums; }
.two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
caption { text-align: left; padding: 11px 13px; color: var(--muted); font-size: .88rem; font-weight: 700; }
th, td { padding: 10px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }
th { background: #eef2f8; color: #25324a; font-size: .8rem; letter-spacing: .025em; }
tbody tr:last-child td { border-bottom: 0; }
tr.current-row { outline: 3px solid #143c7d; outline-offset: -3px; background: #edf4ff; }
.numeric { text-align: right; white-space: nowrap; }
.id { color: var(--muted); font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; font-size: .84em; }
.chart { display: block; width: 100%; height: auto; margin: 14px 0; background: #fbfcfe; border: 1px solid var(--line); border-radius: 12px; }
.compact-chart { max-height: 380px; }
.grid-line { stroke: #dfe4ec; stroke-width: 1; }
.range-line { stroke: #143c7d; stroke-width: 8; stroke-linecap: round; }
.range-cap { stroke: #143c7d; stroke-width: 2; }
.mean-marker { fill: #b74713; stroke: #fff; stroke-width: 2; }
.median-marker { fill: #0b6b67; stroke: #fff; stroke-width: 2; }
.svg-label, .svg-tick, .svg-value, .svg-heading, .svg-region-label { font-family: ui-sans-serif, system-ui, sans-serif; fill: #24324a; }
.svg-label { font-size: 13px; font-weight: 700; }
.svg-tick { font-size: 12px; }
.svg-value { font-size: 12px; font-weight: 800; }
.svg-heading { font-size: 14px; font-weight: 800; }
.svg-region-label { font-size: 12px; font-weight: 800; }
.bar-track { fill: #e7ebf2; }
.contribution-bar { fill: #287f79; }
.explore-region { fill: #e4f3ef; }
.exploit-region { fill: #fff1dc; }
.zero-line { stroke: #29364d; stroke-width: 2; stroke-dasharray: 7 5; }
.policy-line { fill: none; stroke: #143c7d; stroke-width: 3; }
.policy-point { fill: #143c7d; stroke: #fff; stroke-width: 2; }
.current-point { fill: #d05c16; stroke: #172033; stroke-width: 2; }
.note { border-left: 4px solid var(--accent); background: #fff8e8; padding: 12px 15px; }
.distinction { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.distinction > div { padding: 14px; background: var(--wash); border-radius: 10px; }
.interval { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; font-weight: 800; }
.clean-list { margin: 8px 0; padding-left: 22px; }
.clean-list li { margin: 6px 0; }
.empty-state { color: var(--muted); font-style: italic; }
details { margin-top: 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); }
summary { cursor: pointer; padding: 14px 16px; font-weight: 800; color: var(--brand); }
details[open] summary { border-bottom: 1px solid var(--line); }
.details-body { padding: 16px; }
.formula { overflow-x: auto; padding: 12px 14px; border-radius: 8px; background: #182238; color: #f5f7fb; font: .91rem/1.6 ui-monospace, "Cascadia Mono", Consolas, monospace; white-space: pre-wrap; }
.raw-json { max-height: 580px; overflow: auto; margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.report-footer { color: var(--muted); text-align: center; font-size: .85rem; margin-top: 26px; }
.demo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
.demo-card { display: block; color: inherit; text-decoration: none; padding: 22px; border-radius: 14px; border: 1px solid var(--line); background: #fff; box-shadow: 0 4px 14px rgba(23,32,51,.05); }
.demo-card:hover, .demo-card:focus-visible { outline: 3px solid #2e69ba; outline-offset: 3px; transform: translateY(-2px); }
.demo-card strong { color: var(--brand); font-size: 1.14rem; }
.demo-card span { display: block; color: var(--muted); margin-top: 8px; }
@media (max-width: 760px) {
  .page { width: min(100% - 20px, 1180px); padding-top: 10px; }
  .product-header { display: block; padding: 22px; }
  .version-stack { margin-top: 20px; }
  .two-column, .distinction { grid-template-columns: 1fr; }
  .panel { padding: 18px; }
  th, td { padding: 8px; }
}
@media print {
  @page { margin: 14mm; }
  html, body { background: #fff; }
  body { font-size: 10.5pt; color: #000; }
  .page { width: 100%; margin: 0; padding: 0; }
  .product-header { color: #000; background: #fff; border: 2px solid #000; box-shadow: none; }
  .product-header p, .version-stack dt { color: #222; }
  .panel, details, .chart { box-shadow: none; break-inside: avoid; }
  section, table, .metric { break-inside: avoid; }
  details > .details-body { display: block; }
  .raw-json { max-height: none; }
  a { color: #000; text-decoration: none; }
}
"""


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _humanize(identifier: object, *, remove_example: bool = False) -> str:
    text = str(identifier)
    if remove_example:
        text = re.sub(r"[-_]example$", "", text, flags=re.IGNORECASE)
    words = re.sub(r"[-_]+", " ", text).strip()
    return words.title() if words else "Untitled decision"


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Report values must be numeric.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Report values must be finite.")
    return number


def _format_number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "Unavailable"
    number = _finite(value)
    if abs(number) >= 1000:
        return f"{number:,.{digits}f}".rstrip("0").rstrip(".")
    return f"{number:.{digits}f}".rstrip("0").rstrip(".") or "0"


def _format_percent(value: Any) -> str:
    if value is None:
        return "Unavailable"
    return f"{_finite(value) * 100:.1f}%"


def _format_weight(value: Any) -> str:
    return _format_number(value, 6)


def _display_name(result: Mapping[str, Any], identifier: object) -> str:
    metadata = result.get("display_metadata")
    if isinstance(metadata, Mapping):
        alternatives = metadata.get("alternatives")
        if isinstance(alternatives, Mapping) and isinstance(alternatives.get(str(identifier)), str):
            return str(alternatives[str(identifier)])
    return _humanize(identifier)


def _criterion_name(result: Mapping[str, Any], identifier: object) -> str:
    metadata = result.get("display_metadata")
    if isinstance(metadata, Mapping):
        criteria = metadata.get("criteria")
        if isinstance(criteria, Mapping) and isinstance(criteria.get(str(identifier)), str):
            return str(criteria[str(identifier)])
    return _humanize(identifier)


def _decision_title(result: Mapping[str, Any]) -> str:
    metadata = result.get("decision_metadata")
    if isinstance(metadata, Mapping) and isinstance(metadata.get("title"), str):
        return str(metadata["title"])
    return _humanize(result.get("decision_id", "decision"), remove_example=True)


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>'


def _version_stack(result: Mapping[str, Any]) -> str:
    rows = [
        ("Model", result.get("model_version", "Unknown")),
        ("Result", result.get("result_version", "Unknown")),
        ("Engine", result.get("engine_version", "Not recorded")),
        ("Report", REPORT_GENERATOR_VERSION),
    ]
    return '<dl class="version-stack">' + "".join(
        f'<div><dt>{_escape(label)}</dt><dd>{_escape(value)}</dd></div>' for label, value in rows
    ) + "</dl>"


def _header(result: Mapping[str, Any], model_label: str) -> str:
    title = _decision_title(result)
    return (
        '<header class="product-header"><div>'
        '<p class="eyebrow">Decision Architect</p>'
        f'<h1>{_escape(title)}</h1>'
        f'<p>{_escape(model_label)} · Decision ID <span class="id">'
        f'{_escape(result.get("decision_id", "unknown"))}</span></p>'
        '</div>' + _version_stack(result) + '</header>'
        f'<p class="conditionality">{_escape(CONDITIONALITY_STATEMENT)}</p>'
    )


def _list_section(title: str, values: Sequence[object], empty_text: str) -> str:
    if not values:
        content = f'<p class="empty-state">{_escape(empty_text)}</p>'
    else:
        content = '<ul class="clean-list">' + "".join(
            f'<li>{_escape(value)}</li>' for value in values
        ) + '</ul>'
    return f'<div><h3>{_escape(title)}</h3>{content}</div>'


def _metadata_tables(result: Mapping[str, Any]) -> str:
    method = result.get("method", {})
    reproducibility = result.get("reproducibility", {})

    def rows(mapping: object) -> str:
        if not isinstance(mapping, Mapping):
            return '<tr><td colspan="2">Not recorded</td></tr>'
        rendered = []
        for key, value in mapping.items():
            if isinstance(value, (dict, list)):
                display = json.dumps(value, ensure_ascii=False, sort_keys=True)
            else:
                display = value
            rendered.append(
                f'<tr><th scope="row">{_escape(_humanize(key))}</th><td>{_escape(display)}</td></tr>'
            )
        return "".join(rendered)

    return (
        '<div class="two-column"><div class="table-wrap"><table>'
        '<caption>Calculation method recorded in the result</caption><tbody>'
        f'{rows(method)}</tbody></table></div>'
        '<div class="table-wrap"><table>'
        '<caption>Reproducibility metadata recorded in the result</caption><tbody>'
        f'{rows(reproducibility)}</tbody></table></div></div>'
    )


def _audit_sections(result: Mapping[str, Any], source_json: str, mathematics: str) -> str:
    assumptions = result.get("assumptions", [])
    warnings = result.get("warnings", [])
    return (
        '<section class="panel" aria-labelledby="audit-heading">'
        '<p class="section-kicker">Assumptions & audit trail</p>'
        '<h2 id="audit-heading">What this result depends on</h2>'
        '<div class="two-column">'
        f'{_list_section("User-confirmed assumptions", assumptions, "No assumptions were recorded.")}'
        f'{_list_section("Warnings", warnings, "No warnings were recorded.")}'
        '</div>' + _metadata_tables(result) +
        '<details><summary>Mathematical details</summary>'
        f'<div class="details-body">{mathematics}</div></details>'
        '<details><summary>Raw audit data (escaped source result JSON)</summary>'
        '<div class="details-body"><pre class="formula raw-json">'
        f'{_escape(source_json)}</pre></div></details></section>'
    )


def _document(title: str, content: str) -> str:
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{_escape(title)} · Decision Architect</title>\n'
        f'<style>\n{BASE_STYLES}\n</style>\n</head>\n<body>\n'
        f'<div class="page">{content}'
        '<footer class="report-footer">Decision Architect · Transparent, reproducible decision support</footer>'
        '</div>\n</body>\n</html>\n'
    )


def _multi_recommendation(result: Mapping[str, Any]) -> str:
    recommendation = result["recommendation"]
    status = str(recommendation["status"])
    alternative_id = recommendation.get("alternative_id")
    tied_ids = recommendation.get("tied_alternative_ids", [])
    labels = {
        "recommended": "Recommended under this model",
        "close_call": "Close call",
        "mean_utility_tie": "Mean-utility tie",
        "only_feasible_alternative": "Only feasible alternative",
        "no_feasible_alternative": "No feasible alternative",
    }
    if status == "no_feasible_alternative":
        headline = "No alternative satisfies all hard constraints"
        panel_class = "recommendation infeasible"
        badge_class = "status danger"
    elif status == "mean_utility_tie":
        names = [_display_name(result, value) for value in tied_ids]
        headline = "Tied leaders: " + ", ".join(names)
        panel_class = "recommendation tie"
        badge_class = "status caution"
    elif status == "close_call":
        headline = (
            f"Current mean-utility leader: {_display_name(result, alternative_id)}"
            if alternative_id is not None else "No unique leader"
        )
        panel_class = "recommendation close"
        badge_class = "status caution"
    else:
        headline = (
            _display_name(result, alternative_id)
            if alternative_id is not None else "No unique leader"
        )
        panel_class = "recommendation"
        badge_class = "status"

    metrics = ""
    if recommendation.get("leading_monte_carlo_mean_utility") is not None:
        metrics += _metric(
            "Monte Carlo mean utility",
            _format_number(recommendation["leading_monte_carlo_mean_utility"]),
        )
    if recommendation.get("leading_win_probability") is not None:
        metrics += _metric("Win probability", _format_percent(recommendation["leading_win_probability"]))
    approximation_notes = [
        str(value)
        for value in result.get("assumptions", [])
        if "approximate" in str(value).lower() and "staged" in str(value).lower()
    ]
    approximation = "".join(
        '<p class="note"><strong>Important model approximation:</strong> '
        f'{_escape(value)}</p>'
        for value in approximation_notes
    )
    return (
        f'<section class="panel {panel_class}" aria-labelledby="recommendation-heading">'
        '<p class="section-kicker">Result</p>'
        f'<span class="{badge_class}">{_escape(labels.get(status, _humanize(status)))}</span>'
        f'<h2 class="hero-action" id="recommendation-heading">{_escape(headline)}</h2>'
        f'<p class="lede">{_escape(recommendation["conditional_statement"])}</p>'
        '<p class="note"><strong>What win probability means:</strong> the percentage of modeled '
        'Monte Carlo scenarios in which an alternative ranked first. It is not the probability '
        'that the real-life decision will succeed, and it is not objective truth.</p>'
        f'{approximation}<div class="metrics">{metrics}</div></section>'
    )


def _multi_alternatives(result: Mapping[str, Any]) -> str:
    alternatives = []
    for alternative in result["alternative_results"]:
        item = dict(alternative)
        item["display_name"] = _display_name(result, item["alternative_id"])
        alternatives.append(item)
    if not alternatives:
        return (
            '<section class="panel"><p class="section-kicker">Alternatives</p>'
            '<h2>No feasible alternatives to compare</h2>'
            '<p class="empty-state">Utility summaries are unavailable because every alternative was excluded.</p></section>'
        )
    rows = []
    for alternative in alternatives:
        distribution = alternative["utility_distribution"]
        rows.append(
            '<tr>'
            f'<th scope="row">{_escape(alternative["display_name"])}<br>'
            f'<span class="id">{_escape(alternative["alternative_id"])}</span></th>'
            f'<td class="numeric">{_format_number(alternative["monte_carlo_mean_utility"])}</td>'
            f'<td class="numeric">{_format_number(alternative["analytical_utility"])}</td>'
            f'<td class="numeric">{_format_percent(alternative["win_probability"])}</td>'
            f'<td class="numeric">{_format_number(distribution["percentile_10"])}</td>'
            f'<td class="numeric">{_format_number(distribution["percentile_50"])}</td>'
            f'<td class="numeric">{_format_number(distribution["percentile_90"])}</td>'
            f'<td class="numeric">{_format_number(distribution["standard_deviation"])}</td>'
            '</tr>'
        )
    return (
        '<section class="panel" aria-labelledby="alternatives-heading">'
        '<p class="section-kicker">Why</p><h2 id="alternatives-heading">Alternatives overview</h2>'
        '<div class="table-wrap"><table><caption>Feasible alternatives and their stored utility summaries</caption>'
        '<thead><tr><th scope="col">Alternative</th><th scope="col" class="numeric">MC mean</th>'
        '<th scope="col" class="numeric">Analytical</th><th scope="col" class="numeric">Win probability</th>'
        '<th scope="col" class="numeric">P10</th><th scope="col" class="numeric">P50</th>'
        '<th scope="col" class="numeric">P90</th><th scope="col" class="numeric">Std. dev.</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        '<h3>Uncertainty at the current weights</h3>'
        '<p>Ranges show the stored Monte Carlo distribution. They describe estimate uncertainty at the current preferences.</p>'
        f'{uncertainty_chart(alternatives)}'
        '<p class="note">Chart alternative: the complete numerical uncertainty table appears immediately above.</p>'
        '</section>'
    )


def _multi_contributions(result: Mapping[str, Any]) -> str:
    sensitivity = result["sensitivity"]
    weight_by_criterion = {
        item["criterion_id"]: item["baseline_weight"] for item in sensitivity.get("criteria", [])
    }
    charts = []
    rows = []
    for chart_index, alternative in enumerate(result["alternative_results"]):
        alternative_name = _display_name(result, alternative["alternative_id"])
        chart_values = []
        for criterion_id, mean_utility in alternative["criterion_mean_utilities"].items():
            contribution = alternative["weighted_criterion_contributions"][criterion_id]
            criterion_name = _criterion_name(result, criterion_id)
            weight = weight_by_criterion.get(criterion_id)
            if weight is not None and _finite(weight) <= 0:
                continue
            rows.append(
                '<tr>'
                f'<th scope="row">{_escape(alternative_name)}</th>'
                f'<td>{_escape(criterion_name)}<br><span class="id">{_escape(criterion_id)}</span></td>'
                f'<td class="numeric">{_format_weight(weight)}</td>'
                f'<td class="numeric">{_format_number(mean_utility)}</td>'
                f'<td class="numeric">{_format_number(contribution)}</td>'
                '</tr>'
            )
            chart_values.append((criterion_name, contribution))
        charts.append(contribution_chart(alternative_name, chart_values, chart_index))
    return (
        '<section class="panel" aria-labelledby="contributions-heading">'
        '<p class="section-kicker">Preference structure</p>'
        '<h2 id="contributions-heading">Criterion contributions</h2>'
        '<p>Each contribution is the stored criterion mean utility multiplied by its recorded weight. '
        'These modeled components are not causal effects.</p>'
        f'{"".join(charts)}'
        '<div class="table-wrap"><table><caption>Numerical alternative to the contribution charts</caption>'
        '<thead><tr><th scope="col">Alternative</th><th scope="col">Criterion</th>'
        '<th scope="col" class="numeric">Weight</th><th scope="col" class="numeric">Criterion mean utility</th>'
        '<th scope="col" class="numeric">Weighted contribution</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _multi_constraints(result: Mapping[str, Any]) -> str:
    excluded = result["excluded_alternatives"]
    zero_weight_ids = [
        item["criterion_id"]
        for item in result.get("sensitivity", {}).get("criteria", [])
        if _finite(item.get("baseline_weight", 0)) <= 0
    ]
    indicators = ""
    if zero_weight_ids:
        indicator_items = "".join(
            f'<li>{_escape(_criterion_name(result, criterion_id))} '
            f'<span class="id">{_escape(criterion_id)}</span></li>'
            for criterion_id in zero_weight_ids
        )
        indicators = (
            '<h3>Zero-weight model indicators</h3>'
            '<p>These fields contribute no weighted preference utility. They are grouped in this '
            'eligibility section so they are not mistaken for ordinary weighted preferences. A zero '
            'weight alone does not classify a field as a hard constraint; actual failures appear below.</p>'
            f'<ul class="clean-list">{indicator_items}</ul>'
        )
    if not excluded:
        content = '<p class="empty-state">No alternative was excluded by a hard constraint.</p>'
    else:
        rows = []
        for alternative in excluded:
            for failure in alternative["failed_constraints"]:
                boundary = failure["relevant_estimate_boundary"]
                boundary_values = ", ".join(_format_number(value) for value in boundary["values"])
                rows.append(
                    '<tr>'
                    f'<th scope="row">{_escape(_display_name(result, alternative["alternative_id"]))}<br>'
                    f'<span class="id">{_escape(alternative["alternative_id"])}</span></th>'
                    f'<td>{_escape(failure["constraint_id"])}</td>'
                    f'<td>{_escape(_criterion_name(result, failure["criterion_id"]))}</td>'
                    f'<td class="numeric">{_escape(failure["operator"])}</td>'
                    f'<td class="numeric">{_format_number(failure["threshold"])}</td>'
                    f'<td>{_escape(boundary["name"])}: {_escape(boundary_values)}</td>'
                    f'<td>{_escape(failure["human_explanation"])}</td>'
                    '</tr>'
                )
        content = (
            '<div class="table-wrap"><table><caption>Alternatives excluded before utility ranking</caption>'
            '<thead><tr><th scope="col">Alternative</th><th scope="col">Failed constraint</th>'
            '<th scope="col">Criterion</th><th scope="col">Operator</th><th scope="col">Threshold</th>'
            '<th scope="col">Relevant estimate boundary</th><th scope="col">Reason</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )
    return (
        '<section class="panel" aria-labelledby="constraints-heading">'
        '<p class="section-kicker">Eligibility</p><h2 id="constraints-heading">Hard constraints</h2>'
        f'{indicators}{content}</section>'
    )


def _interval_text(interval: Mapping[str, Any]) -> str:
    lower = "[" if interval["minimum_inclusive"] else "("
    upper = "]" if interval["maximum_inclusive"] else ")"
    return (
        f'{lower}{_format_weight(interval["minimum_weight"])}, '
        f'{_format_weight(interval["maximum_weight"])}{upper}'
    )


def _multi_sensitivity(result: Mapping[str, Any]) -> str:
    sensitivity = result["sensitivity"]
    criteria = sensitivity.get("criteria", [])
    switches = []
    rows = []
    for criterion in criteria:
        if _finite(criterion.get("baseline_weight", 0)) <= 0:
            continue
        for key in ("lower_switch", "upper_switch"):
            switch = criterion.get(key)
            if switch and switch.get("change_type") == "winner_switch":
                switches.append(
                    (
                        abs(_finite(switch["threshold_weight"]) - _finite(criterion["baseline_weight"])),
                        criterion,
                        switch,
                    )
                )
        interval = criterion.get("robust_interval")
        interval_display = _interval_text(interval) if interval else "Not applicable"
        plain = criterion.get("explanation", "")
        if interval and sensitivity.get("baseline_winner_id"):
            plain = (
                f'The baseline recommendation remains the unique mean-utility leader while the '
                f'{_criterion_name(result, criterion["criterion_id"])} weight stays in '
                f'{interval_display}.'
            )
        rows.append(
            '<tr>'
            f'<th scope="row">{_escape(_criterion_name(result, criterion["criterion_id"]))}<br>'
            f'<span class="id">{_escape(criterion["criterion_id"])}</span></th>'
            f'<td class="numeric">{_format_weight(criterion["baseline_weight"])}</td>'
            f'<td><span class="interval">{_escape(interval_display)}</span></td>'
            f'<td>{_escape(plain)}</td></tr>'
        )

    if sensitivity["status"] != "analyzed":
        highlight = (
            '<div class="note"><strong>Sensitivity is not applicable.</strong> '
            f'{_escape(sensitivity["explanation"])}</div>'
        )
    elif switches:
        distance, criterion, switch = min(switches, key=lambda item: item[0])
        baseline = _display_name(result, sensitivity["baseline_winner_id"])
        new_winner = _display_name(result, switch["new_winner_id"])
        highlight = (
            '<div class="recommendation close">'
            '<span class="status caution">Closest real winner switch</span>'
            f'<h3>{_escape(_criterion_name(result, criterion["criterion_id"]))} weight: '
            f'{_format_weight(criterion["baseline_weight"])} → {_format_weight(switch["threshold_weight"])}</h3>'
            f'<p>At the threshold, {_escape(baseline)} and {_escape(new_winner)} tie on stored '
            f'fixed-sample mean utility. Beyond it in the reported direction, {_escape(new_winner)} leads.</p>'
            f'<div class="metrics">{_metric("Absolute weight change", _format_weight(distance))}'
            f'{_metric("New winner beyond threshold", new_winner)}</div></div>'
        )
    else:
        highlight = (
            '<div class="note"><strong>No real winner switch occurs inside the permitted ranges.</strong> '
            f'{_escape(sensitivity["explanation"])}</div>'
        )

    return (
        '<section class="panel" aria-labelledby="sensitivity-heading">'
        '<p class="section-kicker">Preference sensitivity</p><h2 id="sensitivity-heading">When could the leader change?</h2>'
        '<div class="distinction"><div><strong>Uncertainty at current weights</strong><p>Monte Carlo ranges '
        'describe uncertainty in the estimates while preferences stay fixed.</p></div>'
        '<div><strong>Sensitivity to changing preferences</strong><p>This section varies one criterion weight '
        'at a time while reusing the same simulation sample.</p></div></div>'
        f'{highlight}'
        '<p><strong>Baseline winner:</strong> '
        f'{_escape(_display_name(result, sensitivity["baseline_winner_id"])) if sensitivity.get("baseline_winner_id") else "Not applicable"}. '
        f'<strong>Method:</strong> {_escape(sensitivity["method"])}.</p>'
        '<div class="table-wrap"><table><caption>Robust interval for every criterion</caption>'
        '<thead><tr><th scope="col">Criterion</th><th scope="col" class="numeric">Baseline weight</th>'
        '<th scope="col">Robust interval</th><th scope="col">Interpretation</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></section>'
    )


MULTI_MATHEMATICS = """
<p>The report displays stored engine results; it does not run these calculations.</p>
<pre class="formula">Anchor normalization:
utility = clamp((value − worst anchor) / (best anchor − worst anchor), 0, 1)

Weighted utility:
total utility = Σ (criterion weight × normalized criterion utility)

Triangular raw mean:
mean = (minimum + most likely + maximum) / 3</pre>
<p>Monte Carlo ranking draws each confirmed triangular estimate with the recorded seed, calculates weighted utility, and ranks feasible alternatives by mean utility. Simulation ties split win credit.</p>
<pre class="formula">One-at-a-time fixed-sample sensitivity:
w_target(x) = x
w_other(x) = original w_other × (1 − x) / (1 − original w_target)</pre>
<p>The engine reuses stored criterion means, solves linear winner crossings analytically, and verifies both sides. It does not resample or change hard-constraint eligibility.</p>
"""


def render_multi_criteria_report(result: Mapping[str, Any], source_json: str) -> str:
    """Render one validated multi-criteria result without calculation."""

    content = (
        _header(result, "Multi-criteria decision model")
        + '<main>'
        + _multi_recommendation(result)
        + _multi_alternatives(result)
        + _multi_contributions(result)
        + _multi_constraints(result)
        + _multi_sensitivity(result)
        + _audit_sections(result, source_json, MULTI_MATHEMATICS)
        + '</main>'
    )
    return _document(_decision_title(result), content)


def _sequential_recommendation(result: Mapping[str, Any]) -> str:
    action = str(result["recommended_action"]).upper()
    status_label = {
        "explore_preferred": "Explore preferred under this model",
        "exploit_preferred": "Exploit preferred under this model",
        "indifferent": "Indifferent under this model",
    }.get(str(result["recommendation_status"]), _humanize(str(result["recommendation_status"])))
    unavailable = result.get("explore_value") is None
    badge_class = "status caution" if action == "INDIFFERENT" else "status"
    note = (
        '<p class="note">Exploration is unavailable because no unseen option remains.</p>'
        if unavailable else ""
    )
    metrics = (
        _metric("Expected optimal total utility", _format_number(result["expected_total_utility"]))
        + _metric("Exploit value", _format_number(result["exploit_value"]))
        + _metric("Explore value", _format_number(result.get("explore_value")))
        + _metric("Explore − exploit", _format_number(result.get("action_advantage")))
    )
    return (
        '<section class="panel recommendation" aria-labelledby="recommendation-heading">'
        '<p class="section-kicker">Result</p>'
        f'<span class="{badge_class}">{_escape(status_label)}</span>'
        f'<h2 class="hero-action" id="recommendation-heading">{_escape(action)}</h2>'
        f'<p class="lede">{_escape(result["conditional_statement"])}</p>{note}'
        f'<div class="metrics">{metrics}</div></section>'
    )


def _sequential_state(result: Mapping[str, Any]) -> str:
    state = result["current_state"]
    distribution = result["new_option_distribution"]
    scale = result["utility_scale"]
    metrics = (
        _metric("Remaining opportunities", str(state["remaining_opportunities"]))
        + _metric("Unseen options", str(state["unseen_options_remaining"]))
        + _metric("Best-known value", _format_number(state["best_known_value"]))
        + _metric("Utility scale", f'{_format_number(scale["minimum"])} to {_format_number(scale["maximum"])} {scale["unit"]}')
    )
    return (
        '<section class="panel" aria-labelledby="state-heading">'
        '<p class="section-kicker">Current state</p><h2 id="state-heading">What the policy starts from</h2>'
        f'<div class="metrics">{metrics}</div>'
        '<h3>Uncertain quality of a new option</h3>'
        '<div class="metrics">'
        f'{_metric("Minimum", _format_number(distribution["minimum"]))}'
        f'{_metric("Most likely", _format_number(distribution["most_likely"]))}'
        f'{_metric("Maximum", _format_number(distribution["maximum"]))}</div>'
        f'<p>{_escape(scale["description"])}</p></section>'
    )


def _sequential_policy(result: Mapping[str, Any]) -> str:
    state = result["current_state"]
    current_horizon = int(state["remaining_opportunities"])
    rows = []
    for policy in result["policy_by_remaining_opportunities"]:
        horizon = int(policy["remaining_opportunities"])
        row_class = ' class="current-row"' if horizon == current_horizon else ""
        current_text = " (current horizon)" if horizon == current_horizon else ""
        rows.append(
            f'<tr{row_class}><th scope="row">{horizon}{_escape(current_text)}</th>'
            f'<td class="numeric">{_format_number(policy["exploit_value"])}</td>'
            f'<td class="numeric">{_format_number(policy.get("explore_value"))}</td>'
            f'<td class="numeric">{_format_number(policy.get("action_advantage"))}</td>'
            f'<td><strong>{_escape(str(policy["recommended_action"]).upper())}</strong></td></tr>'
        )
    switches = result["action_switch_points"]
    if switches:
        switch_items = "".join(
            '<li>At <strong>' + _escape(item["remaining_opportunities"]) +
            '</strong> remaining opportunities, the stored policy changes from <strong>' +
            _escape(str(item["previous_action"]).upper()) + '</strong> to <strong>' +
            _escape(str(item["recommended_action"]).upper()) + '</strong>.</li>'
            for item in switches
        )
        switch_content = f'<ul class="clean-list">{switch_items}</ul>'
    else:
        switch_content = '<p class="empty-state">The stored policy has no action switch within this horizon.</p>'
    return (
        '<section class="panel" aria-labelledby="policy-heading">'
        '<p class="section-kicker">Time horizon</p><h2 id="policy-heading">How the recommendation changes with remaining opportunities</h2>'
        '<p>Action advantage equals stored explore value minus stored exploit value. Positive favors explore; '
        'negative favors exploit; values inside the recorded tolerance are indifferent.</p>'
        f'{horizon_chart(result["policy_by_remaining_opportunities"], current_horizon)}'
        '<p class="note">Chart alternative: every plotted horizon appears in the numerical policy table below.</p>'
        '<div class="table-wrap"><table><caption>Complete stored horizon policy</caption>'
        '<thead><tr><th scope="col">Remaining opportunities</th><th scope="col" class="numeric">Exploit value</th>'
        '<th scope="col" class="numeric">Explore value</th><th scope="col" class="numeric">Action advantage</th>'
        '<th scope="col">Recommended action</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        '<h3>Action-switch points</h3>' + switch_content + '</section>'
    )


SEQUENTIAL_MATHEMATICS = """
<p>The report displays stored dynamic-programming output; it does not rerun the model.</p>
<pre class="formula">V(0, u, b) = 0

Exploit:
b + V(t − 1, u, b)

Explore:
E[X + V(t − 1, u − 1, max(b, X))]

Optimal value:
max(exploit, explore)</pre>
<p>The expectation uses deterministic midpoint quantile quadrature with the recorded point count. The engine memoizes best-known values at the recorded decimal precision and compares actions using the recorded tolerance.</p>
<p>Assumptions include no discounting, no learning of the distribution, and independent new-option draws from one triangular distribution. Exploration receives the new draw immediately. This is a Feynman-inspired finite-horizon model, not a claim of perfect historical reproduction.</p>
"""


def render_sequential_report(result: Mapping[str, Any], source_json: str) -> str:
    """Render one validated sequential-exploration result without calculation."""

    content = (
        _header(result, "Feynman-inspired exploration model")
        + '<main>'
        + _sequential_recommendation(result)
        + _sequential_state(result)
        + _sequential_policy(result)
        + _audit_sections(result, source_json, SEQUENTIAL_MATHEMATICS)
        + '</main>'
    )
    return _document(_decision_title(result), content)


def render_demo_index(entries: Sequence[Mapping[str, str]]) -> str:
    """Render a standalone demonstration landing page from validated summaries."""

    cards = "".join(
        '<a class="demo-card" href="' + _escape(entry["href"]) + '">'
        '<p class="eyebrow">' + _escape(entry["model_label"]) + '</p>'
        '<strong>' + _escape(entry["title"]) + '</strong>'
        '<span>' + _escape(entry["summary"]) + '</span></a>'
        for entry in entries
    )
    content = (
        '<header class="product-header"><div><p class="eyebrow">OpenAI Build Week project</p>'
        '<h1>Decision Architect</h1><p>Turn an informal personal decision into a transparent, '
        'user-confirmed mathematical model with reproducible calculations.</p></div></header>'
        f'<p class="conditionality">{_escape(CONDITIONALITY_STATEMENT)}</p>'
        '<main><section class="panel"><p class="section-kicker">Local demonstrations</p>'
        '<h2>Choose a report</h2><p class="lede">Multi-criteria analysis compares one-time choices using '
        'weighted utility and uncertainty. Sequential exploration compares trying something new with using '
        'the best known option over a finite horizon.</p>'
        f'<div class="demo-grid">{cards}</div></section></main>'
    )
    return _document("Demonstrations", content)
