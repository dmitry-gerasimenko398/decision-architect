"""Windows-friendly command-line interface for Decision Architect."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from .engine import UnsupportedModelTypeError, analyze_file
from .multi_criteria import CalculationError
from .reporting import (
    ReportError,
    concise_result_summary,
    generate_demo_index,
    generate_report,
)
from .result_serialization import result_to_json_text, write_result_json
from .sequential_exploration import SequentialCalculationError
from .session_state import (
    SESSION_FILES,
    SessionError,
    finalize_session,
    initialize_session,
    load_json_object,
    record_model_review,
    session_check,
    session_directory,
    stage_proposed_model,
)
from .validation import DecisionModelValidationError


def _print_sensitivity_summary(result: dict) -> None:
    sensitivity = result["sensitivity"]
    candidates = []
    boundary_ties = []
    for criterion in sensitivity["criteria"]:
        for direction in ("lower_switch", "upper_switch"):
            switch = criterion[direction]
            if switch is not None and switch["change_type"] == "winner_switch":
                candidates.append(
                    (
                        abs(switch["threshold_weight"] - criterion["baseline_weight"]),
                        criterion["criterion_id"],
                        direction,
                        switch,
                    )
                )
            elif switch is not None and switch["change_type"] == "boundary_tie":
                boundary_ties.append(
                    (
                        abs(switch["threshold_weight"] - criterion["baseline_weight"]),
                        criterion["criterion_id"],
                        switch,
                    )
                )
    if candidates:
        distance, criterion_id, _, switch = min(candidates)
        print(
            "Closest winner switch (smallest absolute change from its baseline weight):",
            file=sys.stderr,
        )
        print(
            f"  {criterion_id}: {switch['explanation']} "
            f"Absolute weight change: {distance:.12g}.",
            file=sys.stderr,
        )
    elif boundary_ties:
        _, criterion_id, switch = min(boundary_ties)
        print(
            "Weight sensitivity: no winner changes inside the permitted ranges; "
            f"{criterion_id} reaches a tie at boundary {switch['threshold_weight']:.12g}.",
            file=sys.stderr,
        )
    elif sensitivity["status"] == "analyzed":
        print(
            "Weight sensitivity: the baseline winner remains unique across every tested "
            "criterion's full permitted weight range.",
            file=sys.stderr,
        )
    else:
        print(f"Weight sensitivity: {sensitivity['explanation']}", file=sys.stderr)


def _write_user_text(text: str) -> None:
    """Write interview text without crashing on a limited Windows console encoding."""

    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding)
        sys.stdout.write(safe_text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="decision_architect")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser(
        "analyze",
        help="Validate and analyze a decision-model-v1 JSON file.",
    )
    analyze.add_argument("model", help="Path to the confirmed decision-model JSON file")
    analyze.add_argument("--output", help="Optional path for decision-result-v1 JSON")
    report = subparsers.add_parser(
        "report",
        help="Render an existing decision-result-v1 JSON file as standalone HTML.",
    )
    report.add_argument("result", help="Path to an existing decision-result-v1 JSON file")
    report.add_argument("--output", required=True, help="Path for the standalone HTML report")
    report.add_argument(
        "--open",
        action="store_true",
        dest="open_report",
        help="Open the completed report in the default browser.",
    )
    report_index = subparsers.add_parser(
        "report-index",
        help="Build the local release demonstration index.",
    )
    report_index.add_argument("report_directory", help="Directory containing the release reports")
    report_index.add_argument(
        "--results-dir",
        default="outputs",
        help="Directory containing the four validated release example results (default: outputs)",
    )
    session_init = subparsers.add_parser(
        "session-init",
        help="Create a safe persisted interview session without running calculations.",
    )
    session_init.add_argument("name", help="Human-readable session name")
    session_init.add_argument(
        "--model-type",
        choices=("multi_criteria", "sequential_exploration"),
        help="Optional provisional model selection",
    )
    session_init.add_argument(
        "--sessions-dir", default="sessions", help="Session root directory (default: sessions)"
    )
    session_stage = subparsers.add_parser(
        "session-stage",
        help="Store a proposed, calculation-blocked model in an existing session.",
    )
    session_stage.add_argument("session_slug", help="Safe slug printed by session-init")
    session_stage.add_argument("draft", help="Path to proposed decision-model JSON")
    session_stage.add_argument(
        "--source-type",
        choices=("user_statement", "user_estimate", "system_proposal", "default"),
        default="user_statement",
        help="Initial provenance for staged fields; the Skill may refine individual records",
    )
    session_stage.add_argument(
        "--source-map",
        help="Optional JSON object mapping exact model field paths to individual source types",
    )
    session_stage.add_argument(
        "--sessions-dir", default="sessions", help="Session root directory (default: sessions)"
    )
    session_check_parser = subparsers.add_parser(
        "session-check",
        help="Check a proposed session model and print its confirmation review.",
    )
    session_check_parser.add_argument("session_slug", help="Safe slug printed by session-init")
    session_check_parser.add_argument(
        "--sessions-dir", default="sessions", help="Session root directory (default: sessions)"
    )
    session_finalize = subparsers.add_parser(
        "session-finalize",
        help="Create confirmed-model.json after the exact confirmation gate passes.",
    )
    session_finalize.add_argument("session_slug", help="Safe slug printed by session-init")
    session_finalize.add_argument(
        "--confirmation",
        required=True,
        help="Exact user reply; must be CONFIRM",
    )
    session_finalize.add_argument(
        "--sessions-dir", default="sessions", help="Session root directory (default: sessions)"
    )
    subparsers.add_parser(
        "verify-release",
        help="Run the complete offline release-readiness verification checklist.",
    )
    return parser


def _run_analyze(args: argparse.Namespace) -> int:
    try:
        result = analyze_file(args.model)
        if args.output:
            output = write_result_json(result, args.output)
            print(f"Analysis complete: {args.model}", file=sys.stderr)
            print(f"Result written: {output}", file=sys.stderr)
        else:
            print(result_to_json_text(result), end="")
            print(f"Analysis complete: {args.model}", file=sys.stderr)
        if result["model_type"] == "multi_criteria":
            recommendation = result["recommendation"]
            status = recommendation["status"]
            statement = recommendation["conditional_statement"]
        else:
            status = result["recommendation_status"]
            statement = result["conditional_statement"]
        print(
            f"Recommendation status: {status}",
            file=sys.stderr,
        )
        print(statement, file=sys.stderr)
        if result["model_type"] == "multi_criteria":
            _print_sensitivity_summary(result)
        return 0
    except DecisionModelValidationError as error:
        print("Validation failed; no recommendation was produced.", file=sys.stderr)
        for issue in error.issues:
            print(f"  {issue}", file=sys.stderr)
    except (UnsupportedModelTypeError, CalculationError, SequentialCalculationError) as error:
        print("Analysis failed; no recommendation was produced.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not analyze the model; no recommendation was produced.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
    return 1


def _run_report(args: argparse.Namespace) -> int:
    try:
        output, result = generate_report(args.result, args.output)
        print(f"Report written: {output}", file=sys.stderr)
        print(f"Stored result summary: {concise_result_summary(result)}", file=sys.stderr)
        print("No decision calculations were rerun.", file=sys.stderr)
        if args.open_report:
            try:
                opened = webbrowser.open(output.resolve().as_uri())
            except (webbrowser.Error, OSError) as error:
                print(
                    f"Report was generated, but the default browser could not open it: {error}",
                    file=sys.stderr,
                )
            else:
                if opened:
                    print("Opened report in the default browser.", file=sys.stderr)
                else:
                    print(
                        "Report was generated, but the default browser did not confirm opening it.",
                        file=sys.stderr,
                    )
        return 0
    except (ReportError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not generate the report; no partial report was written.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_report_index(args: argparse.Namespace) -> int:
    try:
        output = generate_demo_index(args.report_directory, args.results_dir)
        print(f"Demo index written: {output}", file=sys.stderr)
        print("Summaries were read from validated result JSON; no calculations were rerun.", file=sys.stderr)
        return 0
    except (ReportError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not generate the demo index; no partial index was written.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_session_init(args: argparse.Namespace) -> int:
    try:
        directory = initialize_session(
            args.name,
            sessions_root=args.sessions_dir,
            model_type=args.model_type,
        )
        print(f"Session initialized: {directory}", file=sys.stderr)
        print(f"Safe session slug: {directory.name}", file=sys.stderr)
        print(
            "I've started a draft decision model. I won't calculate a recommendation until "
            "you review and confirm it.",
            file=sys.stderr,
        )
        return 0
    except (SessionError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not initialize the session.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_session_stage(args: argparse.Namespace) -> int:
    try:
        directory = session_directory(
            args.sessions_dir, args.session_slug, require_existing=True
        )
        model = load_json_object(args.draft)
        source_types = load_json_object(args.source_map) if args.source_map else None
        output = stage_proposed_model(
            directory,
            model,
            default_source_type=args.source_type,
            source_types=source_types,
        )
        issues = session_check(directory)
        print(f"Proposed model staged: {output}", file=sys.stderr)
        print("No calculation has run.", file=sys.stderr)
        if issues:
            print("The draft still needs correction:", file=sys.stderr)
            for issue in issues:
                print(f"  {issue}", file=sys.stderr)
            return 1
        print("The draft is structurally ready for a complete user review.", file=sys.stderr)
        return 0
    except (SessionError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not stage the proposed model.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_session_check(args: argparse.Namespace) -> int:
    try:
        directory = session_directory(
            args.sessions_dir, args.session_slug, require_existing=True
        )
        issues = session_check(directory)
        if issues:
            print("Session is incomplete or contradictory; no calculation may run.", file=sys.stderr)
            for issue in issues:
                print(f"  {issue}", file=sys.stderr)
            return 1
        review = record_model_review(directory)
        _write_user_text(review)
        print(
            "Your model is ready for review. No recommendation has been calculated yet.",
            file=sys.stderr,
        )
        return 0
    except (SessionError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not check the session; no calculation may run.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_session_finalize(args: argparse.Namespace) -> int:
    try:
        directory = session_directory(
            args.sessions_dir, args.session_slug, require_existing=True
        )
        output = finalize_session(directory, confirmation=args.confirmation)
        print(f"Confirmed model written: {output}", file=sys.stderr)
        print("Model confirmed. The deterministic analysis has not run yet.", file=sys.stderr)
        return 0
    except (SessionError, DecisionModelValidationError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print("Could not finalize the session; no confirmed model was written.", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return 1


def _run_verify_release() -> int:
    from .release_verification import format_verification_report, verify_release

    report = verify_release()
    print(format_verification_report(report), end="")
    return 0 if report.success else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "report":
        return _run_report(args)
    if args.command == "report-index":
        return _run_report_index(args)
    if args.command == "session-init":
        return _run_session_init(args)
    if args.command == "session-stage":
        return _run_session_stage(args)
    if args.command == "session-check":
        return _run_session_check(args)
    if args.command == "session-finalize":
        return _run_session_finalize(args)
    if args.command == "verify-release":
        return _run_verify_release()
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
