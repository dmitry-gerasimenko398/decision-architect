# Decision model contract v1

Read this reference before constructing or checking Decision Architect JSON. The authoritative machine-readable contracts are `schemas/decision-model-v1.schema.json` and `schemas/decision-result-v1.schema.json` at the repository root.

## Shared input envelope

Require `model_version: "1.0"`, one supported `model_type`, a stable decision ID, title, description, time horizon, explicit user confirmation, and a list of assumptions. Do not calculate from an unconfirmed model.

## `multi_criteria`

- Require 2–4 alternatives and at least two criteria.
- Use triangular `minimum`, `most_likely`, and `maximum` estimates.
- Require each alternative to provide an estimate for every criterion and a confirmed true/false result for every hard constraint.
- Define every constraint with `criterion_id`, one of `<= < >= > == !=`, and a numeric `threshold`. The engine recomputes it conservatively and stops if the declared boolean disagrees.
- Require user-confirmed, distinct worst and best anchors. Never infer anchors from the alternatives.
- Require non-negative weights that sum to 1 with at least one positive weight. Never silently normalize invalid weights.
- Normalize with `(value - worst_anchor) / (best_anchor - worst_anchor)` and clamp to 0–1. Require `clamp_utility: true` and report diagnostics whenever clamping occurs.
- Rank feasible alternatives by Monte Carlo mean utility. Report analytical triangular means and weighted utility as a cross-check.
- Sample with a dedicated seeded `random.Random` instance. Split simulation-tie credit equally using absolute tolerance `1e-12`.
- Use `recommended`, `close_call`, `mean_utility_tie`, `only_feasible_alternative`, or `no_feasible_alternative` exactly as the engine reports.
- Describe simulated win probability only as the fraction of modeled Monte Carlo scenarios in which an alternative ranked first. Never call it the probability of real-life success.

Conservative constraints inspect the triangular maximum for `<` and `<=`, the minimum for `>` and `>=`, and all three values for `==` and `!=`. Excluded alternatives receive constraint diagnostics and no utility result.

### Fixed-sample weight sensitivity

Run the ordinary Monte Carlo simulation once. Retain the mean normalized utility for every feasible alternative/criterion pair and do not draw new samples while testing weights. Excluded alternatives never participate, and weight changes never reevaluate hard constraints.

For target criterion `k` and candidate weight `x`, use:

```text
w_k(x) = x
w_j(x) = original_w_j * (1-x) / (1-original_w_k)
```

This preserves every non-target proportion. If the original target weight is exactly 1, mark that criterion not analyzable because the other proportions are undefined.

The fixed-sample alternative score is linear:

```text
mean_utility_a(x) = x * target_mean_a + (1-x) * weighted_other_mean_a
```

Solve line equalities analytically with tolerance `1e-12`; do not search a grid. Ignore crossings outside `[0,1]`. At a threshold, retain every tied top alternative and never choose arbitrarily. Verify the ranking on both sides with a small epsilon, reducing it near adjacent crossings when necessary. Report the nearest lower and upper verified thresholds and a robust interval around the baseline weight. A switch boundary is excluded from the unique-winner interval because the boundary itself is tied. A crossing at 0 or 1 may be a boundary tie with no permitted weight beyond it.

Treat no feasible alternative, one feasible alternative, and a baseline top-mean tie as explicit not-applicable cases. Sensitivity tracks changes in the highest fixed-sample mean utility. It does not track a change between `recommended` and `close_call` caused only by the 60% win-probability classification, and it does not model simultaneous changes to several weights.

## `sequential_exploration`

Require a declared utility scale, `remaining_opportunities >= 1`, `unseen_options_remaining >= 0`, an in-scale `best_known_value`, and an in-scale triangular new-option distribution. `analysis_settings.quadrature_points` is optional; omission means the documented default of 101. If supplied, it must be a positive odd integer.

Let the state be `(t,u,b)`, where `t` includes the current opportunity. Use these authoritative equations:

```text
V(0,u,b) = 0
exploit(t,u,b) = b + V(t-1,u,b)
explore(t,u,b) = E[X + V(t-1,u-1,max(b,X))]  when u > 0
V(t,u,b) = max(exploit(t,u,b), explore(t,u,b))
```

Exploration receives `X` immediately, decrements both counts, and preserves `max(b,X)` for later. Exploitation decrements only `t`. If `u=0`, exploration is unavailable and the action is `exploit`.

The expectation uses deterministic midpoint quantile quadrature. For `i=0..N-1`, compute `p_i=(i+0.5)/N`, map it through the triangular inverse CDF, and average the resulting reward plus continuation value. The engine uses memoized dynamic programming, 12 decimal places for best-known keys, and action-comparison tolerance `1e-10`. It reports lowercase `explore`, `exploit`, or `indifferent` without arbitrary tie-breaking.

Assumptions: values are net utility; there is no discount factor or separate exploration cost; unseen options are independent draws from one fixed triangular distribution; observing a value does not update that distribution. Describe this as a Feynman-inspired finite-horizon model, not a reproduction of every historical detail.

The sequential result includes current action values, expected total utility, method and reproducibility metadata, every horizon from 1 through the input horizon while holding `u`, `b`, and the distribution fixed, and all action-switch points.

## Validation and analysis

Run from the repository root:

```powershell
python -m decision_architect.validation path\to\model.json
python -m decision_architect analyze path\to\model.json --output path\to\result.json
python -m decision_architect report path\to\result.json --output path\to\report.html
```

In the current Codex workspace, use the Python fallback described in `docs/QUICKSTART_WINDOWS.md` when `py` is unavailable. Stop on any validation, calculation, or report error. The validator never repairs input, and a failed analysis must not produce a recommendation file.

## HTML reporting

Generate a report only from an already-saved, validated result-v1 JSON document. Reporting is a deterministic presentation step: it must not call the analysis engine, draw new samples, recompute utilities or policies, alter a recommendation, or modify source JSON. The standalone file contains embedded CSS and accessible inline SVG, no JavaScript or external resources, visible conditionality, numerical table alternatives for charts, print styling, and escaped raw JSON.

Use `--open` only when the user wants the completed file opened in the default browser. For the four release reports, generate the local index after all four reports with `python -m decision_architect report-index reports --results-dir outputs`.

Release `1.0.0-rc3` keeps the model and result contracts at `1.0` and the mathematical engine at `0.4.0`. The Skill must create proposed JSON with `confirmed_by_user: false`; only the confirmation-gated session helper may create the final model with that field true. Reports are presentation-only. Correlation-aware sampling, Bayesian networks, and influence diagrams are not implemented.
