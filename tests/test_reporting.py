"""Deterministic, accessible, and secure HTML reporting tests."""

from __future__ import annotations

import contextlib
import copy
import html
import io
import json
import tempfile
import unittest
import re
import webbrowser
from pathlib import Path
from unittest.mock import patch

from decision_architect.cli import main
from decision_architect.engine import analyze_model
from decision_architect.models import model_from_validated_dict
from decision_architect.report_templates import (
    CONDITIONALITY_STATEMENT,
    render_multi_criteria_report,
    render_sequential_report,
)
from decision_architect.reporting import (
    ReportError,
    generate_demo_index,
    generate_report,
    load_validated_result,
    render_report,
)
from decision_architect.result_serialization import write_result_json
from decision_architect.validation import validate_model_or_raise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = PROJECT_ROOT / "outputs"
EXAMPLES = PROJECT_ROOT / "examples"
JOB_RESULT = OUTPUTS / "job-choice-result.json"
LONG_RESULT = OUTPUTS / "feynman-restaurant-result.json"
SHORT_RESULT = OUTPUTS / "feynman-restaurant-short-horizon-result.json"
UNIVERSITY_RESULT = OUTPUTS / "university-transfer-result.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ReportRenderingTests(unittest.TestCase):
    def test_valid_multi_criteria_result_produces_html(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        self.assertTrue(rendered.startswith("<!doctype html>"))
        self.assertIn("Multi-criteria decision model", rendered)
        self.assertIn("Remote Startup", rendered)

    def test_valid_sequential_result_produces_html(self) -> None:
        rendered = render_report(load_json(LONG_RESULT))
        self.assertIn("Feynman-inspired exploration model", rendered)
        self.assertIn(">EXPLORE<", rendered)

    def test_generated_html_is_deterministic(self) -> None:
        result = load_json(JOB_RESULT)
        first = render_report(result)
        second = render_report(copy.deepcopy(result))
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_user_controlled_text_is_escaped(self) -> None:
        result = load_json(JOB_RESULT)
        result["assumptions"][0] = "A < B & C > D"
        rendered = render_report(result)
        self.assertIn("A &lt; B &amp; C &gt; D", rendered)
        self.assertNotIn("A < B", rendered)

    def test_script_tags_cannot_become_executable_markup(self) -> None:
        result = load_json(JOB_RESULT)
        attack = "</script><script>alert('report')</script>"
        result["assumptions"][0] = attack
        rendered = render_report(result)
        self.assertNotIn("<script", rendered.lower())
        self.assertIn(html.escape(attack, quote=True), rendered)

    def test_attribute_breaking_text_is_escaped(self) -> None:
        result = load_json(JOB_RESULT)
        attack = '\"><img src=x onerror="alert(1)">'
        result["assumptions"][0] = attack
        rendered = render_report(result)
        self.assertNotIn("<img", rendered.lower())
        self.assertIn("&quot;&gt;&lt;img", rendered)

    def test_invalid_result_is_rejected(self) -> None:
        with self.assertRaises(ReportError):
            render_report({"model_type": "multi_criteria"})

    def test_unsupported_model_type_is_rejected(self) -> None:
        result = load_json(JOB_RESULT)
        result["model_type"] = "unsupported"
        with self.assertRaisesRegex(ReportError, "supported"):
            render_report(result)

    def test_renderer_does_not_invoke_calculation_engine(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "report.html"
            with patch("decision_architect.engine.analyze_file") as analyze, patch(
                "decision_architect.multi_criteria.analyze_multi_criteria"
            ) as multi_calculation:
                generate_report(JOB_RESULT, output)
            analyze.assert_not_called()
            multi_calculation.assert_not_called()

    def test_conditionality_statement_is_prominent_in_both_models(self) -> None:
        for result_path in (JOB_RESULT, LONG_RESULT):
            with self.subTest(result=result_path.name):
                rendered = render_report(load_json(result_path))
                self.assertIn(html.escape(CONDITIONALITY_STATEMENT), rendered)
                self.assertIn('class="conditionality"', rendered)

    def test_all_multi_recommendation_statuses_have_distinct_rendering(self) -> None:
        original = load_json(JOB_RESULT)
        cases = {
            "recommended": "Recommended under this model",
            "close_call": "Close call",
            "only_feasible_alternative": "Only feasible alternative",
            "mean_utility_tie": "Mean-utility tie",
            "no_feasible_alternative": "No feasible alternative",
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                result = copy.deepcopy(original)
                recommendation = result["recommendation"]
                recommendation["status"] = status
                if status == "mean_utility_tie":
                    recommendation["alternative_id"] = None
                    recommendation["tied_alternative_ids"] = ["remote-startup", "stable-corp"]
                if status == "no_feasible_alternative":
                    recommendation["alternative_id"] = None
                    recommendation["tied_alternative_ids"] = []
                    recommendation["leading_monte_carlo_mean_utility"] = None
                    recommendation["leading_win_probability"] = None
                rendered = render_multi_criteria_report(result, json.dumps(result))
                self.assertIn(expected, rendered)

    def test_tie_does_not_render_a_false_single_winner(self) -> None:
        result = load_json(JOB_RESULT)
        result["recommendation"].update(
            {
                "status": "mean_utility_tie",
                "alternative_id": None,
                "tied_alternative_ids": ["remote-startup", "stable-corp"],
            }
        )
        rendered = render_multi_criteria_report(result, json.dumps(result))
        self.assertIn("Tied leaders: Remote Startup, Stable Corp", rendered)
        self.assertNotIn("Recommended under this model", rendered)

    def test_no_feasible_alternative_renders_without_fake_metrics(self) -> None:
        result = load_json(JOB_RESULT)
        result["alternative_results"] = []
        result["recommendation"].update(
            {
                "status": "no_feasible_alternative",
                "alternative_id": None,
                "tied_alternative_ids": [],
                "leading_monte_carlo_mean_utility": None,
                "leading_win_probability": None,
            }
        )
        rendered = render_multi_criteria_report(result, json.dumps(result))
        self.assertIn("No alternative satisfies all hard constraints", rendered)
        self.assertIn("No feasible alternatives to compare", rendered)

    def test_excluded_alternatives_and_reasons_are_present(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        self.assertIn("Local Nonprofit", rendered)
        self.assertIn("minimum_salary", rendered)
        self.assertIn("minimum 48000 must be at least 50000", rendered)

    def test_sensitivity_threshold_and_robust_intervals_are_present(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        self.assertIn("Closest real winner switch", rendered)
        self.assertIn("0.84359", rendered)
        self.assertIn("Robust interval for every criterion", rendered)
        self.assertIn("uncertainty in the estimates", rendered)
        self.assertIn("changing preferences", rendered)

    def test_multi_uncertainty_table_is_complete(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        for heading in ("MC mean", "Analytical", "Win probability", "P10", "P50", "P90", "Std. dev."):
            self.assertIn(heading, rendered)
        for alternative in ("Remote Startup", "Stable Corp"):
            self.assertIn(alternative, rendered)

    def test_criterion_contributions_include_weight_mean_and_contribution(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        self.assertIn("Criterion mean utility", rendered)
        self.assertIn("Weighted contribution", rendered)
        self.assertIn("These modeled components are not causal effects", rendered)

    def test_sequential_current_state_is_present(self) -> None:
        rendered = render_report(load_json(LONG_RESULT))
        for expected in ("Remaining opportunities", "Unseen options", "Best-known value", "Most likely"):
            self.assertIn(expected, rendered)
        self.assertIn("8", rendered)
        self.assertIn("10", rendered)
        self.assertIn("6.5", rendered)

    def test_sequential_policy_table_contains_every_horizon(self) -> None:
        result = load_json(LONG_RESULT)
        rendered = render_report(result)
        for row in result["policy_by_remaining_opportunities"]:
            self.assertIn(f'<th scope="row">{row["remaining_opportunities"]}', rendered)
        self.assertIn("Complete stored horizon policy", rendered)

    def test_sequential_action_switch_information_is_present(self) -> None:
        rendered = render_report(load_json(LONG_RESULT))
        self.assertIn("Action-switch points", rendered)
        self.assertIn("changes from <strong>EXPLOIT</strong> to <strong>EXPLORE</strong>", rendered)

    def test_long_and_short_horizons_follow_stored_actions(self) -> None:
        long_html = render_report(load_json(LONG_RESULT))
        short_html = render_report(load_json(SHORT_RESULT))
        self.assertIn(">EXPLORE<", long_html)
        self.assertIn("8 remaining opportunities", long_html)
        self.assertIn(">EXPLOIT<", short_html)
        self.assertIn("2 remaining opportunities", short_html)

    def test_unavailable_exploration_is_explained(self) -> None:
        result = load_json(LONG_RESULT)
        result["explore_value"] = None
        result["action_advantage"] = None
        rendered = render_sequential_report(result, json.dumps(result))
        self.assertIn("Exploration is unavailable", rendered)
        self.assertIn("Unavailable", rendered)

    def test_validated_unavailable_exploration_report(self) -> None:
        model_data = load_json(EXAMPLES / "feynman-restaurant.json")
        model_data["state"]["unseen_options_remaining"] = 0
        validate_model_or_raise(model_data)
        result = analyze_model(model_from_validated_dict(model_data))
        rendered = render_report(result)
        self.assertEqual(result["recommendation_status"], "exploration_unavailable")
        self.assertIn("Exploration is unavailable", rendered)
        self.assertIn(">EXPLOIT<", rendered)

    def test_validated_indifferent_report_preserves_tie(self) -> None:
        model_data = load_json(EXAMPLES / "feynman-restaurant.json")
        model_data["state"]["best_known_value"] = 6.5
        model_data["new_option_distribution"] = {
            "minimum": 6.5,
            "most_likely": 6.5,
            "maximum": 6.5,
        }
        validate_model_or_raise(model_data)
        result = analyze_model(model_from_validated_dict(model_data))
        rendered = render_report(result)
        self.assertEqual(result["recommendation_status"], "indifferent")
        self.assertIn(">INDIFFERENT<", rendered)
        self.assertIn('class="status caution"', rendered)

    def test_svg_charts_are_accessibly_labelled(self) -> None:
        for result_path in (JOB_RESULT, LONG_RESULT):
            with self.subTest(result=result_path.name):
                rendered = render_report(load_json(result_path))
                self.assertIn('<svg class="chart', rendered)
                self.assertIn('role="img"', rendered)
                self.assertIn("aria-labelledby=", rendered)
                self.assertIn("<title id=", rendered)
                self.assertIn("<desc id=", rendered)

    def test_accessibility_references_resolve_to_unique_ids(self) -> None:
        for result_path in (JOB_RESULT, LONG_RESULT, SHORT_RESULT):
            with self.subTest(result=result_path.name):
                rendered = render_report(load_json(result_path))
                identifiers = re.findall(r'\bid="([^"]+)"', rendered)
                self.assertEqual(len(identifiers), len(set(identifiers)))
                for references in re.findall(r'aria-labelledby="([^"]+)"', rendered):
                    for identifier in references.split():
                        self.assertIn(identifier, identifiers)

    def test_every_chart_has_a_numerical_table_alternative(self) -> None:
        multi_html = render_report(load_json(JOB_RESULT))
        sequential_html = render_report(load_json(LONG_RESULT))
        self.assertIn("complete numerical uncertainty table", multi_html)
        self.assertIn("Numerical alternative to the contribution charts", multi_html)
        self.assertIn("every plotted horizon appears in the numerical policy table", sequential_html)

    def test_print_css_is_present(self) -> None:
        rendered = render_report(load_json(JOB_RESULT))
        self.assertIn("@media print", rendered)
        self.assertIn("@page", rendered)
        self.assertIn("details > .details-body { display: block; }", rendered)
        self.assertIn("section, table, .metric { break-inside: avoid; }", rendered)
        self.assertIn(CONDITIONALITY_STATEMENT, rendered)

    def test_reports_have_no_external_resources_or_scripts(self) -> None:
        for result_path in (JOB_RESULT, LONG_RESULT, SHORT_RESULT):
            with self.subTest(result=result_path.name):
                rendered = render_report(load_json(result_path)).lower()
                self.assertNotIn("http://", rendered)
                self.assertNotIn("https://", rendered)
                self.assertNotIn("<script", rendered)
                self.assertNotIn("src=", rendered)

    def test_reports_have_no_unresolved_template_placeholders(self) -> None:
        for result_path in (JOB_RESULT, LONG_RESULT, SHORT_RESULT):
            with self.subTest(result=result_path.name):
                rendered = render_report(load_json(result_path))
                self.assertNotIn("{{", rendered)
                self.assertNotIn("}}", rendered)
                self.assertNotIn("${", rendered)
                self.assertNotIn("__PLACEHOLDER__", rendered)

    def test_raw_source_json_is_safely_escaped(self) -> None:
        result = load_json(JOB_RESULT)
        attack = "<details open><script>bad()</script>"
        result["warnings"].append(attack)
        source = json.dumps(result, ensure_ascii=False, indent=2)
        rendered = render_report(result, source)
        self.assertIn("Raw audit data", rendered)
        self.assertIn(html.escape(source, quote=True), rendered)
        self.assertNotIn("<script>bad()", rendered)


class ReportFileAndCliTests(unittest.TestCase):
    def test_report_refuses_to_overwrite_its_source_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "result.json"
            original = JOB_RESULT.read_bytes()
            source.write_bytes(original)
            with self.assertRaisesRegex(ReportError, "must differ"):
                generate_report(source, source)
            self.assertEqual(source.read_bytes(), original)

    def test_malformed_field_is_rejected_without_cli_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            malformed = load_json(JOB_RESULT)
            malformed["alternative_results"][0]["win_probability"] = None
            source = root / "malformed.json"
            output = root / "report.html"
            source.write_text(json.dumps(malformed), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["report", str(source), "--output", str(output)])
            self.assertNotEqual(exit_code, 0)
            self.assertFalse(output.exists())
            self.assertIn("safely validated", stderr.getvalue())

    def test_source_json_line_endings_are_canonicalized_for_raw_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "result.json"
            crlf_text = JOB_RESULT.read_text(encoding="utf-8").replace("\n", "\r\n")
            source.write_bytes(crlf_text.encode("utf-8"))
            _, loaded_source = load_validated_result(source)
            self.assertNotIn("\r", loaded_source)
            self.assertEqual(loaded_source, JOB_RESULT.read_text(encoding="utf-8"))

    def test_crlf_source_cannot_change_generated_report_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lf_source = root / "lf.json"
            crlf_source = root / "crlf.json"
            source_text = JOB_RESULT.read_text(encoding="utf-8")
            lf_source.write_bytes(source_text.encode("utf-8"))
            crlf_source.write_bytes(source_text.replace("\n", "\r\n").encode("utf-8"))
            lf_report = root / "lf.html"
            crlf_report = root / "crlf.html"
            generate_report(lf_source, lf_report)
            generate_report(crlf_source, crlf_report)
            self.assertEqual(lf_report.read_bytes(), crlf_report.read_bytes())

    def test_generated_reports_use_lf_and_one_final_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "report.html"
            generate_report(JOB_RESULT, output)
            content = output.read_bytes()
            self.assertNotIn(b"\r", content)
            self.assertTrue(content.endswith(b"\n"))
            self.assertFalse(content.endswith(b"\n\n"))

    def test_result_writer_uses_lf_and_one_final_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "result.json"
            write_result_json(load_json(JOB_RESULT), output)
            content = output.read_bytes()
            self.assertNotIn(b"\r", content)
            self.assertTrue(content.endswith(b"\n"))
            self.assertFalse(content.endswith(b"\n\n"))

    def test_invalid_input_leaves_no_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            invalid = root / "invalid.json"
            output = root / "nested" / "report.html"
            invalid.write_text('{"model_type":"unsupported"}', encoding="utf-8")
            with self.assertRaises(ReportError):
                generate_report(invalid, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(root.rglob("*.tmp")))

    def test_cli_report_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "nested" / "report.html"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["report", str(JOB_RESULT), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("Report written:", stderr.getvalue())
            self.assertIn("No decision calculations were rerun", stderr.getvalue())

    def test_cli_report_failure_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            invalid = root / "invalid.json"
            output = root / "report.html"
            invalid.write_text("{}", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["report", str(invalid), "--output", str(output)])
            self.assertNotEqual(exit_code, 0)
            self.assertFalse(output.exists())
            self.assertIn("no partial report", stderr.getvalue())

    def test_open_flag_uses_default_browser_without_real_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "report.html"
            with patch("decision_architect.cli.webbrowser.open", return_value=True) as open_browser:
                exit_code = main(
                    ["report", str(JOB_RESULT), "--output", str(output), "--open"]
                )
            self.assertEqual(exit_code, 0)
            open_browser.assert_called_once_with(output.resolve().as_uri())

    def test_browser_open_error_is_contained_after_successful_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "report.html"
            stderr = io.StringIO()
            with patch(
                "decision_architect.cli.webbrowser.open",
                side_effect=webbrowser.Error("synthetic browser failure"),
            ), contextlib.redirect_stderr(stderr):
                exit_code = main(
                    ["report", str(JOB_RESULT), "--output", str(output), "--open"]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("browser could not open", stderr.getvalue())

    def test_demo_index_contains_all_relative_report_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = generate_demo_index(temporary_directory, OUTPUTS)
            rendered = output.read_text(encoding="utf-8")
            expected_links = (
                "job-choice-report.html",
                "feynman-restaurant-report.html",
                "feynman-restaurant-short-horizon-report.html",
                "university-transfer-report.html",
            )
            for link in expected_links:
                self.assertIn(f'href="{link}"', rendered)
            self.assertIn("Job Choice", rendered)
            self.assertIn("Feynman-inspired Dishes — 8 Visits", rendered)
            self.assertIn("Feynman-inspired Dishes — 2 Visits", rendered)
            self.assertIn("University Faculty Transfer", rendered)

    def test_two_independent_generations_of_every_report_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            for result_path in (JOB_RESULT, LONG_RESULT, SHORT_RESULT, UNIVERSITY_RESULT):
                with self.subTest(result=result_path.name):
                    first = Path(first_directory) / f"{result_path.stem}.html"
                    second = Path(second_directory) / f"{result_path.stem}.html"
                    generate_report(result_path, first)
                    generate_report(result_path, second)
                    self.assertEqual(first.read_bytes(), second.read_bytes())
            first_index = generate_demo_index(first_directory, OUTPUTS)
            second_index = generate_demo_index(second_directory, OUTPUTS)
            self.assertEqual(first_index.read_bytes(), second_index.read_bytes())

    def test_committed_and_regenerated_reports_are_byte_identical(self) -> None:
        report_names = {
            JOB_RESULT: "job-choice-report.html",
            LONG_RESULT: "feynman-restaurant-report.html",
            SHORT_RESULT: "feynman-restaurant-short-horizon-report.html",
            UNIVERSITY_RESULT: "university-transfer-report.html",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            for result_path, report_name in report_names.items():
                with self.subTest(result=result_path.name):
                    generated = Path(temporary_directory) / report_name
                    generate_report(result_path, generated)
                    self.assertEqual(
                        generated.read_bytes(),
                        (PROJECT_ROOT / "reports" / report_name).read_bytes(),
                    )

    def test_existing_analyze_output_remains_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "job-result.json"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                exit_code = main(
                    ["analyze", str(EXAMPLES / "job-choice.json"), "--output", str(output)]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(output.read_bytes(), JOB_RESULT.read_bytes())


if __name__ == "__main__":
    unittest.main()
