# Decision Architect — Ordered Development Plan

Only one phase should be undertaken at a time after review of the previous phase.

## Phase 1 — Foundation (approved)

- [x] Inspect the project folder.
- [x] Verify Git and Python without installing software.
- [x] Initialize a local Git repository.
- [x] Create the proposed directory skeleton and initial Skill metadata.
- [x] Record product scope, architecture, acceptance criteria, assumptions, and working rules.
- [x] Obtain user review and approval before implementation.

## Phase 2 — Data contracts and hand-checkable examples (approved)

- [x] Resolve the deferred mathematical decisions listed in `ARCHITECTURE.md`.
- [x] Define versioned input schemas for the shared envelope and both model types.
- [x] Define the calculation-output contract.
- [x] Create one small, hand-calculated example per model type.
- [x] Write validation requirements and tests before calculation code.
- [x] Document conditional recommendation language.
- [x] Implement standard-library-only manual input validation and typed data structures.
- [x] Obtain user review and approval before Phase 3.

Deliverable: reviewed schemas, example JSON, expected hand calculations, and validation tests.

## Phase 3 — Core `multi_criteria` calculations (approved)

- [x] Extend v1 hard constraints with criterion, operator, and threshold while preserving confirmed boolean results.
- [x] Implement conservative hard-constraint filtering and detailed exclusion diagnostics.
- [x] Implement clamped utility normalization, analytical triangular means, and weighted utility.
- [x] Implement seeded triangular sampling, Monte Carlo mean utility, win probabilities, and distribution summaries.
- [x] Implement numerical-tolerance tie handling and all approved recommendation statuses.
- [x] Add result-v1 serialization and the Windows-friendly `analyze` command.
- [x] Generate `outputs/job-choice-result.json` through the engine.
- [x] Add focused unit, CLI, result-contract, and reproducibility tests.
- [x] Obtain user review and approval before Phase 4.

Deliverable: deterministic JSON results for the approved multi-criteria example; no polished report yet.

## Phase 4 — `sequential_exploration` calculations (approved)

- [x] Implement the approved finite-horizon Bellman recurrence.
- [x] Implement deterministic midpoint quantile quadrature and memoization.
- [x] Produce current exploit/explore values, policy by horizon, and switch points.
- [x] Add Feynman-inspired long- and short-horizon examples and outputs.
- [x] Add hand-checkable, edge-case, contract, CLI, and reproducibility tests.
- [x] Obtain user review and approval before Phase 5.

Deliverable: deterministic JSON results for the approved sequential examples.

## Phase 5 — `multi_criteria` sensitivity (approved)

- [x] Retain fixed-sample criterion means without resampling candidate weights.
- [x] Implement the approved one-weight renormalization rule.
- [x] Solve winner-line crossings analytically and verify both sides.
- [x] Report lower/upper switches, robust intervals, ties, and not-applicable cases.
- [x] Extend result-v1 and CLI output with auditable sensitivity data.
- [x] Add hand-checkable, edge-case, contract, CLI, and reproducibility tests.
- [x] Obtain user review and approval before Phase 6.

Deliverable: auditable sensitivity output and recommendation-change conditions.

## Phase 6 — Command-line interface and report generator (approved)

- [x] Extend the existing validation and `analyze` commands with report generation.
- [x] Build self-contained accessible HTML templates for both model types.
- [x] Display results, sensitivity or horizon policy, assumptions, limitations, and reproducibility details.
- [x] Escape JSON-originated text and test injection, deterministic generation, and atomic failure behavior.
- [x] Add accessible inline SVG charts with complete numerical table alternatives.
- [x] Generate the three demonstration reports and local index through actual commands.
- [x] Add copy-and-paste Windows instructions.
- [x] Obtain user review and approval before Phase 7.

Deliverable: local end-to-end runs from JSON to HTML.

## Phase 7 — Adaptive interview Skill (approved)

- [x] Write structural model-selection and adaptive question-selection workflows.
- [x] Add small-batch interview, uncertainty, swing-weighting, and contradiction guidance.
- [x] Add versioned persisted session state and exact confirmation gating.
- [x] Connect confirmed sessions to the existing deterministic analyze and report commands.
- [x] Generate realistic job-choice and restaurant demonstration sessions and transcripts.
- [x] Add a repeatable workflow evaluation rubric and deterministic support tests.
- [x] Ensure unsupported, privacy-sensitive, and high-stakes cases receive suitable limitations.
- [x] Persist review fingerprints, support per-field provenance maps, and make multi-artifact finalization rollback-safe.
- [x] Independently audit and correct review completeness and demo terminology/provenance.
- [x] Obtain user review and approval before Phase 8, including both live human Skill tests.

Deliverable: the reusable Skill drives both model types without doing authoritative math itself.

## Phase 8 — MVP integration and release readiness (current)

- [x] Run full automated tests from a controlled clean local export.
- [x] Verify deterministic output and generated artifacts across repeat runs.
- [x] Review every recommendation for conditional wording and simulated-win-probability meaning.
- [x] Review report content, accessibility structure, responsive/print CSS, and zero-weight indicator presentation; direct local-file visual opening remains a documented manual check because the in-app browser blocks local-file URLs.
- [x] Finalize the approved MIT License.
- [x] Freeze overall release `1.0.0-rc1` while preserving contract `1.0` and engine `0.4.0`.
- [x] Add release documents, Windows quickstart, judging guide, contest demo, and known limitations.
- [x] Sanitize and document both live human acceptance tests.
- [x] Add and pass the standard-library release verifier.
- [x] Confirm working sessions are ignored and absent from the intended release manifest.
- [x] Complete independent Phase 8 audits and resolve concrete findings.
- [ ] Obtain user review before Phase 9 publication work.

Deliverable: contest-ready local MVP. Remote repository creation and deployment remain separate, user-approved tasks.
