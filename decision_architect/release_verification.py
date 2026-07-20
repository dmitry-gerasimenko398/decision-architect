"""Offline, standard-library release verification and controlled clean copying."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .engine import analyze_file
from .reporting import generate_demo_index, generate_report
from .result_serialization import result_to_json_text, validate_result, write_result_json
from .validation import validate_model


RELEASE_VERSION = "1.0.0-rc3"
MODEL_VERSION = "1.0"
RESULT_VERSION = "1.0"
ENGINE_VERSION = "0.4.0"
REPORT_VERSION = "1.0.0-rc3"
MANIFEST_NAME = "RELEASE_MANIFEST.json"

ARTIFACTS = (
    ("job-choice.json", "job-choice-result.json", "job-choice-report.html"),
    (
        "feynman-restaurant.json",
        "feynman-restaurant-result.json",
        "feynman-restaurant-report.html",
    ),
    (
        "feynman-restaurant-short-horizon.json",
        "feynman-restaurant-short-horizon-result.json",
        "feynman-restaurant-short-horizon-report.html",
    ),
    (
        "university-transfer.json",
        "university-transfer-result.json",
        "university-transfer-report.html",
    ),
)

REQUIRED_FILES = {
    ".gitattributes",
    "VERSION",
    "README.md",
    "LICENSE",
    "RELEASE_CHECKLIST.md",
    "KNOWN_LIMITATIONS.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "PROJECT_SPEC.md",
    "ARCHITECTURE.md",
    "TODO.md",
    "AGENTS.md",
    "requirements.txt",
    "docs/QUICKSTART_WINDOWS.md",
    "docs/MATHEMATICAL_METHODS.md",
    "docs/CONTEST_DEMO.md",
    "docs/CODEX_USAGE.md",
    "docs/JUDGING_GUIDE.md",
    ".agents/skills/decision-analysis/SKILL.md",
    ".agents/skills/decision-analysis/agents/openai.yaml",
    "schemas/decision-model-v1.schema.json",
    "schemas/decision-result-v1.schema.json",
    "examples/conversations/feynman-restaurant-interview.md",
    "examples/conversations/university-transfer-interview.md",
    "reports/index.html",
}

PRIVATE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:^|[^A-Za-z])/" + "Users/", re.IGNORECASE),
    re.compile(r"(?:^|[^A-Za-z])/" + "home/", re.IGNORECASE),
    re.compile("file" + r":/{2,3}", re.IGNORECASE),
    re.compile(r"\\\\[A-Za-z0-9_.-]+[\\/]"),
)

PLACEHOLDER_PATTERNS = (
    "{{",
    "}}",
    "TODO_PLACEHOLDER",
    "REPLACE_ME",
    "YOUR_NAME_HERE",
    "FIXME_PLACEHOLDER",
)

REPORT_FORBIDDEN_PATTERNS = (
    "http://",
    "https://",
    "file:",
    "javascript:",
    "<script",
    "<iframe",
    "<object",
    "<embed",
    "<form",
    "<base",
    "srcset=",
    "@import",
    "url(",
    "http-equiv=\"refresh\"",
    "http-equiv='refresh'",
)

LF_TEXT_PATTERNS = (
    "*.py",
    "*.md",
    "*.json",
    "*.html",
    "*.css",
    "*.js",
    "*.yml",
    "*.yaml",
    "*.toml",
    "*.txt",
    "*.csv",
    "*.svg",
    "*.xml",
    "*.ini",
    "*.cfg",
    "*.ps1",
    "*.sh",
)

TEXT_SUFFIXES = {Path(pattern).suffix for pattern in LF_TEXT_PATTERNS}
GENERATED_TEXT_PREFIXES = ("outputs/", "reports/", "demo_sessions/")


class ReleaseVerificationError(ValueError):
    """Raised for an invalid release manifest or unsafe clean-copy request."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[CheckResult, ...]

    @property
    def success(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def test_count(self) -> int | None:
        for check in self.checks:
            if check.name == "complete unittest suite" and check.passed:
                match = re.search(r"(\d+) tests", check.detail)
                if match:
                    return int(match.group(1))
        return None


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_release_manifest(root: str | Path) -> tuple[str, ...]:
    root_path = Path(root).resolve()
    manifest_path = root_path / MANIFEST_NAME
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseVerificationError(f"Could not read {MANIFEST_NAME}: {error}") from error
    if not isinstance(value, dict) or value.get("release_version") != RELEASE_VERSION:
        raise ReleaseVerificationError(
            f"{MANIFEST_NAME} must declare release_version {RELEASE_VERSION}."
        )
    files = value.get("files")
    if not isinstance(files, list) or not files or not all(isinstance(item, str) for item in files):
        raise ReleaseVerificationError(f"{MANIFEST_NAME} files must be a non-empty string list.")
    normalized = tuple(item.replace("\\", "/") for item in files)
    if normalized != tuple(sorted(set(normalized))):
        raise ReleaseVerificationError(f"{MANIFEST_NAME} files must be sorted and unique.")
    for relative in normalized:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ReleaseVerificationError(f"Unsafe release path: {relative}")
        if relative == "sessions" or relative.startswith("sessions/"):
            raise ReleaseVerificationError("Working sessions/ must not appear in the release manifest.")
        source = root_path / candidate
        if not source.is_file():
            raise ReleaseVerificationError(f"Manifest file is missing: {relative}")
        current = source
        while current != root_path:
            if current.is_symlink():
                raise ReleaseVerificationError(f"Symlinks are not permitted in the release: {relative}")
            current = current.parent
    missing_required = sorted(REQUIRED_FILES - set(normalized))
    if missing_required:
        raise ReleaseVerificationError(
            "Required release files are absent from the manifest: " + ", ".join(missing_required)
        )
    return normalized


def create_clean_copy(root: str | Path, destination: str | Path) -> Path:
    root_path = Path(root).resolve()
    destination_path = Path(destination).resolve()
    if destination_path.exists() and any(destination_path.iterdir()):
        raise ReleaseVerificationError("Clean-copy destination must be empty.")
    destination_path.mkdir(parents=True, exist_ok=True)
    for relative in load_release_manifest(root_path):
        source = root_path / relative
        target = destination_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination_path


def _manifest_check(root: Path) -> str:
    files = load_release_manifest(root)
    if ".gitignore" not in files or MANIFEST_NAME not in files:
        raise ReleaseVerificationError("Manifest must include .gitignore and itself.")
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    if not re.search(r"(?m)^sessions/$", ignore):
        raise ReleaseVerificationError(".gitignore must ignore the entire sessions/ directory.")
    return f"{len(files)} explicitly allowlisted files; working sessions excluded"


def _line_ending_policy_check(root: Path) -> str:
    attributes = (root / ".gitattributes").read_text(encoding="utf-8")
    attribute_lines = {
        line.strip()
        for line in attributes.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = [
        pattern for pattern in LF_TEXT_PATTERNS if f"{pattern} text eol=lf" not in attribute_lines
    ]
    if missing:
        raise ReleaseVerificationError(
            ".gitattributes lacks canonical LF rules for: " + ", ".join(missing)
        )

    checked = 0
    generated = 0
    for relative in load_release_manifest(root):
        path = root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES and relative not in {
            ".gitattributes",
            ".gitignore",
            "VERSION",
        }:
            continue
        content = path.read_bytes()
        if b"\r" in content:
            raise ReleaseVerificationError(f"Non-canonical CR byte detected in {relative}.")
        checked += 1
        if relative.startswith(GENERATED_TEXT_PREFIXES):
            if not content.endswith(b"\n") or content.endswith(b"\n\n"):
                raise ReleaseVerificationError(
                    f"Generated text must end with exactly one LF newline: {relative}."
                )
            generated += 1
    return (
        f"{len(LF_TEXT_PATTERNS)} LF patterns enforced; {checked} release text files canonical; "
        f"{generated} generated files have one final LF"
    )


def _privacy_check(root: Path) -> str:
    files = load_release_manifest(root)
    checked = 0
    for relative in files:
        path = root / relative
        if path.suffix.lower() not in {".md", ".py", ".json", ".html", ".yaml", ".txt", ""}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATH_PATTERNS:
            if pattern.search(text):
                raise ReleaseVerificationError(f"Machine-specific path detected in {relative}.")
        checked += 1
    return f"{checked} release text files contain no obvious absolute user paths"


def _placeholder_check(root: Path) -> str:
    files = load_release_manifest(root)
    checked = 0
    for relative in files:
        if not (
            relative.endswith(".md")
            or relative.endswith(".html")
            or relative.endswith("SKILL.md")
            or relative.endswith("openai.yaml")
        ):
            continue
        text = (root / relative).read_text(encoding="utf-8")
        for marker in PLACEHOLDER_PATTERNS:
            if marker in text:
                raise ReleaseVerificationError(f"Unresolved placeholder {marker!r} in {relative}.")
        checked += 1
    return f"{checked} documentation, Skill, and report files contain no stale placeholders"


def _report_security_check(root: Path) -> str:
    report_files = sorted((root / "reports").glob("*.html"))
    if not report_files:
        raise ReleaseVerificationError("No release reports were found.")
    for path in report_files:
        text = html.unescape(path.read_text(encoding="utf-8")).lower()
        for marker in REPORT_FORBIDDEN_PATTERNS:
            if marker in text:
                raise ReleaseVerificationError(
                    f"Forbidden external or active report content {marker!r} in {path.name}."
                )
        if re.search(r"(?:src|href|action)\s*=\s*[\"']\s*//", text):
            raise ReleaseVerificationError(f"Scheme-relative report resource in {path.name}.")
        if re.search(r"<meta[^>]+http-equiv\s*=\s*[\"']?refresh", text):
            raise ReleaseVerificationError(f"Meta refresh in {path.name}.")
    return f"{len(report_files)} reports contain no external resources, active content, or file URLs"


def _read_constant(path: Path, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']", path.read_text(encoding="utf-8"))
    if not match:
        raise ReleaseVerificationError(f"Could not find {name} in {path}.")
    return match.group(1)


def _version_check(root: Path) -> str:
    if (root / "VERSION").read_text(encoding="utf-8").strip() != RELEASE_VERSION:
        raise ReleaseVerificationError("VERSION is inconsistent.")
    if _read_constant(root / "decision_architect" / "__init__.py", "__version__") != RELEASE_VERSION:
        raise ReleaseVerificationError("Package version is inconsistent.")
    if _read_constant(root / "decision_architect" / "report_templates.py", "REPORT_GENERATOR_VERSION") != REPORT_VERSION:
        raise ReleaseVerificationError("Report generator version is inconsistent.")
    skill = (root / ".agents" / "skills" / "decision-analysis" / "SKILL.md").read_text(encoding="utf-8")
    if f"Release version: `{RELEASE_VERSION}`" not in skill:
        raise ReleaseVerificationError("Skill release version is inconsistent.")
    model_schema = json.loads((root / "schemas" / "decision-model-v1.schema.json").read_text(encoding="utf-8"))
    result_schema = json.loads((root / "schemas" / "decision-result-v1.schema.json").read_text(encoding="utf-8"))
    if model_schema["$defs"]["baseModel"]["properties"]["model_version"]["const"] != MODEL_VERSION:
        raise ReleaseVerificationError("Model contract version changed unexpectedly.")
    result_properties = result_schema["$defs"]["baseResult"]["properties"]
    if (
        result_properties["result_version"]["const"] != RESULT_VERSION
        or result_properties["model_version"]["const"] != MODEL_VERSION
    ):
        raise ReleaseVerificationError("Result contract version changed unexpectedly.")
    for _, result_name, _ in ARTIFACTS:
        result = json.loads((root / "outputs" / result_name).read_text(encoding="utf-8"))
        if (
            result.get("result_version") != RESULT_VERSION
            or result.get("model_version") != MODEL_VERSION
            or result.get("engine_version") != ENGINE_VERSION
        ):
            raise ReleaseVerificationError(f"Stored component versions are inconsistent in {result_name}.")
    return (
        f"release {RELEASE_VERSION}; contracts {MODEL_VERSION}/{RESULT_VERSION}; "
        f"engine {ENGINE_VERSION}; report {REPORT_VERSION}"
    )


def _skill_check(root: Path) -> str:
    skill_root = root / ".agents" / "skills" / "decision-analysis"
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    lines = skill_text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ReleaseVerificationError("Skill frontmatter delimiters are invalid.")
    closing = lines.index("---", 1)
    frontmatter = lines[1:closing]
    if len(frontmatter) != 2 or frontmatter[0] != "name: decision-analysis":
        raise ReleaseVerificationError("Skill frontmatter must contain only name and description.")
    references = sorted(set(re.findall(r"references/[a-z0-9-]+\.md", skill_text)))
    for reference in references:
        if not (skill_root / reference).is_file():
            raise ReleaseVerificationError(f"Skill reference is missing: {reference}")
    ui_text = (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "$decision-analysis" not in ui_text:
        raise ReleaseVerificationError("Skill UI prompt does not contain exact invocation.")
    readme = (root / "README.md").read_text(encoding="utf-8")
    if "$decision-analysis" not in readme:
        raise ReleaseVerificationError("README does not document exact Skill invocation.")
    friendly_phrases = (
        "I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it.",
        "Your model is ready for review. No recommendation has been calculated yet.",
        "Model confirmed. I’ve now run the deterministic analysis and generated your report.",
    )
    for phrase in friendly_phrases:
        if phrase not in skill_text:
            raise ReleaseVerificationError(f"Skill is missing approved user-facing wording: {phrase}")
    return f"valid concise Skill structure with {len(references)} existing references"


def _documentation_check(root: Path) -> str:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            raise ReleaseVerificationError(f"Required release file is missing: {relative}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    readme_lower = readme.lower()
    required_phrases = (
        "No API key",
        "Start here — use Decision Architect in three steps",
        "Download ZIP",
        "$decision-analysis",
        "CONFIRM",
        "No separate Skill installation is required for the supported contest workflow",
        "The complete repository is required",
        "Optional advanced Python CLI",
        "docs/QUICKSTART_WINDOWS.md",
        "reports/index.html",
        "Generated-artifact policy",
        "py -m decision_architect verify-release",
        "probability that the real-life decision will succeed",
    )
    for phrase in required_phrases:
        if phrase.lower() not in readme_lower:
            raise ReleaseVerificationError(f"README is missing required release text: {phrase}")

    quickstart = (root / "docs" / "QUICKSTART_WINDOWS.md").read_text(encoding="utf-8")
    quickstart_phrases = (
        "Download ZIP",
        "complete repository",
        "No separate Skill installation is required",
        "$decision-analysis",
        "CONFIRM",
        "sessions\\<decision-name>\\report.html",
        "py -m decision_architect verify-release",
        "replace `py` with `python`",
        "No API key",
        "No additional Python package",
    )
    for phrase in quickstart_phrases:
        if phrase.lower() not in quickstart.lower():
            raise ReleaseVerificationError(f"Windows quickstart is missing: {phrase}")

    codex_usage = (root / "docs" / "CODEX_USAGE.md").read_text(encoding="utf-8")
    codex_usage_phrases = (
        "repository-scoped Skill",
        "complete Decision Architect repository",
        "Downloading only the Skill folder is not the supported complete workflow",
        "exact reply `CONFIRM` before calculation",
        "Python is responsible for authoritative numerical calculations",
        "Direct Python CLI commands are optional",
    )
    for phrase in codex_usage_phrases:
        if phrase.lower() not in codex_usage.lower():
            raise ReleaseVerificationError(f"Codex usage documentation is missing: {phrase}")
    cli_source = (root / "decision_architect" / "cli.py").read_text(encoding="utf-8")
    for command in ("analyze", "report", "report-index", "verify-release"):
        if f'add_parser(\n        "{command}"' not in cli_source and f'add_parser("{command}"' not in cli_source:
            raise ReleaseVerificationError(f"README command has no CLI parser: {command}")
    limitations = (root / "KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")
    if "not implemented" not in limitations or "Bayesian networks" not in limitations:
        raise ReleaseVerificationError("Future dependency-aware modes are not truthfully documented.")
    return "first-time workflow, release documents, commands, policies, and limitations are present"


def _artifact_check(root: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="decision-architect-release-") as temporary:
        temporary_root = Path(temporary)
        generated_reports = temporary_root / "reports"
        generated_reports.mkdir()
        for model_name, result_name, report_name in ARTIFACTS:
            model_path = root / "examples" / model_name
            model = json.loads(model_path.read_text(encoding="utf-8"))
            model_issues = validate_model(model)
            if model_issues:
                raise ReleaseVerificationError(f"Invalid model {model_name}: {model_issues[0]}")
            result = analyze_file(model_path)
            result_text = result_to_json_text(result)
            expected_result = root / "outputs" / result_name
            generated_result = temporary_root / "outputs" / result_name
            write_result_json(result, generated_result)
            if generated_result.read_bytes() != expected_result.read_bytes():
                raise ReleaseVerificationError(f"Regenerated result differs: {result_name}")
            if validate_result(json.loads(result_text)):
                raise ReleaseVerificationError(f"Generated result does not validate: {result_name}")
            generated_report = generated_reports / report_name
            generate_report(expected_result, generated_report)
            if generated_report.read_bytes() != (root / "reports" / report_name).read_bytes():
                raise ReleaseVerificationError(f"Regenerated report differs: {report_name}")
        generated_index = generate_demo_index(generated_reports, root / "outputs")
        if generated_index.read_bytes() != (root / "reports" / "index.html").read_bytes():
            raise ReleaseVerificationError("Regenerated report index differs.")

        from scripts.generate_demo_sessions import generate

        generated_sessions = temporary_root / "demo_sessions"
        generate(generated_sessions, project_root=root)
        expected_sessions = root / "demo_sessions"
        expected_files = sorted(
            path.relative_to(expected_sessions).as_posix()
            for path in expected_sessions.rglob("*")
            if path.is_file()
        )
        actual_files = sorted(
            path.relative_to(generated_sessions).as_posix()
            for path in generated_sessions.rglob("*")
            if path.is_file()
        )
        if actual_files != expected_files:
            raise ReleaseVerificationError("Regenerated demo-session file inventory differs.")
        for relative in expected_files:
            if (generated_sessions / relative).read_bytes() != (expected_sessions / relative).read_bytes():
                raise ReleaseVerificationError(f"Regenerated demo-session artifact differs: {relative}")
    return "4 models, 4 results, 4 reports, index, and 18 demo-session files reproduce exactly"


def _acceptance_check(root: Path) -> str:
    sequential = json.loads(
        (root / "outputs" / "feynman-restaurant-result.json").read_text(encoding="utf-8")
    )
    if abs(sequential["explore_value"] - 57.53818075244744) > 1e-12:
        raise ReleaseVerificationError("Sequential explore value changed.")
    if abs(sequential["exploit_value"] - 56.25327198359611) > 1e-12:
        raise ReleaseVerificationError("Sequential exploit value changed.")
    switches = sequential["action_switch_points"]
    if not any(item["remaining_opportunities"] == 3 for item in switches):
        raise ReleaseVerificationError("Sequential switch at three is missing.")

    university = json.loads(
        (root / "outputs" / "university-transfer-result.json").read_text(encoding="utf-8")
    )
    by_id = {item["alternative_id"]: item for item in university["alternative_results"]}
    expected = {
        "postpone": (0.6899506869091862, 0.8549),
        "transfer_now": (0.636820030565787, 0.1435),
        "stay": (0.5786658303516664, 0.0016),
    }
    for alternative_id, (mean, wins) in expected.items():
        item = by_id.get(alternative_id, {})
        if (
            abs(item.get("monte_carlo_mean_utility", -1) - mean) > 1e-12
            or abs(item.get("win_probability", -1) - wins) > 1e-12
        ):
            raise ReleaseVerificationError(f"University acceptance value changed: {alternative_id}")
    information = next(
        item
        for item in university["sensitivity"]["criteria"]
        if item["criterion_id"] == "information_reversibility"
    )
    if abs(information["lower_switch"]["threshold_weight"] - 0.026180015077200885) > 1e-12:
        raise ReleaseVerificationError("University sensitivity switch changed.")
    transcript = (root / "examples" / "conversations" / "university-transfer-interview.md").read_text(
        encoding="utf-8"
    )
    if "sanitized" not in transcript.lower() or "full-horizon" not in transcript:
        raise ReleaseVerificationError("Sanitized university acceptance description is incomplete.")
    return "both live acceptance results and the postponement limitation are preserved"


def _presentation_check(root: Path) -> str:
    university = (root / "reports" / "university-transfer-report.html").read_text(encoding="utf-8")
    lower = university.lower()
    contribution_start = lower.index('aria-labelledby="contributions-heading"')
    constraint_start = lower.index('aria-labelledby="constraints-heading"')
    sensitivity_start = lower.index('aria-labelledby="sensitivity-heading"')
    contribution_section = lower[contribution_start:constraint_start]
    constraint_section = lower[constraint_start:sensitivity_start]
    sensitivity_end = lower.index("</section>", sensitivity_start)
    sensitivity_section = lower[sensitivity_start:sensitivity_end]
    if "near home compatibility" in contribution_section or "near home compatibility" in sensitivity_section:
        raise ReleaseVerificationError(
            "Near-home zero-weight indicator is presented as an ordinary weighted preference."
        )
    if "near home compatibility" not in constraint_section:
        raise ReleaseVerificationError("Near-home zero-weight indicator is missing from Hard Constraints.")
    if "what win probability means" not in lower:
        raise ReleaseVerificationError("University report lacks the win-probability explanation.")
    recommendation_end = lower.index("</section>", lower.index('aria-labelledby="recommendation-heading"'))
    if "full comparison horizon" not in lower[:recommendation_end]:
        raise ReleaseVerificationError("Postponement approximation is not prominent in the report.")
    job = (root / "reports" / "job-choice-report.html").read_text(encoding="utf-8").lower()
    if "not the probability that the real-life decision will succeed" not in job:
        raise ReleaseVerificationError("Job report lacks the win-probability distinction.")
    return "zero-weight indicator, win-frequency explanation, and staged-choice warning are correct"


def _tests_check(root: Path) -> str:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    combined = process.stdout + "\n" + process.stderr
    if process.returncode != 0:
        raise ReleaseVerificationError("Complete unittest suite failed:\n" + combined[-2000:])
    match = re.search(r"Ran (\d+) tests", combined)
    if not match:
        raise ReleaseVerificationError("Could not determine unittest count.")
    return f"{match.group(1)} tests passed"


def verify_release(root: str | Path | None = None, *, run_tests: bool = True) -> VerificationReport:
    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        initial_files = load_release_manifest(root_path)
        initial_hashes = {relative: _sha256(root_path / relative) for relative in initial_files}
    except Exception:
        initial_hashes = {}

    checks: list[CheckResult] = []

    def run(name: str, function: Callable[[Path], str]) -> None:
        try:
            detail = function(root_path)
        except Exception as error:
            checks.append(CheckResult(name, False, str(error)))
        else:
            checks.append(CheckResult(name, True, detail))

    run("release manifest and working-session policy", _manifest_check)
    run("canonical LF checkout and generated-text policy", _line_ending_policy_check)
    run("privacy and machine-path scan", _privacy_check)
    run("unresolved placeholder scan", _placeholder_check)
    run("report security and external resources", _report_security_check)
    run("version consistency", _version_check)
    run("Skill structure and invocation", _skill_check)
    run("documentation and CLI surface", _documentation_check)
    run("deterministic generated artifacts", _artifact_check)
    run("live acceptance mathematics", _acceptance_check)
    run("release presentation requirements", _presentation_check)
    if run_tests:
        run("complete unittest suite", _tests_check)

    if initial_hashes:
        changed = [
            relative
            for relative, digest in initial_hashes.items()
            if not (root_path / relative).is_file() or _sha256(root_path / relative) != digest
        ]
        checks.append(
            CheckResult(
                "source artifacts unchanged by verification",
                not changed,
                "no allowlisted source bytes changed" if not changed else ", ".join(changed),
            )
        )
    return VerificationReport(tuple(checks))


def format_verification_report(report: VerificationReport) -> str:
    lines = []
    for check in report.checks:
        marker = "PASS" if check.passed else "FAIL"
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    lines.append("Release verification PASSED." if report.success else "Release verification FAILED.")
    return "\n".join(lines) + "\n"
