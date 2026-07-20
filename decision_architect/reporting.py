"""Validated, deterministic, calculation-free HTML report generation."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .report_templates import (
    render_demo_index,
    render_multi_criteria_report,
    render_sequential_report,
)
from .result_serialization import validate_result
from .text_io import atomic_write_utf8_lf, canonical_lf_text


class ReportError(ValueError):
    """Raised when a result cannot be safely rendered as a report."""


DEMO_FILES = (
    (
        "job-choice-result.json",
        "job-choice-report.html",
    ),
    (
        "feynman-restaurant-result.json",
        "feynman-restaurant-report.html",
    ),
    (
        "feynman-restaurant-short-horizon-result.json",
        "feynman-restaurant-short-horizon-report.html",
    ),
    (
        "university-transfer-result.json",
        "university-transfer-report.html",
    ),
)


def _parse_and_validate(source_text: str, source_label: str) -> dict[str, Any]:
    try:
        value = json.loads(source_text)
    except json.JSONDecodeError as error:
        raise ReportError(f"{source_label} is not valid JSON: {error}") from error
    try:
        errors = validate_result(value)
    except Exception as error:
        raise ReportError(
            f"{source_label} could not be safely validated as decision-result-v1: {error}"
        ) from error
    if errors:
        detail = "; ".join(errors)
        raise ReportError(f"{source_label} is not a valid decision-result-v1 document: {detail}")
    if not isinstance(value, dict):  # validate_result already enforces this; keeps typing explicit.
        raise ReportError(f"{source_label} must contain a JSON object.")
    return value


def load_validated_result(path: str | Path) -> tuple[dict[str, Any], str]:
    """Read a UTF-8 result and return its object plus canonical audit text."""

    source = Path(path)
    source_text = canonical_lf_text(source.read_bytes().decode("utf-8"))
    return _parse_and_validate(source_text, str(source)), source_text


def render_report(result: Mapping[str, Any], source_json: str | None = None) -> str:
    """Render a validated result mapping without calling either calculation engine."""

    try:
        errors = validate_result(result)
    except Exception as error:
        raise ReportError(
            f"Result could not be safely validated as decision-result-v1: {error}"
        ) from error
    if errors:
        raise ReportError("Result is not a valid decision-result-v1 document: " + "; ".join(errors))
    model_type = result.get("model_type")
    if source_json is None:
        source_json = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if model_type == "multi_criteria":
        return render_multi_criteria_report(result, source_json)
    if model_type == "sequential_exploration":
        return render_sequential_report(result, source_json)
    raise ReportError(f"Unsupported result model_type: {model_type!r}")


def generate_report(result_path: str | Path, output_path: str | Path) -> tuple[Path, dict[str, Any]]:
    """Validate an existing result file, render it, and atomically save one HTML file."""

    source = Path(result_path)
    output = Path(output_path)
    source_identity = os.path.normcase(os.path.abspath(source))
    output_identity = os.path.normcase(os.path.abspath(output))
    if source_identity == output_identity:
        raise ReportError("The report output path must differ from the source result JSON path.")
    result, source_text = load_validated_result(source)
    html_text = render_report(result, source_text)
    output = atomic_write_utf8_lf(output, html_text)
    return output, result


def concise_result_summary(result: Mapping[str, Any]) -> str:
    """Return a short CLI summary using only values stored in the result."""

    if result["model_type"] == "multi_criteria":
        recommendation = result["recommendation"]
        status = str(recommendation["status"])
        alternative = recommendation.get("alternative_id")
        return f"{status}" + (f" · {alternative}" if alternative is not None else "")
    return (
        f'{result["recommendation_status"]} · '
        f'{str(result["recommended_action"]).upper()}'
    )


def _demo_entry(result: Mapping[str, Any], report_filename: str) -> dict[str, str]:
    if result["model_type"] == "multi_criteria":
        decision_id = str(result["decision_id"])
        title = decision_id.replace("-example", "").replace("_example", "")
        title = title.replace("-", " ").replace("_", " ").title()
        recommendation = result["recommendation"]
        status = str(recommendation["status"]).replace("_", " ").title()
        leader = recommendation.get("alternative_id")
        summary = f"{status}." + (
            f" Stored leader: {str(leader).replace('-', ' ').title()}." if leader else ""
        )
        model_label = "Multi-criteria model"
    else:
        horizon = int(result["current_state"]["remaining_opportunities"])
        title = f"Feynman-inspired Dishes — {horizon} Visits"
        action = str(result["recommended_action"]).upper()
        summary = f"Stored result: {action} at {horizon} remaining opportunities."
        model_label = "Sequential exploration model"
    return {
        "title": title,
        "href": report_filename,
        "summary": summary,
        "model_label": model_label,
    }


def generate_demo_index(
    report_directory: str | Path,
    results_directory: str | Path = "outputs",
) -> Path:
    """Build the fixed release demonstration index from validated result summaries."""

    report_dir = Path(report_directory)
    results_dir = Path(results_directory)
    entries = []
    for result_filename, report_filename in DEMO_FILES:
        result, _ = load_validated_result(results_dir / result_filename)
        entries.append(_demo_entry(result, report_filename))
    return atomic_write_utf8_lf(report_dir / "index.html", render_demo_index(entries))
