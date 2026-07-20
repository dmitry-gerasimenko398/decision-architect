"""Versioned, confirmation-gated persisted interview sessions."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .interview import safe_identifier
from .model_draft import (
    SourceType,
    create_field_records,
    draft_validation_issues,
    field_tracking_issues,
    model_review_markdown,
)
from .validation import validate_model_or_raise
from .text_io import atomic_write_bytes, atomic_write_utf8_lf


SESSION_VERSION = "1.0"
EXPLICIT_CONFIRMATION_TOKEN = "CONFIRM"
SESSION_FILES = {
    "state": "session-state.json",
    "proposed_model": "proposed-model.json",
    "confirmed_model": "confirmed-model.json",
    "result": "result.json",
    "report": "report.html",
    "summary": "session-summary.md",
}


class SessionError(ValueError):
    """Raised when a session operation cannot be performed safely."""


def atomic_write_json(path: str | Path, value: Any) -> Path:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    return atomic_write_utf8_lf(path, text)


def atomic_write_text(path: str | Path, value: str) -> Path:
    return atomic_write_utf8_lf(path, value)


def session_slug(value: str) -> str:
    return safe_identifier(value, fallback="decision-session", maximum_length=48)


def _contained_path(root: Path, child: Path) -> Path:
    resolved_root = root.resolve()
    resolved_child = child.resolve()
    try:
        resolved_child.relative_to(resolved_root)
    except ValueError as error:
        raise SessionError("Session path must remain inside the configured sessions directory.") from error
    return resolved_child


def session_directory(
    sessions_root: str | Path,
    slug: str,
    *,
    require_existing: bool = False,
) -> Path:
    if slug != session_slug(slug) or any(separator in slug for separator in ("/", "\\")):
        raise SessionError("Use the safe session slug printed by session-init; paths are not accepted.")
    root = Path(sessions_root)
    target = _contained_path(root, root / slug)
    if require_existing and not target.is_dir():
        raise SessionError(f"Session {slug!r} does not exist in {root}.")
    return target


def new_session_state(slug: str, model_type: str | None = None) -> dict[str, Any]:
    if model_type not in {None, "multi_criteria", "sequential_exploration"}:
        raise SessionError("Model type must be multi_criteria or sequential_exploration.")
    return {
        "session_version": SESSION_VERSION,
        "session_slug": slug,
        "stage": "model_selection" if model_type is None else "interview",
        "model_type": {
            "value": model_type,
            "status": "missing" if model_type is None else "provisional",
            "source_type": "system_proposal",
            "note": "The user must confirm the selected structure.",
        },
        "fields": {},
        "explicit_confirmation": {
            "value": None,
            "status": "missing",
            "source_type": "user_statement",
            "note": "Require the exact reply CONFIRM after displaying the complete model review.",
        },
        "model_review": {
            "status": "missing",
            "proposed_model_sha256": None,
            "review_markdown_sha256": None,
            "note": "session-check must display this exact draft before confirmation.",
        },
        "artifacts": dict(SESSION_FILES),
    }


def initialize_session(
    name: str,
    *,
    sessions_root: str | Path = "sessions",
    model_type: str | None = None,
) -> Path:
    slug = session_slug(name)
    root = Path(sessions_root)
    root.mkdir(parents=True, exist_ok=True)
    directory = session_directory(root, slug)
    try:
        directory.mkdir()
    except FileExistsError as error:
        raise SessionError(f"Session {slug!r} already exists; choose another name.") from error
    atomic_write_json(directory / SESSION_FILES["state"], new_session_state(slug, model_type))
    return directory


def load_json_object(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SessionError(f"Could not read JSON object {source}: {error}") from error
    if not isinstance(value, dict):
        raise SessionError(f"{source} must contain one JSON object.")
    return value


def stage_proposed_model(
    directory: str | Path,
    model: Mapping[str, Any],
    *,
    default_source_type: SourceType = "system_proposal",
    source_types: Mapping[str, SourceType] | None = None,
) -> Path:
    """Persist a calculation-blocked draft and create transparent field records."""

    session_path = Path(directory)
    state_path = session_path / SESSION_FILES["state"]
    state = load_json_object(state_path)
    if (session_path / SESSION_FILES["confirmed_model"]).exists():
        raise SessionError(
            "This session already has a confirmed model. Start a new session for material changes."
        )
    proposed = copy.deepcopy(dict(model))
    if proposed.get("confirmed_by_user") is True:
        raise SessionError("A proposed model must keep confirmed_by_user false until the gate passes.")
    proposed["confirmed_by_user"] = False
    model_type = proposed.get("model_type")
    if model_type not in {"multi_criteria", "sequential_exploration"}:
        raise SessionError("The proposed model must select one supported model type.")
    state["model_type"] = {
        "value": model_type,
        "status": "provisional",
        "source_type": "system_proposal",
        "note": "Confirm this structural choice during the model review.",
    }
    state["fields"] = create_field_records(
        proposed,
        status="provisional",
        source_type=default_source_type,
        source_types=source_types,
    )
    state["stage"] = "model_review"
    state["model_review"] = {
        "status": "missing",
        "proposed_model_sha256": None,
        "review_markdown_sha256": None,
        "note": "session-check must display this exact draft before confirmation.",
    }
    output = atomic_write_json(session_path / SESSION_FILES["proposed_model"], proposed)
    atomic_write_json(state_path, state)
    return output


def session_check(directory: str | Path) -> list[str]:
    session_path = Path(directory)
    state = load_json_object(session_path / SESSION_FILES["state"])
    proposed_path = session_path / SESSION_FILES["proposed_model"]
    if not proposed_path.exists():
        return ["proposed-model.json is missing; continue the interview before confirmation."]
    proposed = load_json_object(proposed_path)
    issues = [str(issue) for issue in draft_validation_issues(proposed)]
    if state.get("model_type", {}).get("value") != proposed.get("model_type"):
        issues.append("The session model type does not match proposed-model.json.")
    issues.extend(field_tracking_issues(proposed, state.get("fields")))
    return issues


def _fingerprint(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record_model_review(directory: str | Path) -> str:
    """Persist proof that the complete current review was generated for display."""

    session_path = Path(directory)
    issues = session_check(session_path)
    if issues:
        raise SessionError("The proposed model is not ready for review:\n- " + "\n- ".join(issues))
    state_path = session_path / SESSION_FILES["state"]
    state = load_json_object(state_path)
    proposed = load_json_object(session_path / SESSION_FILES["proposed_model"])
    review = model_review_markdown(proposed)
    state["stage"] = "awaiting_confirmation"
    state["model_review"] = {
        "status": "displayed",
        "proposed_model_sha256": _fingerprint(proposed),
        "review_markdown_sha256": _text_fingerprint(review),
        "note": "The complete review was generated by session-check for user display.",
    }
    atomic_write_json(state_path, state)
    return review


def _restore_file(path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        atomic_write_bytes(path, previous)


def finalize_session(
    directory: str | Path,
    *,
    confirmation: str,
) -> Path:
    """Write confirmed-model.json only after exact confirmation and complete checks."""

    if confirmation != EXPLICIT_CONFIRMATION_TOKEN:
        raise SessionError("Explicit confirmation is required. The exact reply must be CONFIRM.")
    session_path = Path(directory)
    state_path = session_path / SESSION_FILES["state"]
    state = load_json_object(state_path)
    confirmed_path = session_path / SESSION_FILES["confirmed_model"]
    if confirmed_path.exists():
        existing = load_json_object(confirmed_path)
        existing_fingerprint = _fingerprint(existing)
        if (
            state.get("stage") == "confirmed"
            and state.get("explicit_confirmation", {}).get("value") == EXPLICIT_CONFIRMATION_TOKEN
            and state.get("confirmed_model_sha256") == existing_fingerprint
        ):
            return confirmed_path
        raise SessionError("A confirmed model exists but the session record is inconsistent.")
    issues = session_check(session_path)
    if issues:
        raise SessionError("The proposed model is not ready for confirmation:\n- " + "\n- ".join(issues))
    proposed = load_json_object(session_path / SESSION_FILES["proposed_model"])
    review = model_review_markdown(proposed)
    review_record = state.get("model_review", {})
    if (
        state.get("stage") != "awaiting_confirmation"
        or review_record.get("status") != "displayed"
        or review_record.get("proposed_model_sha256") != _fingerprint(proposed)
        or review_record.get("review_markdown_sha256") != _text_fingerprint(review)
    ):
        raise SessionError(
            "The complete current model review has not been displayed. Run session-check, "
            "show its output to the user, then request the exact reply CONFIRM."
        )
    confirmed = copy.deepcopy(proposed)
    confirmed["confirmed_by_user"] = True
    validate_model_or_raise(confirmed)
    fingerprint = _fingerprint(confirmed)

    for record in state["fields"].values():
        if record["status"] == "provisional":
            record["status"] = "user_confirmed"
    state["model_type"]["status"] = "user_confirmed"
    state["explicit_confirmation"] = {
        "value": EXPLICIT_CONFIRMATION_TOKEN,
        "status": "user_confirmed",
        "source_type": "user_statement",
        "note": "Exact confirmation was supplied after the complete model review.",
    }
    state["stage"] = "confirmed"
    state["model_review"]["status"] = "user_confirmed"
    state["confirmed_model_sha256"] = fingerprint

    summary = model_review_markdown(confirmed).replace(
        "Please reply CONFIRM to run this exact model, or tell me what should be changed.",
        "Explicitly confirmed. The model is ready for deterministic analysis.",
    )
    summary_path = session_path / SESSION_FILES["summary"]
    watched = (summary_path, confirmed_path, state_path)
    previous = {path: path.read_bytes() if path.exists() else None for path in watched}
    try:
        atomic_write_text(summary_path, summary)
        atomic_write_json(confirmed_path, confirmed)
        atomic_write_json(state_path, state)
    except BaseException:
        for path in watched:
            _restore_file(path, previous[path])
        raise
    return confirmed_path
