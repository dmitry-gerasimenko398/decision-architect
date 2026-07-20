# Project Instructions for Codex Agents

## Scope and safety

- Work only inside this project folder.
- Keep this project local unless the user explicitly approves a remote repository or deployment.
- Do not install software or Python packages without asking first.
- Do not use API keys, external backends, private files, or network services.
- Do not advance to a new development phase without user review.
- Preserve user changes and avoid destructive Git commands.

## Product principles

- Never describe a result as an objectively correct life decision.
- Say that an option is preferable under the user's stated preferences, estimates, constraints, time horizon, and assumptions.
- Keep the interview/interpretation layer separate from deterministic calculations.
- Require explicit review and confirmation of structured inputs before calculation.
- Keep formulas, transformations, assumptions, seeds, and intermediate results reproducible.
- Prefer a small, testable, standard-library implementation.
- Explain important actions and mathematical ideas for a non-programmer.

## Engineering conventions

- Support only `multi_criteria` and `sequential_exploration` in the MVP.
- Use versioned JSON for calculation inputs and outputs.
- Treat `schemas/decision-model-v1.schema.json` and `schemas/decision-result-v1.schema.json` as the v1 interoperability contracts.
- Keep executable validation standard-library-only and reject rather than silently repair invalid input.
- Use Python type hints and small pure functions for calculation logic.
- Use a local seeded random-number generator; do not rely on global random state.
- Use `unittest` unless a dependency is explicitly approved.
- Keep report rendering separate from recommendation logic.
- Render reports only from validated saved result JSON. Never call either calculation engine, resample uncertainty, or recompute a policy while rendering.
- Escape all JSON-originated text, avoid executable user-controlled content, keep reports self-contained, and provide numerical alternatives for charts.
- Keep report generation deterministic and use atomic output writes so failures cannot leave partial HTML.
- Keep natural-language interviewing in the Skill. Python session helpers may structure and validate state but must not become a rigid questionnaire or infer user preferences.
- Require a complete review and exact `CONFIRM` before creating `confirmed-model.json`; never call analysis from session initialization, staging, checking, or finalization.
- Persist fingerprints for the exact proposed model and rendered review; reject direct finalization after staging or after any unreviewed change.
- Default Skill-authored fields to `system_proposal` and use per-field source maps for genuine user statements, user estimates, and defaults. Confirmation changes status, not provenance.
- Roll back all confirmation artifacts if any finalization write fails; never leave a partially confirmed session.
- Confine session paths to the selected `sessions/` root and store only model-relevant information with transparent status and provenance.
- Treat `sessions/` as ignored working storage. Publish only deliberately sanitized artifacts listed in the release manifest.
- Preserve the version distinction: overall release and Skill `1.0.0-rc1`, model/result contracts `1.0`, engine `0.4.0`, and current report generator `1.0.0-rc1`.
- Define simulated win probability as modeled first-place frequency, never real-life success probability.
- Keep dependency-aware uncertainty, Bayesian networks, and influence diagrams explicitly unimplemented unless a later reviewed phase changes scope.
- Ensure Windows commands use PowerShell-compatible syntax and project-relative paths.
- Update specifications and tests when a modeling assumption changes.

## Approved mathematical rules

- Represent uncertainty with triangular `minimum`, `most_likely`, and `maximum` values.
- Require user-confirmed, distinct worst and best anchors. Normalize with `(value - worst_anchor) / (best_anchor - worst_anchor)`; never infer anchors from alternatives.
- Require non-negative weights that sum to 1 and include at least one positive weight.
- Clamp utility to 0-1 and record every affected alternative/criterion through aggregate diagnostics.
- Rank feasible multi-criteria alternatives by Monte Carlo mean utility. Report analytical utility as a cross-check and also report Monte Carlo win probability.
- Use a dedicated seeded `random.Random` instance. Split simulation-tie credit equally using absolute tolerance `1e-12`.
- Use `recommended` for a unique leader with win probability at least 0.6 and `close_call` below 0.6.
- Represent exact primary-value ties explicitly (`mean_utility_tie` or `INDIFFERENT`) rather than selecting a winner arbitrarily.
- Evaluate hard constraints conservatively across triangular support using the operator rules in `PROJECT_SPEC.md`; stop if a confirmed boolean result disagrees.
- Vary one weight from 0 to 1 for sensitivity, preserving the relative proportions of all other weights, and report the first winner-change threshold.
- Reuse one fixed Monte Carlo sample for sensitivity, solve linear mean-utility crossings analytically, exclude infeasible alternatives, and verify both sides of every reported threshold without resampling.
- Use the finite-horizon sequential transitions recorded in `PROJECT_SPEC.md`, with net utility, finite unseen options, a zero-horizon base value of 0, and no discount factor.
- Approximate sequential expectations with deterministic midpoint quantile quadrature (default 101 positive odd points), canonicalize best-known memoization keys to 12 decimal places, and classify actions with tolerance `1e-10`.
- Sequential exploration receives the new draw `X` immediately, decrements unseen options, and updates the reusable best known value to `max(b, X)`; never substitute the old best-known value as the exploration reward.

## Definition of done for calculation work

A calculation feature is not done until it has documented assumptions, hand-checkable behavior, automated tests, deterministic output where applicable, useful validation errors, and conditional recommendation language.
