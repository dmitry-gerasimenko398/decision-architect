# Decision Architect

**Release candidate:** `1.0.0-rc3` · **OpenAI Build Week project**

Decision Architect is **a reusable Codex Skill with an adaptive interview, deterministic Python decision engine, validated JSON contracts, and self-contained local HTML reports**.

It turns an informal personal decision into a reviewable mathematical model, then explains which option is preferable under the user’s stated preferences, estimates, constraints, time horizon, and assumptions. It does not claim to discover an objectively correct life decision.

## Start here — use Decision Architect in three steps

### Requirements

- The Codex app.
- Python 3.12 or a compatible Python 3 installation.
- No API key.
- No external backend.
- No additional Python packages.

### 1. Download the complete project

**Option A — no Git required:**

1. On the [GitHub repository page](https://github.com/dmitry-gerasimenko398/decision-architect), select **Code**.
2. Select **Download ZIP**.
3. Extract the downloaded archive.
4. Keep the full folder structure intact.

**Option B — with Git:**

```powershell
git clone https://github.com/dmitry-gerasimenko398/decision-architect.git
```

The complete repository is required because the Skill uses the included deterministic Python engine, schemas, validation, and report generator. Downloading only the Skill folder is not the supported complete workflow for this release.

### 2. Open the project in Codex

Open the extracted or cloned `decision-architect` folder as the current Codex project.

> **No separate Skill installation is required for the supported contest workflow.** Codex discovers the repository-scoped Skill from `.agents/skills/decision-analysis/` when the repository root is opened as the project.

### 3. Start a decision

Type:

```text
$decision-analysis
```

Then describe the decision in ordinary language. Codex selects one of the two supported model structures, asks adaptive follow-up questions, and prepares a complete proposed model for review. Ordinary Skill users do not need JSON knowledge.

No recommendation is calculated until you review the complete model and reply exactly:

```text
CONFIRM
```

After confirmation, deterministic Python validates the model, performs the numerical analysis, saves JSON results, and generates a local HTML report.

- [Beginner Windows guide](docs/QUICKSTART_WINDOWS.md)
- [Browse example reports](reports/index.html)
- [See the contest demonstration](docs/CONTEST_DEMO.md)
- [Read the mathematical methods](docs/MATHEMATICAL_METHODS.md)

## Recommended ordinary workflow

1. Download the complete repository.
2. Open the repository root in Codex.
3. Invoke `$decision-analysis`.
4. Describe the decision normally.
5. Answer the adaptive questions.
6. Review the proposed model.
7. Reply exactly `CONFIRM`.
8. Open the generated report.

## What you are downloading

| Directory | Purpose |
|---|---|
| `.agents/skills/decision-analysis/` | Repository-scoped adaptive Codex Skill |
| `decision_architect/` | Deterministic standard-library Python engine |
| `schemas/` | Validated, versioned JSON contracts |
| `examples/` | Example confirmed decision models |
| `outputs/` | Stored deterministic result JSON |
| `reports/` | Self-contained local HTML reports |
| `demo_sessions/` | Sanitized end-to-end demonstration sessions |
| `docs/` | Beginner, contest, usage, and mathematical guides |
| `tests/` | Automated standard-library test suite |

Local working sessions are stored under `sessions/`. That directory can contain personal decision details, so it is intentionally ignored and excluded from the public repository.

## First-time user FAQ

### Do I install the Skill separately?

No separate installation is required for the supported repository-scoped workflow. Download the complete repository and open its root folder in Codex.

### Can I download only the Skill folder?

That is not the supported complete workflow for this release. The Skill relies on the included Python engine, schemas, validation, and report generation files.

### Do I need an OpenAI API key?

No API key is required for the contest version.

### Do I need to run the Python commands manually?

Not for ordinary Skill use. The commands are provided for developers, reviewers, and manual verification.

### Is the recommendation objectively correct?

No. It is conditional decision support based on the user-confirmed preferences, estimates, constraints, time horizon, and assumptions.

## Problem, solution, and difference

Personal decisions often mix hard requirements, preferences, uncertainty, and time. A conversational answer can hide assumptions; a spreadsheet can be difficult to structure correctly.

Decision Architect combines:

- A natural-language Codex interview that asks only relevant questions.
- An exact review and `CONFIRM` gate before any recommendation is calculated.
- Deterministic, reproducible Python calculations rather than language-model arithmetic.
- Saved JSON inputs and outputs that make every result auditable.
- Accessible standalone HTML reports with uncertainty and sensitivity information.

The interview and mathematics are intentionally separate: Codex interprets and structures; Python validates and calculates.

## Supported decisions

| Model | Use it for | Main output |
|---|---|---|
| `multi_criteria` | One-time choices among 2–4 known alternatives with several weighted criteria and optional hard constraints | Expected weighted utility, Monte Carlo summaries, simulated win frequency, exclusions, and weight-switch sensitivity |
| `sequential_exploration` | Finite repeated explore-versus-exploit choices where a good discovery can be reused | Explore/exploit action values, recommended current action, complete horizon policy, and action switches |

Continuous portfolio allocation, negotiation, voting, open-ended planning, correlated-uncertainty modeling, Bayesian networks, influence diagrams, and general optimization are not implemented.

## Architecture

```text
natural-language decision
        ↓
Codex Skill: model selection + adaptive interview
        ↓
proposed model → validation → complete review → exact CONFIRM
        ↓
confirmed decision-model-v1 JSON
        ↓
deterministic Python engine
        ↓
validated decision-result-v1 JSON
        ↓
self-contained local HTML report + conditional explanation
```

## Optional advanced Python CLI

Ordinary Skill users do not need to run these commands or understand JSON. The direct CLI is available for developers, reviewers, and people who want to inspect or reproduce existing model files manually.

- **Codex workflow:** structures the conversation, maintains the draft, enforces confirmation, and invokes the deterministic tools.
- **Direct Python CLI:** validates existing JSON models, runs analysis, generates reports, and verifies the release.
- **Stored result JSON:** remains the authoritative machine-readable calculation output.
- **HTML report:** presents an already-saved validated result and never reruns the mathematics.

The standard-library code was verified with Python 3.12. From PowerShell in the repository root, run verification with:

```powershell
py -m decision_architect verify-release
py -m unittest discover -s tests -v
```

If `py` is unavailable but `python` works, replace `py` with `python`. If neither command works, see the non-machine-specific fallback in [Windows Quickstart](docs/QUICKSTART_WINDOWS.md); do not copy a Python path from another computer.

Optionally analyze and report the released examples:

```powershell
py -m decision_architect analyze examples\job-choice.json --output outputs\job-choice-result.json
py -m decision_architect analyze examples\feynman-restaurant.json --output outputs\feynman-restaurant-result.json
py -m decision_architect analyze examples\feynman-restaurant-short-horizon.json --output outputs\feynman-restaurant-short-horizon-result.json
py -m decision_architect analyze examples\university-transfer.json --output outputs\university-transfer-result.json

py -m decision_architect report outputs\job-choice-result.json --output reports\job-choice-report.html
py -m decision_architect report outputs\feynman-restaurant-result.json --output reports\feynman-restaurant-report.html
py -m decision_architect report outputs\feynman-restaurant-short-horizon-result.json --output reports\feynman-restaurant-short-horizon-report.html
py -m decision_architect report outputs\university-transfer-result.json --output reports\university-transfer-report.html
py -m decision_architect report-index reports --results-dir outputs
```

Rebuild the three sanitized end-to-end demo sessions:

```powershell
py -m scripts.generate_demo_sessions
```

Open [reports/index.html](reports/index.html) by double-clicking it in File Explorer. The reports need no server and load no external resources.

## Demonstrated results

- **Job choice:** Remote startup leads under the fictional confirmed inputs; the report shows uncertainty, a salary constraint exclusion, and weight sensitivity.
- **Feynman-inspired dish choice:** EXPLORE at eight visits; EXPLOIT at one–two visits; policy switch at three.
- **Sanitized university acceptance test:** Postpone for one semester has mean utility about `0.6900` and simulated win frequency `85.49%`; Transfer now becomes the leader if the information-and-reversibility weight falls below about `0.02618`.

Simulated win probability means the fraction of modeled Monte Carlo scenarios in which an alternative ranked first. It is **not** the probability that the real-life decision will succeed.

See [Contest Demo](docs/CONTEST_DEMO.md) and [Judging Guide](docs/JUDGING_GUIDE.md).

## Mathematical transparency

The implementation records formulas, model assumptions, seeds, methods, warnings, intermediate summaries, and sensitivity thresholds. See:

- [Mathematical Methods](docs/MATHEMATICAL_METHODS.md)
- [Project Specification](PROJECT_SPEC.md)
- [Architecture](ARCHITECTURE.md)
- [Input schema](schemas/decision-model-v1.schema.json)
- [Result schema](schemas/decision-result-v1.schema.json)

Multi-criteria uncertainties are sampled independently in the MVP. Future work may investigate validated correlation matrices, copulas, Bayesian networks, or influence diagrams, but none of those features is implemented in this release.

## Generated-artifact policy

The intended release includes sanitized example models, deterministic result JSON, standalone HTML reports, the report index, transcripts, and the three explicitly sanitized `demo_sessions/` records.

The release excludes arbitrary `sessions/`, caches, bytecode, temporary files, editor metadata, local review PDFs, browser artifacts, secrets, and duplicate verification copies. The release verifier uses an explicit allowlist and a controlled clean copy rather than assuming every unignored file is public.

Browser print-to-PDF headers or footers can display a local file path even though the HTML source contains none. Disable browser headers and footers when intentionally printing a report.

## Safety and limitations

- Recommendations are conditional decision support, not medical, legal, financial, educational, or safety advice.
- Utility anchors, weights, estimates, and hard constraints remain subjective user inputs.
- Triangular distributions and independent sampling are approximations.
- One-at-a-time sensitivity does not vary several weights simultaneously.
- Sequential exploration assumes independent draws from one fixed distribution with no learning or discounting.
- The university postponement alternative is approximated as a full-horizon strategy, not solved as a genuinely staged sequential decision.
- Working sessions can contain sensitive context and are ignored by Git.

See [Known Limitations](KNOWN_LIMITATIONS.md) and [Security](SECURITY.md).

## How Codex and GPT-5.6 are used

Codex/GPT-5.6 performs conversational interpretation, model selection, adaptive questioning, categorization, review, tool invocation, and conditional explanation. Deterministic Python performs all authoritative numerical calculations. The language model does not guarantee arithmetic accuracy.

Development usage and conversational judgment boundaries are documented in [Codex Usage](docs/CODEX_USAGE.md).

## Release versions

| Component | Version |
|---|---|
| Overall project and Skill release | `1.0.0-rc3` |
| Decision model contract | `1.0` |
| Decision result contract | `1.0` |
| Mathematical engine recorded in results | `0.4.0` |
| Current report generator | `1.0.0-rc3` |

Overall release changes do not rewrite historical numerical results.

## Contributing, security, and license

- [Contributing](CONTRIBUTING.md)
- [Security and privacy](SECURITY.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Changelog](CHANGELOG.md)

Licensed under the [MIT License](LICENSE).
