"""Command-line behavior tests for both calculation engines."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from decision_architect.cli import main
from decision_architect.result_serialization import (
    validate_multi_criteria_result,
    validate_sequential_exploration_result,
)
from decision_architect.sequential_exploration import SequentialCalculationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_EXAMPLE = PROJECT_ROOT / "examples" / "job-choice.json"
LONG_EXAMPLE = PROJECT_ROOT / "examples" / "feynman-restaurant.json"


class CliTests(unittest.TestCase):
    def test_cli_success_path_writes_valid_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "result.json"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(["analyze", str(JOB_EXAMPLE), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(validate_multi_criteria_result(result), [])
            self.assertIn("Recommendation status: recommended", stderr.getvalue())
            self.assertIn("Closest winner switch", stderr.getvalue())
            self.assertIn("salary", stderr.getvalue())
            self.assertIn("Stable corporation", stderr.getvalue())

    def test_sequential_cli_success_path_writes_valid_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "sequential-result.json"
            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                exit_code = main(["analyze", str(LONG_EXAMPLE), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(validate_sequential_exploration_result(result), [])
            self.assertIn("Recommendation status: explore_preferred", stderr.getvalue())

    def test_sequential_validation_error_returns_nonzero_without_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid = Path(temporary_directory) / "invalid-sequential.json"
            data = json.loads(LONG_EXAMPLE.read_text(encoding="utf-8"))
            data["analysis_settings"]["quadrature_points"] = 100
            invalid.write_text(json.dumps(data), encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(["analyze", str(invalid)])
            self.assertNotEqual(exit_code, 0)
            self.assertIn("invalid_quadrature_points", stderr.getvalue())
            self.assertIn("no recommendation was produced", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")

    def test_no_result_file_is_written_after_calculation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "must-not-exist.json"
            stderr = io.StringIO()
            with patch(
                "decision_architect.cli.analyze_file",
                side_effect=SequentialCalculationError("synthetic calculation failure"),
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                exit_code = main(["analyze", str(LONG_EXAMPLE), "--output", str(output)])
            self.assertNotEqual(exit_code, 0)
            self.assertFalse(output.exists())
            self.assertIn("no recommendation was produced", stderr.getvalue())

    def test_cli_validation_error_path_has_no_fake_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid = Path(temporary_directory) / "invalid.json"
            invalid.write_text('{"model_type": "multi_criteria"}', encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(["analyze", str(invalid)])
            self.assertNotEqual(exit_code, 0)
            self.assertIn("Validation failed", stderr.getvalue())
            self.assertIn("no recommendation was produced", stderr.getvalue())
            self.assertNotIn("Recommendation status:", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
