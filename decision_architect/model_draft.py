"""Calculation-free checks and summaries for interview model drafts."""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .validation import ValidationIssue, validate_model


FieldStatus = Literal["missing", "provisional", "user_confirmed"]
SourceType = Literal["user_statement", "user_estimate", "system_proposal", "default"]


@dataclass(frozen=True)
class DraftField:
    value: Any
    status: FieldStatus
    source_type: SourceType
    confidence: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "value": self.value,
            "status": self.status,
            "source_type": self.source_type,
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.note is not None:
            result["note"] = self.note
        return result


def iter_material_fields(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    """Yield deterministic leaf paths, excluding the derived confirmation flag."""

    if isinstance(value, Mapping):
        if not value:
            yield path, {}
            return
        for key in sorted(value):
            if path == "$" and key == "confirmed_by_user":
                continue
            yield from iter_material_fields(value[key], f"{path}.{key}")
        return
    if isinstance(value, list):
        if not value:
            yield path, []
            return
        for index, item in enumerate(value):
            yield from iter_material_fields(item, f"{path}[{index}]")
        return
    yield path, value


def create_field_records(
    model: Mapping[str, Any],
    *,
    status: FieldStatus = "provisional",
    source_type: SourceType = "system_proposal",
    source_types: Mapping[str, SourceType] | None = None,
) -> dict[str, dict[str, Any]]:
    overrides = dict(source_types or {})
    material = dict(iter_material_fields(model))
    unknown = sorted(set(overrides) - set(material))
    if unknown:
        raise ValueError("Source map contains unknown model field paths: " + ", ".join(unknown))
    allowed = {"user_statement", "user_estimate", "system_proposal", "default"}
    invalid = sorted(path for path, value in overrides.items() if value not in allowed)
    if invalid:
        raise ValueError("Source map contains invalid source types at: " + ", ".join(invalid))
    return {
        path: DraftField(value, status, overrides.get(path, source_type)).to_dict()
        for path, value in material.items()
    }


def draft_validation_issues(model: Any) -> list[ValidationIssue]:
    """Validate a draft as if the later explicit confirmation flag were true."""

    if not isinstance(model, Mapping):
        return [ValidationIssue("$", "expected_object", "The proposed model must be a JSON object.")]
    candidate = copy.deepcopy(dict(model))
    candidate["confirmed_by_user"] = True
    return validate_model(candidate)


def field_tracking_issues(
    model: Mapping[str, Any],
    records: Any,
) -> list[str]:
    """Check that every material value is tracked and no record is missing."""

    if not isinstance(records, Mapping):
        return ["Session field records must be a JSON object."]
    issues: list[str] = []
    expected = dict(iter_material_fields(model))
    for path, value in expected.items():
        record = records.get(path)
        if not isinstance(record, Mapping):
            issues.append(f"{path} has no session field record.")
            continue
        if record.get("status") not in {"provisional", "user_confirmed"}:
            issues.append(f"{path} is still missing or has an invalid status.")
        if record.get("source_type") not in {
            "user_statement", "user_estimate", "system_proposal", "default"
        }:
            issues.append(f"{path} has an invalid source type.")
        if record.get("value") != value:
            issues.append(f"{path} changed after its session record was created; review it again.")
    extra = sorted(set(records) - set(expected))
    for path in extra:
        issues.append(f"{path} is tracked but is not present in the proposed model.")
    return issues


def model_review_markdown(model: Mapping[str, Any]) -> str:
    """Render every material model value in a readable deterministic review."""

    lines = [
        f'# Model review: {model.get("title", "Untitled decision")}',
        "",
        f'- Model version: `{model.get("model_version", "missing")}`',
        f'- Model type: `{model.get("model_type", "missing")}`',
        f'- Decision ID: `{model.get("decision_id", "missing")}`',
        f'- Decision description: {model.get("description", "missing")}',
        f'- Time horizon: {model.get("time_horizon", "missing")}',
        f'- Notes: {model.get("notes", "None recorded.")}',
        "",
    ]
    if model.get("model_type") == "multi_criteria":
        lines.extend(["## Alternatives", ""])
        for item in model.get("alternatives", []):
            lines.append(
                f'- {item.get("name", "Unnamed")} (`{item.get("id", "missing")}`): '
                f'{item.get("description", "description missing")}'
            )
        lines.extend(["", "## Criteria and weights", ""])
        for item in model.get("criteria", []):
            lines.append(
                f'- {item.get("name", "Unnamed")}: {item.get("weight", "missing")} '
                f'({item.get("unit", "unit missing")}); {item.get("preference_direction", "direction missing")}; '
                f'{item.get("description", "description missing")}; anchors '
                f'{item.get("worst_anchor", "missing")} to {item.get("best_anchor", "missing")}'
            )
        lines.extend(["", "## Hard constraints", ""])
        constraints = model.get("hard_constraints", [])
        if constraints:
            for item in constraints:
                lines.append(
                    f'- {item.get("name", "Unnamed")} (`{item.get("id", "missing")}`): '
                    f'{item.get("description", "description missing")} Rule: '
                    f'{item.get("criterion_id", "missing")} {item.get("operator", "?")} '
                    f'{item.get("threshold", "missing")}'
                )
                constraint_id = item.get("id")
                for alternative in model.get("alternatives", []):
                    result = alternative.get("constraint_results", {}).get(constraint_id, "missing")
                    display = "passes" if result is True else "fails" if result is False else "missing"
                    lines.append(f'  - {alternative.get("name", "Unnamed")}: {display}')
        else:
            lines.append("- None recorded.")
        criterion_by_id = {
            item.get("id"): item for item in model.get("criteria", [])
        }
        lines.extend(["", "## Three-point estimates", ""])
        for alternative in model.get("alternatives", []):
            lines.append(f'### {alternative.get("name", "Unnamed") }')
            lines.append("")
            for criterion_id, estimate in alternative.get("criterion_estimates", {}).items():
                criterion = criterion_by_id.get(criterion_id, {})
                lines.append(
                    f'- {criterion.get("name", criterion_id)} ({criterion.get("unit", "unit missing")}): '
                    f'{estimate.get("minimum", "missing")} / '
                    f'{estimate.get("most_likely", "missing")} / '
                    f'{estimate.get("maximum", "missing")} '
                    "(minimum / most likely / maximum)"
                )
        settings = model.get("analysis_settings", {})
        lines.extend(
            [
                "",
                "## Reproducibility settings",
                "",
                f'- Monte Carlo samples: {settings.get("monte_carlo_samples", "missing")}',
                f'- Random seed: {settings.get("random_seed", "missing")}',
                f'- Clamp utility to anchors: {settings.get("clamp_utility", "missing")}',
            ]
        )
    elif model.get("model_type") == "sequential_exploration":
        state = model.get("state", {})
        scale = model.get("utility_scale", {})
        distribution = model.get("new_option_distribution", {})
        settings = model.get("analysis_settings", {"quadrature_points": 101})
        lines.extend(
            [
                "## Proposed state",
                "",
                f'- Remaining opportunities (including now): {state.get("remaining_opportunities", "missing")}',
                f'- Unseen options remaining: {state.get("unseen_options_remaining", "missing")}',
                f'- Best known value: {state.get("best_known_value", "missing")}',
                f'- Utility scale: {scale.get("minimum", "missing")} to {scale.get("maximum", "missing")} '
                f'{scale.get("unit", "")}',
                f'- Utility scale meaning: {scale.get("description", "missing")}',
                f'- New-option estimate: {distribution.get("minimum", "missing")} / '
                f'{distribution.get("most_likely", "missing")} / {distribution.get("maximum", "missing")}',
                f'- Quadrature points: {settings.get("quadrature_points", 101)}',
            ]
        )
    lines.extend(["", "## Assumptions", ""])
    assumptions = model.get("assumptions", [])
    if assumptions:
        lines.extend(f"- {value}" for value in assumptions)
    else:
        lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "Please reply CONFIRM to run this exact model, or tell me what should be changed.",
            "",
        ]
    )
    return "\n".join(lines)
