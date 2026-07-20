# Decision Architect — Project Specification

## Product promise

Decision Architect is a reusable Codex Skill with an adaptive interview, deterministic Python decision engine, validated JSON contracts, and self-contained local HTML reports. It helps a person turn an informal personal decision into a transparent mathematical model, confirm it, reproduce the calculations, and inspect an explainable recommendation.

The product does **not** claim to find an objectively correct life decision. Every conclusion must be phrased as conditional: an option is preferable **under the user's stated preferences, estimates, constraints, time horizon, and modeling assumptions**.

## Target user

The primary user is a non-programmer facing a personal decision who wants more structure than a pros-and-cons list but still needs to understand and challenge the reasoning. The user should not need to know probability, utility theory, dynamic programming, Python, or JSON.

## User journey

1. Describe the decision in ordinary language.
2. Select or confirm the appropriate model type.
3. Answer an adaptive interview about alternatives, constraints, criteria or opportunities, uncertain estimates, preferences, and time horizon.
4. Review a plain-language summary of the proposed structured model.
5. Correct or explicitly confirm that model before calculations run.
6. Run the deterministic calculation engine.
7. Review results, sensitivity findings, assumptions, and an explainable conditional recommendation.
8. Open a self-contained visual HTML report and reproduce the same result from the saved JSON inputs.

## Exact MVP scope

The MVP is a local, Windows-friendly Codex Skill plus a deterministic Python engine. It supports exactly two model types: `multi_criteria` and `sequential_exploration`.

Shared MVP capabilities:

- Natural-language intake and an adaptive interview run by Codex.
- A user confirmation checkpoint before calculation.
- A versioned local session record that distinguishes missing, provisional, and user-confirmed values and records their source type.
- JSON model input and JSON calculation output.
- Validation with actionable, plain-language error messages.
- Deterministic calculations, including a recorded random seed where sampling is used.
- A self-contained HTML report that works locally without a backend.
- Formulas, normalized values, assumptions, exclusions, and intermediate results sufficient to reproduce the recommendation.
- Lightweight automated tests using Python's standard-library `unittest` unless a later decision justifies another tool.

### Model type: `multi_criteria`

Purpose: one-time choices such as choosing between jobs.

MVP behavior:

- Accept 2–4 alternatives.
- Represent hard constraints and mark alternatives that fail them as infeasible before ranking.
- Define each hard constraint with a criterion ID, one of `<=`, `<`, `>=`, `>`, `==`, or `!=`, and a numeric threshold.
- Record one explicit, user-confirmed true/false result for every hard constraint on every alternative. The engine recomputes the result and stops if it contradicts the confirmed declaration.
- Evaluate uncertain constraints conservatively across all supported triangular values: upper-bound rules use the maximum, lower-bound rules use the minimum, equality requires all three values to equal the threshold within `1e-12`, and inequality fails only when all three equal the forbidden value within that tolerance.
- Accept multiple explicitly named criteria.
- Record whether more or less of each criterion is preferred.
- Require non-negative criterion weights that already sum to 1, with at least one positive weight. Reject rather than silently normalize invalid input.
- Represent uncertain criterion values using minimum, most likely, and maximum estimates, requiring `minimum <= most_likely <= maximum`.
- Model every three-point estimate as a triangular distribution.
- Require distinct, user-confirmed worst and best raw-value anchors for every criterion. Do not infer anchors from the alternatives.
- Normalize raw values with `utility = (value - worst_anchor) / (best_anchor - worst_anchor)`. This covers maximize and minimize criteria because the best anchor may be numerically above or below the worst anchor.
- Clamp normalized utility to the range 0 to 1 and record aggregate warnings and diagnostics whenever clamping occurs. Model v1 requires `clamp_utility: true`.
- Compute weighted utility for every feasible alternative.
- Calculate each triangular raw mean as `(minimum + most_likely + maximum) / 3` and report its weighted analytical utility as a cross-check.
- Rank feasible alternatives primarily by Monte Carlo mean utility.
- Run a seeded Monte Carlo simulation using a dedicated `random.Random` instance and report the fraction of modeled scenarios in which each alternative ranks first.
- Compare simulation utilities with absolute tolerance `1e-12` and divide win credit equally among tied alternatives.
- Report simulated minimum, maximum, population standard deviation, and percentiles 10, 50, and 90. Percentiles use linear interpolation at sorted index `(n - 1) * p`.
- Use recommendation statuses `recommended`, `close_call`, `mean_utility_tie`, `only_feasible_alternative`, and `no_feasible_alternative`.
- Classify a unique leader as `close_call` when its win probability is below 60 percent; otherwise use `recommended`.
- For weight sensitivity, vary one criterion's weight from 0 to 1 while preserving the relative proportions of all other weights and renormalizing them.
- Report the first weight threshold at which the winner changes. Use the explicit triangular minimum and maximum values rather than inventing uncertainty ranges.

Weight sensitivity reuses one fixed Monte Carlo sample. For target weight `x`, each non-target weight is `original_weight * (1-x) / (1-original_target_weight)`. The engine uses the fixed-sample mean normalized utility for each alternative/criterion, making every alternative score linear in `x`. It solves equality crossings analytically with tolerance `1e-12`, verifies both sides, and reports nearest lower and upper switches plus the robust interval containing the baseline weight. Excluded alternatives never participate and hard constraints are not reevaluated. A target with original weight 1 is not analyzable because the remaining proportions are undefined. Winner sensitivity concerns the top mean utility, not changes in the 60 percent `close_call` classification.

The recommendation is the alternative with the highest Monte Carlo mean utility under the confirmed model. Analytical utility is a transparent cross-check. Simulated win probability is modeled first-place frequency, not the probability of real-life success or objective truth. It and the `close_call` classification communicate uncertainty but do not replace the primary ranking rule. The decision rule, tie tolerance, and 60 percent threshold also appear in calculation output.

If alternatives have equal leading Monte Carlo mean utility within `1e-12`, the result represents a `mean_utility_tie` and lists the tied alternatives rather than selecting one arbitrarily.

### Model type: `sequential_exploration`

Purpose: repeated finite-horizon choices where the user may exploit the best known option or explore a new one, inspired by Richard Feynman's restaurant problem.

MVP behavior:

- Accept a finite integer number of remaining opportunities.
- Accept the quality or utility of the best known option.
- Accept a documented uncertain distribution for the quality of a new option.
- Compare the expected value of exploiting the best known option now with exploring a new option now.
- Use dynamic programming or an equivalent mathematically valid finite-horizon method.
- State the timing and information assumptions: whether exploration consumes an opportunity, whether the observed new option can become the new best known option, and how rewards accumulate.
- Show the recommended action for the current state.
- Show how the recommendation changes as the number of remaining opportunities changes.
- Include expected values and the decision boundary or threshold where practical.

The approved finite-horizon state and transition rules are:

- `remaining_opportunities` includes the current decision; the base value is 0 when it reaches 0.
- `unseen_options_remaining` counts the finite number of options that may still be explored.
- `best_known_value` is the net utility of the best reusable known option.
- `EXPLOIT` receives `best_known_value` now, decreases remaining opportunities by 1, and leaves the unseen count and best known value unchanged.
- `EXPLORE` is available only when unseen options remain. It receives a triangularly sampled new-option value now, decreases both counts by 1, and updates the best known value to the maximum of the old and sampled values.
- Values are net utility, so the MVP has no separate cost field.
- The MVP has no discount factor.
- If `EXPLOIT` and `EXPLORE` differ by no more than `1e-10`, the policy reports lowercase `indifferent` rather than choosing arbitrarily.

The implemented engine uses memoized dynamic programming and deterministic midpoint quantile quadrature over the triangular inverse CDF. The grid defaults to 101 points and explicit counts must be positive odd integers. Best-known memoization keys use 12 decimal places. Every horizon row from 1 through the confirmed horizon holds the other starting-state inputs constant, and the result identifies every action-switch point.

## Exclusions from the MVP

- Claims of objective correctness, certainty, professional advice, or guaranteed outcomes.
- More than the two named model types.
- Group decision-making, negotiation, or voting mechanisms.
- Continuous optimization, portfolio optimization, or general constraint solvers.
- Learning a user's preferences without their review.
- Automatic collection of private data or data from external services.
- API keys, hosted services, databases, authentication, telemetry, or an external backend.
- Deployment, a remote GitHub repository, mobile apps, or native desktop packaging.
- Real-time market data or other live data feeds.
- Correlated uncertainty, validated correlation matrices, copulas, Bayesian networks, and influence diagrams. These are possible future directions, not implemented features.
- Advanced value-of-information analysis beyond what is needed for `sequential_exploration`.
- Replacing financial, medical, legal, or other professional advice.

## Acceptance criteria

The MVP is acceptable when all of the following are demonstrated locally:

1. A non-programmer can start from a natural-language decision and complete the interview with clear prompts.
2. The interview chooses one of the two supported model types and rejects unsupported cases with an explanation.
3. The user can review and amend a complete plain-language model summary before explicitly confirming it.
4. Valid confirmed models serialize to a documented JSON schema; invalid models fail before calculation with useful messages.
5. A `multi_criteria` example with 2–4 alternatives produces feasibility results, weighted utilities, seeded Monte Carlo first-place frequencies, sensitivity findings, and recommendation-change conditions.
6. A `sequential_exploration` example produces valid exploit/explore expected values and a policy across different remaining horizons.
7. Running the same engine version with identical JSON input and seed produces identical JSON output.
8. Automated tests cover formulas, validation boundaries, seeded simulation behavior, infeasible alternatives, ties, and edge horizons.
9. Calculation output identifies the model version, engine version, decision rule, assumptions, seed when applicable, and enough intermediate values to audit the result.
10. A self-contained local HTML report faithfully presents the confirmed inputs and calculation output without recomputing or altering the recommendation in JavaScript.
11. Recommendations consistently use conditional language such as "under your stated assumptions."
12. The README gives copy-and-paste Windows commands for running examples and tests with no API key or backend.
13. The adaptive Skill begins from natural language, asks small relevant batches, rejects unsupported structures, and produces no calculation before exact confirmation of a complete valid model.

## Major assumptions and approved decisions

- The language-model layer interviews and explains; it does not perform authoritative calculations.
- The Python engine accepts structured data and returns structured data; it does not conduct the interview.
- The report generator renders engine output and does not contain a second calculation implementation.
- The Skill controls the conversation; deterministic session helpers provide safe IDs, path confinement, incomplete-state checks, validation, confirmation gating, and atomic writes without becoming a terminal questionnaire.
- Session drafts keep `confirmed_by_user: false`. Only exact `CONFIRM` after a fingerprinted complete review may create a validated confirmed model; per-field provenance remains explicit, partial finalization is rolled back, and analysis remains a later separate command.
- The report generator consumes validated result-v1 JSON only, escapes JSON-originated text, performs no calculation, and creates deterministic standalone HTML with no external resources.
- Every visualization has an accessible name and description plus a complete numerical table alternative; print output preserves important caveats.
- JSON schemas will be versioned so saved decisions remain interpretable as the project evolves.
- The executable project remains standard-library-only. JSON Schema files document interoperability; Python performs manual executable validation.
- Monte Carlo tests will use fixed seeds. Production reports will record their seed.
- Uncertainty uses triangular distributions and utility anchors are always user-confirmed.
- Monte Carlo mean utility is the primary multi-criteria ranking rule; analytical utility is a cross-check, and simulated first-place frequencies plus the 60 percent `close_call` threshold qualify recommendation strength without claiming real-life success probability.
- Exact simulation ties split win credit equally.
- Exact primary-value ties remain explicit rather than being broken arbitrarily.
- Weight sensitivity preserves the relative proportions of other weights while varying one weight from 0 to 1.
- Weight sensitivity reuses fixed simulated criterion utilities and never resamples candidate weights.
- One-at-a-time weight sensitivity does not represent simultaneous preference changes.
- The sequential state transitions above are authoritative for the MVP.
- Sequential unseen options are independent draws from one fixed triangular distribution; the MVP does not learn or update that distribution.
- Sequential output is deterministic and uses no random state.
- The project is licensed under the MIT License.
