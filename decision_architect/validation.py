"""Standard-library validation for Decision Architect input model v1."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import DecisionModel, model_from_validated_dict


MODEL_VERSION = "1.0"
SUPPORTED_MODEL_TYPES = {"multi_criteria", "sequential_exploration"}
WEIGHT_SUM_TOLERANCE = 1e-9
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

COMMON_REQUIRED = {
    "model_version",
    "model_type",
    "decision_id",
    "title",
    "description",
    "time_horizon",
    "confirmed_by_user",
    "assumptions",
}
COMMON_ALLOWED = COMMON_REQUIRED | {"notes"}
MULTI_REQUIRED = {"criteria", "hard_constraints", "alternatives", "analysis_settings"}
SEQUENTIAL_REQUIRED = {"utility_scale", "state", "new_option_distribution"}
SEQUENTIAL_ALLOWED = SEQUENTIAL_REQUIRED | {"analysis_settings"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message} ({self.code})"


class DecisionModelValidationError(ValueError):
    """Raised when a model cannot be accepted without changing user data."""

    def __init__(self, issues: Sequence[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("\n".join(str(issue) for issue in self.issues))


class _Validator:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def add(self, path: str, code: str, message: str) -> None:
        self.issues.append(ValidationIssue(path, code, message))

    def object_shape(
        self,
        value: Any,
        path: str,
        required: set[str],
        allowed: set[str],
    ) -> bool:
        if not isinstance(value, Mapping):
            self.add(path, "expected_object", "Must be a JSON object.")
            return False
        for key in sorted(required - set(value)):
            self.add(f"{path}.{key}", "required", "This field is required.")
        for key in sorted(set(value) - allowed):
            self.add(f"{path}.{key}", "unknown_field", "This field is not part of model version 1.0.")
        return True

    def text(self, value: Any, path: str, *, allow_empty: bool = False) -> bool:
        if not isinstance(value, str):
            self.add(path, "expected_string", "Must be text.")
            return False
        if not allow_empty and not value.strip():
            self.add(path, "empty_string", "Must not be empty.")
            return False
        return True

    def identifier(self, value: Any, path: str) -> bool:
        if not self.text(value, path):
            return False
        if not IDENTIFIER_PATTERN.fullmatch(value):
            self.add(
                path,
                "invalid_id",
                "Use 1-64 lowercase letters, digits, underscores, or hyphens, starting with a letter.",
            )
            return False
        return True

    def number(self, value: Any, path: str) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.add(path, "expected_number", "Must be a finite number.")
            return False
        if not math.isfinite(value):
            self.add(path, "non_finite_number", "Must be finite; NaN and infinity are not allowed.")
            return False
        return True

    def integer(self, value: Any, path: str) -> bool:
        if isinstance(value, bool) or not isinstance(value, int):
            self.add(path, "expected_integer", "Must be an integer.")
            return False
        return True

    def boolean(self, value: Any, path: str) -> bool:
        if not isinstance(value, bool):
            self.add(path, "expected_boolean", "Must be true or false.")
            return False
        return True


def _duplicates(values: Sequence[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _validate_string_list(validator: _Validator, value: Any, path: str) -> None:
    if not isinstance(value, list):
        validator.add(path, "expected_array", "Must be an array of text values.")
        return
    valid_values: list[str] = []
    for index, item in enumerate(value):
        if validator.text(item, f"{path}[{index}]"):
            valid_values.append(item)
    for duplicate in sorted(_duplicates(valid_values)):
        validator.add(path, "duplicate_value", f"Contains duplicate value {duplicate!r}.")


def _validate_triangle(
    validator: _Validator,
    value: Any,
    path: str,
) -> tuple[float, float, float] | None:
    field_order = ("minimum", "most_likely", "maximum")
    fields = set(field_order)
    if not validator.object_shape(value, path, fields, fields):
        return None
    if not fields.issubset(value):
        return None
    number_checks = [
        validator.number(value[field], f"{path}.{field}")
        for field in field_order
    ]
    if not all(number_checks):
        return None
    minimum = float(value["minimum"])
    most_likely = float(value["most_likely"])
    maximum = float(value["maximum"])
    if not minimum <= most_likely <= maximum:
        validator.add(
            path,
            "invalid_triangular_distribution",
            "Require minimum <= most_likely <= maximum.",
        )
        return None
    return minimum, most_likely, maximum


def _validate_common(validator: _Validator, model: Mapping[str, Any]) -> None:
    if model.get("model_version") != MODEL_VERSION:
        validator.add("$.model_version", "unsupported_model_version", "Must be exactly '1.0'.")
    validator.identifier(model.get("decision_id"), "$.decision_id")
    for field in ("title", "description", "time_horizon"):
        validator.text(model.get(field), f"$.{field}")
    if model.get("confirmed_by_user") is not True:
        validator.add(
            "$.confirmed_by_user",
            "confirmation_required",
            "Must be true; calculations require explicit user confirmation.",
        )
    _validate_string_list(validator, model.get("assumptions"), "$.assumptions")
    if "notes" in model:
        validator.text(model["notes"], "$.notes", allow_empty=True)


def _validate_criteria(validator: _Validator, value: Any) -> list[str]:
    path = "$.criteria"
    if not isinstance(value, list):
        validator.add(path, "expected_array", "Must be an array with at least two criteria.")
        return []
    if len(value) < 2:
        validator.add(path, "too_few_criteria", "At least two criteria are required.")

    criterion_ids: list[str] = []
    weights: list[float] = []
    required = {
        "id",
        "name",
        "description",
        "weight",
        "preference_direction",
        "worst_anchor",
        "best_anchor",
        "unit",
    }
    for index, criterion in enumerate(value):
        item_path = f"{path}[{index}]"
        if not validator.object_shape(criterion, item_path, required, required):
            continue
        if validator.identifier(criterion.get("id"), f"{item_path}.id"):
            criterion_ids.append(criterion["id"])
        for field in ("name", "description", "unit"):
            validator.text(criterion.get(field), f"{item_path}.{field}")

        weight = criterion.get("weight")
        if validator.number(weight, f"{item_path}.weight"):
            if weight < 0:
                validator.add(f"{item_path}.weight", "negative_weight", "Weight must be non-negative.")
            elif weight > 1:
                validator.add(f"{item_path}.weight", "weight_above_one", "Weight must not exceed 1.")
            else:
                weights.append(float(weight))

        direction = criterion.get("preference_direction")
        if direction not in {"maximize", "minimize"}:
            validator.add(
                f"{item_path}.preference_direction",
                "invalid_preference_direction",
                "Must be 'maximize' or 'minimize'.",
            )

        worst = criterion.get("worst_anchor")
        best = criterion.get("best_anchor")
        anchors_valid = validator.number(worst, f"{item_path}.worst_anchor")
        anchors_valid = validator.number(best, f"{item_path}.best_anchor") and anchors_valid
        if anchors_valid:
            if worst == best:
                validator.add(
                    item_path,
                    "invalid_utility_anchors",
                    "Worst and best anchors must be different.",
                )
            elif direction == "maximize" and best < worst:
                validator.add(
                    item_path,
                    "invalid_utility_anchors",
                    "For a maximize criterion, best_anchor must be greater than worst_anchor.",
                )
            elif direction == "minimize" and best > worst:
                validator.add(
                    item_path,
                    "invalid_utility_anchors",
                    "For a minimize criterion, best_anchor must be less than worst_anchor.",
                )

    for duplicate in sorted(_duplicates(criterion_ids)):
        validator.add(path, "duplicate_id", f"Criterion ID {duplicate!r} is duplicated.")
    if len(weights) == len(value):
        total = math.fsum(weights)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=WEIGHT_SUM_TOLERANCE):
            validator.add(
                path,
                "weights_not_normalized",
                f"Criterion weights must sum to 1; received {total:.12g}.",
            )
        if not any(weight > 0 for weight in weights):
            validator.add(path, "all_weights_zero", "At least one criterion weight must be positive.")
    return criterion_ids


def _validate_constraints(
    validator: _Validator,
    value: Any,
    criterion_ids: Sequence[str],
) -> list[str]:
    path = "$.hard_constraints"
    if not isinstance(value, list):
        validator.add(path, "expected_array", "Must be an array; use an empty array when there are none.")
        return []
    constraint_ids: list[str] = []
    required = {"id", "name", "description", "criterion_id", "operator", "threshold"}
    known_criteria = set(criterion_ids)
    for index, constraint in enumerate(value):
        item_path = f"{path}[{index}]"
        if not validator.object_shape(constraint, item_path, required, required):
            continue
        if validator.identifier(constraint.get("id"), f"{item_path}.id"):
            constraint_ids.append(constraint["id"])
        validator.text(constraint.get("name"), f"{item_path}.name")
        validator.text(constraint.get("description"), f"{item_path}.description")
        criterion_id = constraint.get("criterion_id")
        if validator.identifier(criterion_id, f"{item_path}.criterion_id"):
            if criterion_id not in known_criteria:
                validator.add(
                    f"{item_path}.criterion_id",
                    "unknown_criterion_id",
                    "No criterion has this ID.",
                )
        if constraint.get("operator") not in {"<=", "<", ">=", ">", "==", "!="}:
            validator.add(
                f"{item_path}.operator",
                "invalid_constraint_operator",
                "Must be one of <=, <, >=, >, ==, or !=.",
            )
        validator.number(constraint.get("threshold"), f"{item_path}.threshold")
    for duplicate in sorted(_duplicates(constraint_ids)):
        validator.add(path, "duplicate_id", f"Hard-constraint ID {duplicate!r} is duplicated.")
    return constraint_ids


def _validate_alternatives(
    validator: _Validator,
    value: Any,
    criterion_ids: Sequence[str],
    constraint_ids: Sequence[str],
) -> None:
    path = "$.alternatives"
    if not isinstance(value, list):
        validator.add(path, "expected_array", "Must be an array containing 2-4 alternatives.")
        return
    if not 2 <= len(value) <= 4:
        validator.add(path, "invalid_alternative_count", "Must contain between 2 and 4 alternatives.")

    alternative_ids: list[str] = []
    required = {"id", "name", "description", "constraint_results", "criterion_estimates"}
    expected_criteria = set(criterion_ids)
    expected_constraints = set(constraint_ids)
    for index, alternative in enumerate(value):
        item_path = f"{path}[{index}]"
        if not validator.object_shape(alternative, item_path, required, required):
            continue
        if validator.identifier(alternative.get("id"), f"{item_path}.id"):
            alternative_ids.append(alternative["id"])
        validator.text(alternative.get("name"), f"{item_path}.name")
        validator.text(alternative.get("description"), f"{item_path}.description")

        results = alternative.get("constraint_results")
        if isinstance(results, Mapping):
            actual_constraints = set(results)
            for missing in sorted(expected_constraints - actual_constraints):
                validator.add(
                    f"{item_path}.constraint_results.{missing}",
                    "missing_constraint_result",
                    "This hard constraint must have an explicit true/false result.",
                )
            for unknown in sorted(actual_constraints - expected_constraints):
                validator.add(
                    f"{item_path}.constraint_results.{unknown}",
                    "unknown_constraint_id",
                    "No hard constraint has this ID.",
                )
            for constraint_id, passed in results.items():
                validator.identifier(constraint_id, f"{item_path}.constraint_results key")
                validator.boolean(passed, f"{item_path}.constraint_results.{constraint_id}")
        else:
            validator.add(
                f"{item_path}.constraint_results",
                "expected_object",
                "Must map every hard-constraint ID to true or false.",
            )

        estimates = alternative.get("criterion_estimates")
        if isinstance(estimates, Mapping):
            actual_criteria = set(estimates)
            for missing in sorted(expected_criteria - actual_criteria):
                validator.add(
                    f"{item_path}.criterion_estimates.{missing}",
                    "missing_criterion_estimate",
                    "This alternative needs a triangular estimate for every criterion.",
                )
            for unknown in sorted(actual_criteria - expected_criteria):
                validator.add(
                    f"{item_path}.criterion_estimates.{unknown}",
                    "unknown_criterion_id",
                    "No criterion has this ID.",
                )
            for criterion_id, estimate in estimates.items():
                validator.identifier(criterion_id, f"{item_path}.criterion_estimates key")
                _validate_triangle(validator, estimate, f"{item_path}.criterion_estimates.{criterion_id}")
        else:
            validator.add(
                f"{item_path}.criterion_estimates",
                "expected_object",
                "Must map every criterion ID to a triangular estimate.",
            )

    for duplicate in sorted(_duplicates(alternative_ids)):
        validator.add(path, "duplicate_id", f"Alternative ID {duplicate!r} is duplicated.")


def _validate_analysis_settings(validator: _Validator, value: Any) -> None:
    path = "$.analysis_settings"
    required = {"random_seed", "monte_carlo_samples", "clamp_utility"}
    if not validator.object_shape(value, path, required, required):
        return
    if validator.integer(value.get("monte_carlo_samples"), f"{path}.monte_carlo_samples"):
        if value["monte_carlo_samples"] < 1:
            validator.add(
                f"{path}.monte_carlo_samples",
                "invalid_sample_count",
                "Must be at least 1.",
            )
    validator.integer(value.get("random_seed"), f"{path}.random_seed")
    if validator.boolean(value.get("clamp_utility"), f"{path}.clamp_utility"):
        if value["clamp_utility"] is not True:
            validator.add(
                f"{path}.clamp_utility",
                "clamping_required",
                "Model version 1.0 analysis requires utility clamping to be true.",
            )


def _validate_multi_criteria(validator: _Validator, model: Mapping[str, Any]) -> None:
    criterion_ids = _validate_criteria(validator, model.get("criteria"))
    constraint_ids = _validate_constraints(
        validator,
        model.get("hard_constraints"),
        criterion_ids,
    )
    _validate_alternatives(
        validator,
        model.get("alternatives"),
        criterion_ids,
        constraint_ids,
    )
    _validate_analysis_settings(validator, model.get("analysis_settings"))


def _validate_sequential(validator: _Validator, model: Mapping[str, Any]) -> None:
    scale_path = "$.utility_scale"
    scale_fields = {"minimum", "maximum", "unit", "description"}
    scale: tuple[float, float] | None = None
    scale_value = model.get("utility_scale")
    if validator.object_shape(scale_value, scale_path, scale_fields, scale_fields):
        if scale_fields.issubset(scale_value):
            minimum_ok = validator.number(scale_value["minimum"], f"{scale_path}.minimum")
            maximum_ok = validator.number(scale_value["maximum"], f"{scale_path}.maximum")
            validator.text(scale_value["unit"], f"{scale_path}.unit")
            validator.text(scale_value["description"], f"{scale_path}.description")
            if minimum_ok and maximum_ok:
                minimum = float(scale_value["minimum"])
                maximum = float(scale_value["maximum"])
                if minimum >= maximum:
                    validator.add(scale_path, "invalid_utility_scale", "Scale minimum must be less than maximum.")
                else:
                    scale = minimum, maximum

    state_path = "$.state"
    state_fields = {"remaining_opportunities", "unseen_options_remaining", "best_known_value"}
    state_value = model.get("state")
    if validator.object_shape(state_value, state_path, state_fields, state_fields):
        if state_fields.issubset(state_value):
            if validator.integer(state_value["remaining_opportunities"], f"{state_path}.remaining_opportunities"):
                if state_value["remaining_opportunities"] < 1:
                    validator.add(
                        f"{state_path}.remaining_opportunities",
                        "invalid_remaining_opportunities",
                        "Must be at least 1 because it includes the current decision.",
                    )
            if validator.integer(state_value["unseen_options_remaining"], f"{state_path}.unseen_options_remaining"):
                if state_value["unseen_options_remaining"] < 0:
                    validator.add(
                        f"{state_path}.unseen_options_remaining",
                        "invalid_unseen_options",
                        "Must be 0 or greater.",
                    )
            best_known = state_value["best_known_value"]
            if validator.number(best_known, f"{state_path}.best_known_value") and scale:
                if not scale[0] <= best_known <= scale[1]:
                    validator.add(
                        f"{state_path}.best_known_value",
                        "best_known_outside_scale",
                        f"Must be within the declared utility scale [{scale[0]}, {scale[1]}].",
                    )

    distribution = _validate_triangle(
        validator,
        model.get("new_option_distribution"),
        "$.new_option_distribution",
    )
    if distribution and scale:
        if distribution[0] < scale[0] or distribution[2] > scale[1]:
            validator.add(
                "$.new_option_distribution",
                "distribution_outside_scale",
                f"Minimum and maximum must stay within the declared utility scale [{scale[0]}, {scale[1]}].",
            )

    if "analysis_settings" in model:
        settings_path = "$.analysis_settings"
        settings_fields = {"quadrature_points"}
        settings = model["analysis_settings"]
        if validator.object_shape(settings, settings_path, settings_fields, settings_fields):
            if settings_fields.issubset(settings) and validator.integer(
                settings["quadrature_points"],
                f"{settings_path}.quadrature_points",
            ):
                points = settings["quadrature_points"]
                if points < 1 or points % 2 == 0:
                    validator.add(
                        f"{settings_path}.quadrature_points",
                        "invalid_quadrature_points",
                        "Must be a positive odd integer; omit analysis_settings to use the default of 101.",
                    )


def validate_model(model: Any) -> list[ValidationIssue]:
    """Return every detected v1 input error without altering the supplied object."""

    validator = _Validator()
    if not isinstance(model, Mapping):
        validator.add("$", "expected_object", "The decision model must be a JSON object.")
        return validator.issues

    model_type = model.get("model_type")
    if model_type == "multi_criteria":
        required = COMMON_REQUIRED | MULTI_REQUIRED
        allowed = COMMON_ALLOWED | MULTI_REQUIRED
    elif model_type == "sequential_exploration":
        required = COMMON_REQUIRED | SEQUENTIAL_REQUIRED
        allowed = COMMON_ALLOWED | SEQUENTIAL_ALLOWED
    else:
        required = COMMON_REQUIRED
        allowed = COMMON_ALLOWED

    validator.object_shape(model, "$", required, allowed)
    if model_type not in SUPPORTED_MODEL_TYPES:
        validator.add(
            "$.model_type",
            "unknown_model_type",
            "Must be 'multi_criteria' or 'sequential_exploration'.",
        )

    _validate_common(validator, model)
    if model_type == "multi_criteria":
        _validate_multi_criteria(validator, model)
    elif model_type == "sequential_exploration":
        _validate_sequential(validator, model)
    return validator.issues


def validate_model_or_raise(model: Any) -> None:
    issues = validate_model(model)
    if issues:
        raise DecisionModelValidationError(issues)


def _reject_non_finite_json(token: str) -> None:
    raise ValueError(f"JSON contains non-standard numeric token {token!r}.")


def load_json(path: str | Path) -> dict[str, Any]:
    """Load strict JSON, rejecting Python's non-standard NaN and Infinity extensions."""

    source = Path(path)
    data = json.loads(
        source.read_text(encoding="utf-8"),
        parse_constant=_reject_non_finite_json,
    )
    if not isinstance(data, dict):
        raise ValueError("The top-level JSON value must be an object.")
    return data


def load_validated_model(path: str | Path) -> DecisionModel:
    data = load_json(path)
    validate_model_or_raise(data)
    return model_from_validated_dict(data)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Decision Architect model v1 JSON files.")
    parser.add_argument("files", nargs="+", help="One or more decision-model JSON files")
    args = parser.parse_args(argv)

    failed = False
    for filename in args.files:
        try:
            data = load_json(filename)
            issues = validate_model(data)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            failed = True
            print(f"[INVALID] {filename}")
            print(f"  $: {error}")
            continue
        if issues:
            failed = True
            print(f"[INVALID] {filename}")
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"[OK] {filename}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
