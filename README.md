# Decision Architect

**Release candidate:** `1.0.0-rc1` · **OpenAI Build Week project**

Decision Architect is **a reusable Codex Skill with an adaptive interview, deterministic Python decision engine, validated JSON contracts, and self-contained local HTML reports**.

It turns an informal personal decision into a reviewable mathematical model, then explains which option is preferable under the user’s stated preferences, estimates, constraints, time horizon, and assumptions. It does not claim to discover an objectively correct life decision.

No API key, external backend, web service, deployment, or third-party Python package is required for the contest version.

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

## Quick demonstration in Codex

Open this repository as the current Codex project and type:

```text
$decision-analysis I will visit this restaurant eight more times. Should I try a new dish or order the best one I already know?
```

The Skill explains its provisional model choice, conducts the interview, and prepares a complete review. It does not calculate until the user replies exactly:

```text
CONFIRM
```

For the complete beginner workflow, see [Windows Quickstart](docs/QUICKSTART_WINDOWS.md). No JSON knowledge is needed to use the Skill.

## Codex Skill versus Python CLI

- **Codex Skill experience:** invoke `$decision-analysis`; Codex interviews you, maintains the draft, enforces confirmation, invokes the tools, and explains stored results.
- **Direct Python CLI:** use existing JSON examples to validate, calculate, test, or regenerate reports manually.
- **Stored result JSON:** the authoritative machine-readable calculation output.
- **HTML report:** a deterministic presentation of an already-saved validated result; reporting never reruns the mathematics.

## Windows commands

The standard-library code was verified with Python 3.12. From PowerShell in the repository root:

```powershell
py -m decision_architect verify-release
py -m unittest discover -s tests -v
```

If `py` is unavailable but `python` works, replace `py` with `python`. If neither command works, see the non-machine-specific fallback in [Windows Quickstart](docs/QUICKSTART_WINDOWS.md); do not copy a Python path from another computer.

Analyze and report the released examples:

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

## Repository structure

```text
.agents/skills/decision-analysis/   Codex Skill and focused references
decision_architect/                 Standard-library Python implementation
schemas/                            Versioned JSON contracts
examples/                           Sanitized inputs, source maps, and transcripts
outputs/                            Sanitized deterministic result JSON
reports/                            Sanitized standalone HTML reports and index
demo_sessions/                      Three sanitized end-to-end workflow records
sessions/                           Ignored local working sessions; never release-tracked
docs/                               Judge, usage, mathematics, and Windows guides
scripts/                            Deterministic demo-session generator
tests/                              Standard-library unittest suite
```

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
| Overall project and Skill release | `1.0.0-rc1` |
| Decision model contract | `1.0` |
| Decision result contract | `1.0` |
| Mathematical engine recorded in results | `0.4.0` |
| Current report generator | `1.0.0-rc1` |

Overall release changes do not rewrite historical numerical results.

## Contributing, security, and license

- [Contributing](CONTRIBUTING.md)
- [Security and privacy](SECURITY.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Changelog](CHANGELOG.md)

Licensed under the [MIT License](LICENSE).
