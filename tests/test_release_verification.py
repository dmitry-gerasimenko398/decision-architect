"""Release-candidate verification tests for the complete local package."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from decision_architect.release_verification import (
    ENGINE_VERSION,
    MANIFEST_NAME,
    MODEL_VERSION,
    RELEASE_VERSION,
    REPORT_VERSION,
    RESULT_VERSION,
    ReleaseVerificationError,
    _documentation_check,
    _placeholder_check,
    _privacy_check,
    _report_security_check,
    _skill_check,
    _version_check,
    create_clean_copy,
    format_verification_report,
    load_release_manifest,
    verify_release,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = verify_release(PROJECT_ROOT, run_tests=False)

    def clean_copy(self, parent: str) -> Path:
        destination = Path(parent) / "decision-architect-1.0.0-rc1"
        return create_clean_copy(PROJECT_ROOT, destination)

    def test_core_release_verification_passes(self) -> None:
        self.assertTrue(self.report.success, format_verification_report(self.report))

    def test_verifier_reports_at_least_ten_independent_checks(self) -> None:
        self.assertGreaterEqual(len(self.report.checks), 10)
        self.assertEqual(len({check.name for check in self.report.checks}), len(self.report.checks))

    def test_manifest_is_sorted_unique_and_explicit(self) -> None:
        files = load_release_manifest(PROJECT_ROOT)
        self.assertEqual(files, tuple(sorted(set(files))))
        self.assertIn(MANIFEST_NAME, files)

    def test_manifest_excludes_working_sessions(self) -> None:
        files = load_release_manifest(PROJECT_ROOT)
        self.assertFalse(any(path == "sessions" or path.startswith("sessions/") for path in files))

    def test_manifest_rejects_a_working_session_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            manifest = json.loads((clean / MANIFEST_NAME).read_text(encoding="utf-8"))
            manifest["files"].append("sessions/private.json")
            manifest["files"].sort()
            (clean / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "Working sessions"):
                load_release_manifest(clean)

    def test_clean_copy_contains_only_allowlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            actual = sorted(
                path.relative_to(clean).as_posix()
                for path in clean.rglob("*")
                if path.is_file()
            )
            self.assertEqual(actual, list(load_release_manifest(PROJECT_ROOT)))
            self.assertFalse((clean / "sessions").exists())
            self.assertFalse(any("__pycache__" in path.parts for path in clean.rglob("*")))

    def test_clean_copy_passes_core_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            report = verify_release(clean, run_tests=False)
            self.assertTrue(report.success, format_verification_report(report))

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            (clean / "README.md").unlink()
            with self.assertRaisesRegex(ReleaseVerificationError, "missing"):
                load_release_manifest(clean)

    def test_machine_specific_windows_path_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            readme = clean / "README.md"
            separator = chr(92)
            private_path = "C:" + separator + "Users" + separator + "Example" + separator + "secret"
            readme.write_text(readme.read_text(encoding="utf-8") + f"\n{private_path}\n", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "Machine-specific"):
                _privacy_check(clean)

    def test_file_uri_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            readme = clean / "README.md"
            private_uri = "file" + ":///private/report.html"
            readme.write_text(readme.read_text(encoding="utf-8") + f"\n{private_uri}\n", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "Machine-specific"):
                _privacy_check(clean)

    def test_unresolved_placeholder_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            readme = clean / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nREPLACE_ME\n", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "placeholder"):
                _placeholder_check(clean)

    def test_external_report_resource_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            report = clean / "reports" / "job-choice-report.html"
            report.write_text(report.read_text(encoding="utf-8") + '<img src="https://example.invalid/x.png">', encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "Forbidden external"):
                _report_security_check(clean)

    def test_active_report_script_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            report = clean / "reports" / "job-choice-report.html"
            report.write_text(report.read_text(encoding="utf-8") + "<script>alert(1)</script>", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "active report content"):
                _report_security_check(clean)

    def test_release_and_component_versions_are_intentionally_distinct(self) -> None:
        self.assertEqual(RELEASE_VERSION, "1.0.0-rc1")
        self.assertEqual(REPORT_VERSION, "1.0.0-rc1")
        self.assertEqual((MODEL_VERSION, RESULT_VERSION, ENGINE_VERSION), ("1.0", "1.0", "0.4.0"))
        self.assertIn("release 1.0.0-rc1", _version_check(PROJECT_ROOT))

    def test_inconsistent_package_version_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clean = self.clean_copy(temporary)
            init = clean / "decision_architect" / "__init__.py"
            init.write_text(init.read_text(encoding="utf-8").replace("1.0.0-rc1", "9.9.9"), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseVerificationError, "Package version"):
                _version_check(clean)

    def test_skill_structure_and_exact_invocation_pass(self) -> None:
        detail = _skill_check(PROJECT_ROOT)
        self.assertIn("existing references", detail)

    def test_approved_confirmation_gate_wording_is_preserved(self) -> None:
        skill = (PROJECT_ROOT / ".agents" / "skills" / "decision-analysis" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        cli = (PROJECT_ROOT / "decision_architect" / "cli.py").read_text(encoding="utf-8")
        phrases = (
            "I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it.",
            "Your model is ready for review. No recommendation has been calculated yet.",
        )
        for phrase in phrases:
            self.assertIn(phrase, skill)
        self.assertIn("I've started a draft decision model.", cli)
        self.assertIn("I won't calculate a recommendation until ", cli)
        self.assertIn("Your model is ready for review. No recommendation has been calculated yet.", cli)
        self.assertIn(
            "Model confirmed. I’ve now run the deterministic analysis and generated your report.",
            skill,
        )

    def test_readme_commands_and_release_documents_pass(self) -> None:
        self.assertIn("required release documents", _documentation_check(PROJECT_ROOT))

    def test_working_sessions_are_ignored_by_git_policy(self) -> None:
        ignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertRegex(ignore, r"(?m)^sessions/$")

    def test_demo_session_artifacts_have_no_machine_paths(self) -> None:
        for path in (PROJECT_ROOT / "demo_sessions").rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"[A-Za-z]:[\\/]Users[\\/]")
                self.assertNotIn("file" + ":///", text.lower())

    def test_reports_explain_win_probability_conditionally(self) -> None:
        for name in ("job-choice-report.html", "university-transfer-report.html"):
            text = (PROJECT_ROOT / "reports" / name).read_text(encoding="utf-8").lower()
            self.assertIn("not the probability that the real-life decision will succeed", text)
            self.assertIn("based on the user’s stated", text)

    def test_zero_weight_near_home_indicator_is_not_a_weighted_contribution(self) -> None:
        text = (PROJECT_ROOT / "reports" / "university-transfer-report.html").read_text(encoding="utf-8").lower()
        contribution_start = text.index('aria-labelledby="contributions-heading"')
        constraint_start = text.index('aria-labelledby="constraints-heading"')
        sensitivity_start = text.index('aria-labelledby="sensitivity-heading"')
        self.assertNotIn("near home compatibility", text[contribution_start:constraint_start])
        self.assertIn("near home compatibility", text[constraint_start:sensitivity_start])

    def test_dependency_aware_future_modes_are_not_claimed_as_implemented(self) -> None:
        limitations = (PROJECT_ROOT / "KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")
        methods = (PROJECT_ROOT / "docs" / "MATHEMATICAL_METHODS.md").read_text(encoding="utf-8")
        self.assertIn("not implemented", limitations)
        self.assertIn("not implemented", methods)
        self.assertIn("Bayesian", limitations)

    def test_verification_does_not_change_allowlisted_bytes(self) -> None:
        files = load_release_manifest(PROJECT_ROOT)
        before = {relative: (PROJECT_ROOT / relative).read_bytes() for relative in files}
        verify_release(PROJECT_ROOT, run_tests=False)
        after = {relative: (PROJECT_ROOT / relative).read_bytes() for relative in files}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
