"""Confirmation-gated session persistence and end-to-end workflow tests."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from decision_architect.cli import main
from decision_architect.model_draft import (
    create_field_records,
    draft_validation_issues,
    model_review_markdown,
)
from decision_architect.multi_criteria import CalculationError
from decision_architect.result_serialization import validate_result
from decision_architect.session_state import (
    SESSION_FILES,
    SessionError,
    atomic_write_json,
    finalize_session,
    initialize_session,
    load_json_object,
    record_model_review,
    session_check,
    session_directory,
    stage_proposed_model,
)
from decision_architect.validation import validate_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
OUTPUTS = PROJECT_ROOT / "outputs"
REPORTS = PROJECT_ROOT / "reports"


def example(name: str) -> dict:
    value = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    value["confirmed_by_user"] = False
    return value


def issue_codes(model: dict) -> set[str]:
    return {issue.code for issue in draft_validation_issues(model)}


def canonical_fingerprint(value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def review_and_finalize(directory: Path) -> Path:
    record_model_review(directory)
    return finalize_session(directory, confirmation="CONFIRM")


class DraftCheckingTests(unittest.TestCase):
    def test_missing_fields_are_detected_for_both_models(self) -> None:
        multi = example("job-choice.json")
        sequential = example("feynman-restaurant.json")
        del multi["criteria"]
        del sequential["state"]
        self.assertIn("required", issue_codes(multi))
        self.assertIn("required", issue_codes(sequential))

    def test_invalid_triangle_is_detected(self) -> None:
        model = example("job-choice.json")
        model["alternatives"][0]["criterion_estimates"]["salary"] = {
            "minimum": 80,
            "most_likely": 70,
            "maximum": 90,
        }
        self.assertIn("invalid_triangular_distribution", issue_codes(model))

    def test_invalid_anchor_is_detected(self) -> None:
        model = example("job-choice.json")
        model["criteria"][0]["best_anchor"] = model["criteria"][0]["worst_anchor"]
        self.assertIn("invalid_utility_anchors", issue_codes(model))

    def test_non_normalized_provisional_weights_are_detected(self) -> None:
        model = example("job-choice.json")
        model["criteria"][0]["weight"] = 0.34
        self.assertIn("weights_not_normalized", issue_codes(model))

    def test_duplicate_alternatives_and_criteria_are_detected(self) -> None:
        model = example("job-choice.json")
        model["alternatives"][1]["id"] = model["alternatives"][0]["id"]
        model["criteria"][1]["id"] = model["criteria"][0]["id"]
        self.assertIn("duplicate_id", issue_codes(model))

    def test_review_contains_model_specific_confirmation_data(self) -> None:
        multi_review = model_review_markdown(example("job-choice.json"))
        sequential_review = model_review_markdown(example("feynman-restaurant.json"))
        self.assertIn("Criteria and weights", multi_review)
        self.assertIn("Monte Carlo samples: 10000", multi_review)
        self.assertIn("60000 / 70000 / 90000", multi_review)
        self.assertIn("Local nonprofit: fails", multi_review)
        self.assertIn("Remaining opportunities (including now): 8", sequential_review)
        self.assertIn("Quadrature points: 101", sequential_review)
        self.assertIn("Decision description:", multi_review)
        self.assertIn("Fully remote role with greater upside", multi_review)
        self.assertIn("maximize", multi_review)
        self.assertIn("Clamp utility to anchors: True", multi_review)
        self.assertIn("Utility scale meaning:", sequential_review)
        self.assertIn("Notes:", sequential_review)
        self.assertIn("## Proposed state", sequential_review)
        self.assertNotIn("## Confirmed state", sequential_review)
        self.assertTrue(multi_review.endswith("tell me what should be changed.\n"))
        self.assertNotIn("→", multi_review)


class SessionPersistenceTests(unittest.TestCase):
    def test_session_initialization_is_versioned_and_calculation_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("decision_architect.engine.analyze_file") as analyze:
                directory = initialize_session(
                    "My Job Choice", sessions_root=temporary_directory, model_type="multi_criteria"
                )
            analyze.assert_not_called()
            state = load_json_object(directory / SESSION_FILES["state"])
            self.assertEqual(directory.name, "my-job-choice")
            self.assertEqual(state["session_version"], "1.0")
            self.assertEqual(state["stage"], "interview")
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())

    def test_all_pre_confirmation_session_steps_are_calculation_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("decision_architect.engine.analyze_file") as analyze_file, patch(
                "decision_architect.multi_criteria.analyze_multi_criteria"
            ) as analyze_multi:
                directory = initialize_session("Job", sessions_root=temporary_directory)
                stage_proposed_model(directory, example("job-choice.json"))
                self.assertEqual(session_check(directory), [])
                review_and_finalize(directory)
            analyze_file.assert_not_called()
            analyze_multi.assert_not_called()

    def test_atomic_state_writing_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "state.json"
            value = {"z": [1, 2], "a": "text"}
            atomic_write_json(output, value)
            first = output.read_bytes()
            atomic_write_json(output, value)
            self.assertEqual(first, output.read_bytes())
            self.assertFalse(list(Path(temporary_directory).glob("*.tmp")))

    def test_user_controlled_session_name_cannot_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            directory = initialize_session(r"..\..\outside", sessions_root=root)
            self.assertEqual(directory.parent.resolve(), root.resolve())
            self.assertEqual(directory.name, "outside")
            with self.assertRaises(SessionError):
                session_directory(root, r"..\outside", require_existing=False)

    def test_session_files_remain_inside_selected_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            directory = initialize_session("Restaurant", sessions_root=root)
            stage_proposed_model(directory, example("feynman-restaurant.json"))
            for path in directory.iterdir():
                path.resolve().relative_to(root.resolve())

    def test_finalization_refuses_missing_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            with self.assertRaisesRegex(SessionError, "exact reply must be CONFIRM"):
                finalize_session(directory, confirmation="okay, go on")
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())

    def test_finalization_refuses_confirmation_before_review_is_displayed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            with self.assertRaisesRegex(SessionError, "review has not been displayed"):
                finalize_session(directory, confirmation="CONFIRM")
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())

    def test_review_fingerprint_blocks_changed_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            record_model_review(directory)
            proposed_path = directory / SESSION_FILES["proposed_model"]
            proposed = load_json_object(proposed_path)
            proposed["title"] = "Changed after review"
            atomic_write_json(proposed_path, proposed)
            with self.assertRaisesRegex(SessionError, "review it again"):
                finalize_session(directory, confirmation="CONFIRM")

    def test_finalization_refuses_unconfirmed_or_changed_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            state_path = directory / SESSION_FILES["state"]
            state = load_json_object(state_path)
            state["fields"]["$.title"]["status"] = "missing"
            atomic_write_json(state_path, state)
            with self.assertRaisesRegex(SessionError, "still missing"):
                finalize_session(directory, confirmation="CONFIRM")
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())

    def test_failed_validation_does_not_create_confirmed_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Broken", sessions_root=temporary_directory)
            model = example("job-choice.json")
            model["criteria"][0]["weight"] = 9
            stage_proposed_model(directory, model)
            with self.assertRaisesRegex(SessionError, "not ready"):
                finalize_session(directory, confirmation="CONFIRM")
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())

    def test_confirmed_multi_and_sequential_drafts_validate(self) -> None:
        for filename in ("job-choice.json", "feynman-restaurant.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary_directory:
                directory = initialize_session(filename, sessions_root=temporary_directory)
                stage_proposed_model(directory, example(filename))
                confirmed_path = review_and_finalize(directory)
                confirmed = load_json_object(confirmed_path)
                self.assertTrue(confirmed["confirmed_by_user"])
                self.assertEqual(validate_model(confirmed), [])

    def test_user_change_before_confirmation_replaces_reviewed_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Restaurant", sessions_root=temporary_directory)
            model = example("feynman-restaurant.json")
            stage_proposed_model(directory, model)
            model["state"]["remaining_opportunities"] = 2
            model["time_horizon"] = "The next 2 visits, including the current visit"
            stage_proposed_model(directory, model)
            confirmed = load_json_object(review_and_finalize(directory))
            self.assertEqual(confirmed["state"]["remaining_opportunities"], 2)

    def test_repeated_finalization_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            confirmed_path = review_and_finalize(directory)
            first_files = {
                name: (directory / filename).read_bytes()
                for name, filename in SESSION_FILES.items()
                if (directory / filename).exists()
            }
            finalize_session(directory, confirmation="CONFIRM")
            second_files = {
                name: (directory / filename).read_bytes()
                for name, filename in SESSION_FILES.items()
                if (directory / filename).exists()
            }
            self.assertEqual(first_files, second_files)

    def test_confirmed_session_refuses_a_replacement_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            review_and_finalize(directory)
            with self.assertRaisesRegex(SessionError, "already has a confirmed model"):
                stage_proposed_model(directory, example("job-choice.json"))

    def test_field_specific_source_map_overrides_only_named_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(
                directory,
                example("job-choice.json"),
                default_source_type="system_proposal",
                source_types={"$.alternatives[0].criterion_estimates.salary.minimum": "user_estimate"},
            )
            fields = load_json_object(directory / SESSION_FILES["state"])["fields"]
            self.assertEqual(
                fields["$.alternatives[0].criterion_estimates.salary.minimum"]["source_type"],
                "user_estimate",
            )
            self.assertEqual(fields["$.decision_id"]["source_type"], "system_proposal")

    def test_unknown_source_map_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            with self.assertRaisesRegex(ValueError, "unknown model field paths"):
                stage_proposed_model(
                    directory,
                    example("job-choice.json"),
                    source_types={"$.does_not_exist": "user_statement"},
                )

    def test_failed_summary_write_rolls_back_all_finalization_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            record_model_review(directory)
            before_state = (directory / SESSION_FILES["state"]).read_bytes()
            with patch(
                "decision_architect.session_state.atomic_write_text",
                side_effect=OSError("synthetic write failure"),
            ):
                with self.assertRaisesRegex(OSError, "synthetic write failure"):
                    finalize_session(directory, confirmation="CONFIRM")
            self.assertEqual((directory / SESSION_FILES["state"]).read_bytes(), before_state)
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())
            self.assertFalse((directory / SESSION_FILES["summary"]).exists())

    def test_failed_final_state_write_rolls_back_all_finalization_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            record_model_review(directory)
            state_path = directory / SESSION_FILES["state"]
            before_state = state_path.read_bytes()

            def fail_confirmed_state(path: str | Path, value: object) -> Path:
                if Path(path) == state_path and isinstance(value, dict) and value.get("stage") == "confirmed":
                    raise OSError("synthetic final state failure")
                return atomic_write_json(path, value)

            with patch(
                "decision_architect.session_state.atomic_write_json",
                side_effect=fail_confirmed_state,
            ):
                with self.assertRaisesRegex(OSError, "synthetic final state failure"):
                    finalize_session(directory, confirmation="CONFIRM")
            self.assertEqual(state_path.read_bytes(), before_state)
            self.assertFalse((directory / SESSION_FILES["confirmed_model"]).exists())
            self.assertFalse((directory / SESSION_FILES["summary"]).exists())

    def test_session_check_reports_missing_proposed_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Empty", sessions_root=temporary_directory)
            self.assertIn("proposed-model.json is missing", session_check(directory)[0])


class SessionCliAndPipelineTests(unittest.TestCase):
    def test_session_cli_init_stage_check_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            draft = root / "draft.json"
            draft.write_text(json.dumps(example("job-choice.json")), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(
                    main(["session-init", "Demo Job", "--sessions-dir", str(root)]), 0
                )
                self.assertEqual(
                    main(
                        [
                            "session-stage", "demo-job", str(draft),
                            "--sessions-dir", str(root),
                        ]
                    ),
                    0,
                )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(["session-check", "demo-job", "--sessions-dir", str(root)]), 0
                )
            self.assertIn("Please reply CONFIRM", stdout.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "session-finalize", "demo-job", "--sessions-dir", str(root),
                            "--confirmation", "CONFIRM",
                        ]
                    ),
                    0,
                )
            self.assertTrue((root / "demo-job" / "confirmed-model.json").exists())

    def test_complete_session_uses_existing_analyze_and_report_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            confirmed = review_and_finalize(directory)
            result_path = directory / SESSION_FILES["result"]
            report_path = directory / SESSION_FILES["report"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(["analyze", str(confirmed), "--output", str(result_path)]), 0
                )
                self.assertEqual(
                    main(["report", str(result_path), "--output", str(report_path)]), 0
                )
            self.assertEqual(validate_result(load_json_object(result_path)), [])
            self.assertTrue(report_path.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_failed_analysis_creates_no_fake_result_or_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Job", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            confirmed = review_and_finalize(directory)
            result_path = directory / SESSION_FILES["result"]
            report_path = directory / SESSION_FILES["report"]
            with patch(
                "decision_architect.cli.analyze_file",
                side_effect=CalculationError("synthetic failure"),
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(
                    main(["analyze", str(confirmed), "--output", str(result_path)]), 0
                )
            self.assertFalse(result_path.exists())
            self.assertFalse(report_path.exists())

    def test_existing_examples_results_and_reports_are_not_changed(self) -> None:
        watched = [
            OUTPUTS / "job-choice-result.json",
            OUTPUTS / "feynman-restaurant-result.json",
            OUTPUTS / "feynman-restaurant-short-horizon-result.json",
            REPORTS / "job-choice-report.html",
            REPORTS / "feynman-restaurant-report.html",
            REPORTS / "feynman-restaurant-short-horizon-report.html",
            REPORTS / "index.html",
        ]
        before = {path: path.read_bytes() for path in watched}
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = initialize_session("Temporary", sessions_root=temporary_directory)
            stage_proposed_model(directory, example("job-choice.json"))
            review_and_finalize(directory)
        self.assertEqual(before, {path: path.read_bytes() for path in watched})


class DemonstrationArtifactTests(unittest.TestCase):
    def test_persisted_demo_sessions_are_valid_and_match_historical_calculations(self) -> None:
        mappings = (
            ("job-choice-demo", "job-choice-result.json", "job-choice-report.html"),
            (
                "feynman-restaurant-8-visits-demo",
                "feynman-restaurant-result.json",
                "feynman-restaurant-report.html",
            ),
            (
                "feynman-restaurant-2-visits-demo",
                "feynman-restaurant-short-horizon-result.json",
                "feynman-restaurant-short-horizon-report.html",
            ),
        )
        for slug, result_name, report_name in mappings:
            with self.subTest(slug=slug):
                directory = PROJECT_ROOT / "demo_sessions" / slug
                confirmed = load_json_object(directory / SESSION_FILES["confirmed_model"])
                result = load_json_object(directory / SESSION_FILES["result"])
                state = load_json_object(directory / SESSION_FILES["state"])
                proposed = load_json_object(directory / SESSION_FILES["proposed_model"])
                self.assertEqual(validate_model(confirmed), [])
                self.assertEqual(validate_result(result), [])
                historical = load_json_object(OUTPUTS / result_name)
                if result["model_type"] == "multi_criteria":
                    self.assertEqual(result["recommendation"], historical["recommendation"])
                else:
                    for key in (
                        "exploit_value",
                        "explore_value",
                        "recommended_action",
                        "policy_by_remaining_opportunities",
                        "action_switch_points",
                    ):
                        self.assertEqual(result[key], historical[key])
                report = (directory / SESSION_FILES["report"]).read_text(encoding="utf-8")
                self.assertTrue(report.startswith("<!doctype html>"))
                self.assertEqual(state["stage"], "confirmed")
                self.assertEqual(state["explicit_confirmation"]["value"], "CONFIRM")
                self.assertEqual(state["model_review"]["status"], "user_confirmed")
                self.assertEqual(
                    state["model_review"]["proposed_model_sha256"],
                    canonical_fingerprint(proposed),
                )
                self.assertEqual(state["confirmed_model_sha256"], canonical_fingerprint(confirmed))
                review = model_review_markdown(proposed)
                self.assertEqual(
                    state["model_review"]["review_markdown_sha256"],
                    hashlib.sha256(review.encode("utf-8")).hexdigest(),
                )
                self.assertTrue(
                    all(record["status"] == "user_confirmed" for record in state["fields"].values())
                )
                self.assertEqual(state["fields"]["$.model_version"]["source_type"], "system_proposal")

    def test_demo_provenance_and_user_terminology_are_preserved(self) -> None:
        job_state = load_json_object(PROJECT_ROOT / "demo_sessions" / "job-choice-demo" / "session-state.json")
        self.assertEqual(
            job_state["fields"]["$.alternatives[0].criterion_estimates.salary.minimum"][
                "source_type"
            ],
            "user_estimate",
        )
        self.assertEqual(
            job_state["fields"]["$.analysis_settings.random_seed"]["source_type"],
            "system_proposal",
        )
        for slug in (
            "feynman-restaurant-8-visits-demo",
            "feynman-restaurant-2-visits-demo",
        ):
            model = load_json_object(PROJECT_ROOT / "demo_sessions" / slug / "confirmed-model.json")
            state = load_json_object(PROJECT_ROOT / "demo_sessions" / slug / "session-state.json")
            self.assertIn("dish", model["title"].lower())
            self.assertNotIn("unseen restaurant", json.dumps(model).lower())
            self.assertEqual(
                state["fields"]["$.assumptions[2]"]["source_type"], "system_proposal"
            )
            self.assertEqual(
                state["fields"]["$.state.best_known_value"]["source_type"], "user_estimate"
            )

    def test_transcript_numbers_match_generated_results(self) -> None:
        job_text = (EXAMPLES / "conversations" / "job-choice-interview.md").read_text(
            encoding="utf-8"
        )
        restaurant_text = (
            EXAMPLES / "conversations" / "feynman-restaurant-interview.md"
        ).read_text(encoding="utf-8")
        job = load_json_object(PROJECT_ROOT / "demo_sessions" / "job-choice-demo" / "result.json")
        long = load_json_object(
            PROJECT_ROOT / "demo_sessions" / "feynman-restaurant-8-visits-demo" / "result.json"
        )
        short = load_json_object(
            PROJECT_ROOT / "demo_sessions" / "feynman-restaurant-2-visits-demo" / "result.json"
        )
        self.assertIn(f'{job["recommendation"]["leading_monte_carlo_mean_utility"]:.10f}', job_text)
        self.assertIn(f'{job["recommendation"]["leading_win_probability"] * 100:.2f}%', job_text)
        self.assertIn("**User:** Here are my estimates:\n\n| Alternative", job_text)
        self.assertIn(f'{long["explore_value"]:.10f}', restaurant_text)
        self.assertIn(f'{short["explore_value"]:.10f}', restaurant_text)
        self.assertIn("policy changes from EXPLOIT to EXPLORE at 3", restaurant_text)

    def test_demo_guide_fits_the_requested_three_minute_structure(self) -> None:
        script = (PROJECT_ROOT / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
        self.assertIn("2 minutes 45 seconds", script)
        self.assertIn("$decision-analysis", script)
        self.assertIn("CONFIRM", script)
        self.assertIn("reports/job-choice-report.html", script)
        self.assertIn("reports/feynman-restaurant-report.html", script)


if __name__ == "__main__":
    unittest.main()
